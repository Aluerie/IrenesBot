"""
_Insert Module Docstring Here_.

License
-------
* License: MPL-2.0, see LICENSE for more details.
* Copyright: (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import pprint
import re
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Annotated, Any, TypedDict, override

import asyncpg
from eventapi.EventApi import EventApi
from eventapi.WebSocket import (
    Dispatch,
    EventType,
    ResponseTypes,
    SubscriptionCondition,
    SubscriptionData,
)
from twitchio.ext import commands

from core import IrePublicComponent, ireloop
from shared import errors, fuzzy, seven_tv
from utils import const, guards

if TYPE_CHECKING:
    import twitchio

    from core import IreBot, IreContext

    class CycleStatusQueryRow(TypedDict):
        """Cycle Status Query Row."""

        reward_id: str
        emote_limit: int
        emote_count: int
        emote_set_id: str

    class BatchLastYearEntry(TypedDict):
        """BatchLastYearEntry."""

        emote_id: int
        guild_id: int
        author_id: int
        used: str  # isoformat


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def to_emote_id(user_input: str) -> str:
    """A function to convert a 7TV emote link to an emote_id.

    Does not do anything if the user input is already an emote_id.
    If no emote_id is provided then it errors out.
    """
    search = re.search(
        r"(?:https?:\/\/(?:www\.)?7tv\.app\/emotes\/)?(?P<emote_id>[0-7][0-9A-HJKMNP-TV-Z]{25})",
        user_input,
    )
    if search is None:
        msg = f"Bad emote id, make sure you made no mistakes {const.FFZ.peepoPolice}"
        raise errors.BadUserInputError(msg)
    return search["emote_id"]


class UserSearchEmoteIDConverter(commands.Converter[str]):
    """Seven TV Emote Converter.

    Converts user_input from `str` type into 7TV emote_id.
    """

    @override
    async def convert(self, ctx: IreContext, user_input: str) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Convert `user_input` to 7TV emote_id."""
        # Step 1. Check if it's emote link / emote_id
        try:
            return to_emote_id(user_input)
        except errors.BadUserInputError:
            pass

        # Step 2. Try to find the said emote with 7TV Graph QL
        try:
            return (await (ctx.bot.stv.create_partial_user(ctx.broadcaster.id)).search_emote(user_input)).id
        except errors.UnsatisfyingResultError:
            msg = f"It seems there is no emote like that {const.STV.POLICE}"
            raise errors.RespondWithError(msg) from None


class SevenTVCyclingEmotes(IrePublicComponent):
    """Cycling Emotes."""

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.reward_ids_cache: set[str] = set()

        self._batch_total: defaultdict[int, Counter[int]] = defaultdict(Counter)
        self._batch_last_year: list[BatchLastYearEntry] = []
        self._batch_lock = asyncio.Lock()

        self.bulk_insert.add_exception_type(asyncpg.PostgresConnectionError)

        async def ws_callback(data: ResponseTypes) -> None:
            """7TV WebSocket Callback.

            When emotes get deleted - they should be deleted from the bot's database too.
            """
            if not isinstance(data, Dispatch):
                return
            if data.type != EventType.EMOTE_SET_UPDATE:
                return

            if data.body.pulled:
                # Emote Deleted
                for pulled in data.body.pulled:
                    query = """
                        DELETE FROM ttv_cycling_emotes
                        WHERE emote_id = $1 AND emote_set_id = $2;
                    """
                    emote_id: str = pulled.old_value["id"]  # pyright: ignore[reportOptionalSubscript, reportUnknownVariableType]
                    emote_set_id = data.body.id

                    await self.bot.pool.execute(query, emote_id, emote_set_id)  # pyright: ignore[reportUnknownArgumentType]

        self.stv_ws = EventApi(callback=ws_callback)

    async def stv_ws_subscribe(self, emote_set_id: str) -> None:
        """Make 7TV WebSocket Subscription."""
        condition = SubscriptionCondition(object_id=emote_set_id)  # your emote-set id
        subscription = SubscriptionData(subscription_type=EventType.EMOTE_SET_ALL, condition=condition)
        await self.stv_ws.subscribe(subscription_data=subscription)

    async def stv_ws_multi_subscribe(self) -> None:
        """Make 7TV WebSocket Subscriptions."""
        query = "SELECT DISTINCT emote_set_id FROM ttv_cycling_emote_rewards;"
        for (emote_set_id,) in await self.bot.pool.fetch(query):
            await self.stv_ws_subscribe(emote_set_id)

    @override
    async def component_load(self) -> None:
        await self.stv_ws.connect()
        await self.stv_ws_multi_subscribe()
        self.fill_known_rewards.start()
        # self.bulk_insert.start()
        # self.clean_up_old_records.start()
        await super().component_load()

    @override
    async def component_teardown(self) -> None:
        self.fill_known_rewards.cancel()
        # self.bulk_insert.stop()
        # self.clean_up_old_records.stop()
        await super().component_teardown()

    @commands.group(name="7tv", aliases=["stv"])
    async def stv(self, ctx: IreContext) -> None:
        """Group command for `!7tv`.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

    #########################################################################################################################
    # 7TV EMOTE CYCLING EMOTES CHANNEL POINTS REWARD                                                                        #
    #########################################################################################################################

    @ireloop(count=1)
    async def fill_known_rewards(self) -> None:
        """The task that fills a set of rewards ids for convenience to cut on a few database queries."""
        query = "SELECT reward_id FROM ttv_cycling_emote_rewards"
        self.reward_ids_cache = {r for (r,) in await self.bot.pool.fetch(query)}

    @stv.group(name="cycle")
    async def stv_cycle(self, ctx: IreContext) -> None:
        """Group command for `!7tv cycle`.

        These commands manage 7tv cycling emotes and channel points reward.

        Without a subcommand this lists subcommands.
        """
        await ctx.send(
            content=(
                "`!7tv cycle` is a group command, use it together with one of the "
                f"children: {', '.join(list(self.stv_cycle._commands))}."
            )
        )

    @guards.is_broadcaster_or_dev()
    @stv_cycle.command(name="create")
    async def stv_cycle_create(self, ctx: IreContext, emote_limit: int = 10) -> None:
        """Create 7TV Cycling emote channel points reward."""
        custom_reward = await ctx.broadcaster.create_custom_reward(
            # This prompt can be 45 characters max
            title=f"Add 7TV emote ({emote_limit} slots, oldest cycle out)",
            cost=10,
            prompt=(
                # This prompt can be 200 characters max
                "Give me a 7TV emote link or emote ID. Optionally, type an emote alias. "
                'Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF SMH"'
            ),
        )
        partial_emote_set = await self.bot.stv.create_partial_user(ctx.broadcaster.id).fetch_active_emote_set()

        query = """
            INSERT INTO ttv_cycling_emote_rewards
            (streamer_id, reward_id, emote_limit, emote_set_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (streamer_id)
                DO NOTHING
            returning streamer_id
        """
        streamer_id: str | None = await self.bot.pool.fetchval(
            query,
            ctx.broadcaster.id,
            custom_reward.id,
            emote_limit,
            partial_emote_set.id,
        )
        if streamer_id is None:
            msg = "This channel already has 7TV Cycling Emotes Channel Reward"
            raise errors.RespondWithError(msg)

        await self.fill_known_rewards()
        await ctx.send(
            f"Created a cycling 7tv emote channel points reward {const.STV.DankApprove} "
            "PS. if you want to edit it (e.g. text or color) - visit your creator dashboard "
            f"(dashboard.twitch.tv/u/{ctx.broadcaster.name}/viewer-rewards/channel-points/rewards). "
            "Just don't remove `Require Viewer to Enter Text`, please."
        )
        await self.stv_ws_subscribe(partial_emote_set.id)

    @guards.is_broadcaster_or_dev()
    @stv_cycle.command(name="remove", aliases=["delete"])
    async def stv_cycle_remove(self, ctx: IreContext, emote_id: Annotated[str, UserSearchEmoteIDConverter]) -> None:
        """Remove an emote from the cycling list.

        Useful when a streamer wants an emote to stop from being cycled out.
        """
        query = """
            DELETE FROM ttv_cycling_emotes
            WHERE emote_id = $1 AND streamer_id = $2
        """
        await self.bot.pool.execute(query, emote_id, ctx.broadcaster.id)
        await ctx.send(f"The {emote_id} was removed from the cycling emote list {const.STV.DonkCrayon}")

    @stv_cycle.command(name="status")
    async def stv_cycle_status(self, ctx: IreContext) -> None:
        """Get 7TV Cycling emote channel points reward's status."""
        query = """
            SELECT
                reward_id,
                emote_limit,
                (
                    SELECT COUNT(*)
                    FROM ttv_cycling_emotes
                    WHERE ttv_cycling_emotes.streamer_id = ttv_cycling_emote_rewards.streamer_id
                ) AS emote_count,
                emote_set_id
            FROM ttv_cycling_emote_rewards
            WHERE streamer_id = $1;
        """
        row: CycleStatusQueryRow | None = await self.bot.pool.fetchrow(query, ctx.broadcaster.id)

        if row is None:
            msg = "This streamer doesn't have 7tv cycling emote channel points reward set up."
            raise errors.RespondWithError(msg)

        reward = next(iter(await ctx.broadcaster.fetch_custom_rewards(ids=[row["reward_id"]])), None)
        if reward is None:
            msg = (
                "Somehow the database has wrong information about the 7tv cycle reward - "
                "please, use !7tv cycle attach *name_of_the_channel_points_reward* to reattach."
            )
            raise errors.PlaceholderError(msg)

        content = (
            f"✅ title={reward.title} cost={reward.cost} reward_id={row['reward_id']} emote_limit={row['emote_limit']} "
            f"emote_count={row['emote_count']} emote_set_id={row['emote_set_id']}"
        )
        await ctx.send(content)

    @guards.is_broadcaster_or_dev()
    @stv_cycle.command(name="limit")
    async def stv_cycle_limit(self, ctx: IreContext, new_limit: int) -> None:
        """Change 7TV Cycling emote channel points reward's limit."""
        query = """
            UPDATE ttv_cycling_emote_rewards
            SET emote_limit = $1
            WHERE streamer_id = $2
            RETURNING (SELECT emote_limit FROM ttv_cycling_emote_rewards WHERE streamer_id = $2);
        """
        # TODO: after upgrading to PostgresQL 18 https://stackoverflow.com/a/7927957/19217368
        old_emote_limit = await self.bot.pool.fetchval(query, new_limit, ctx.broadcaster.id)
        await ctx.send(f"Changed emote_limit from {old_emote_limit} to {new_limit}")

    @guards.is_broadcaster_or_dev()
    @stv_cycle.command(name="attach")
    async def stv_cycle_attach(self, ctx: IreContext, *, reward_title: str) -> None:
        """Attach cycling to an existing channel points reward."""
        rewards = await ctx.broadcaster.fetch_custom_rewards()
        find = next(iter(fuzzy.finder(reward_title, rewards, key=lambda x: x.title)), None)
        if find is None:
            msg = f"Couldn't find any rewards matching title {reward_title}"
            raise errors.RespondWithError(msg)

        query = """
            UPDATE ttv_cycling_emote_rewards
            SET reward_id = $1
            WHERE streamer_id = $2;
        """
        await self.bot.pool.execute(query, find.id, ctx.broadcaster.id)
        await self.fill_known_rewards()
        await ctx.send(f"Attached cycling emotes reward to the channel points redeem `{find.title}` ({find.id})")

    @commands.Component.listener(name="custom_redemption_add")
    async def channel_points_redeem(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Somebody redeemed a custom channel points reward."""
        if redemption.reward.id not in self.reward_ids_cache:
            return

        log.debug(
            "🖍️ - User @%s (%s) requested cycle-emote at broadcaster @%s (%s)",
            redemption.user.display_name,
            redemption.user.id,
            redemption.broadcaster.display_name,
            redemption.broadcaster.id,
        )

        # Step 1. Parse User Input
        split = redemption.user_input.split()

        async def refund_and_respond(content: str) -> None:
            """Refund the redemption and response.

            Just a little lazy shortcut.
            """
            await redemption.refund(token_for=redemption.broadcaster.id)
            await redemption.respond(content=content)

        if len(split) > 2:
            await refund_and_respond(
                f'Bad Input, it\'s supposed to be an "*emote_link/id* *optional_emote_alias*" - '
                f"no extra words {const.FFZ.peepoPolice}"
            )
            return

        try:
            emote_id = to_emote_id(split[0])
        except errors.BadUserInputError:
            await refund_and_respond(
                f'Bad input (it\'s supposed to be "*emote_link/id* *optional_emote_alias*") {const.FFZ.peepoPolice}'
            )
            return

        try:
            # If emote alias was given - assign it.
            emote_alias: str = split[1]
        except IndexError:
            # unfortunately, due to Seven TV weird implementation of Emote Set update call
            # we won't actually get the name from it, so we need to fetch it beforehand.
            emote_alias = (await self.bot.stv.fetch_emote(emote_id)).default_name

        log.debug("🖍️ - emote_id = %s emote_alias = %s", emote_id, emote_alias)

        # Step 2. Get Emote Set
        partial_emote_set = await self.bot.stv.create_partial_user(redemption.broadcaster.id).fetch_active_emote_set()
        log.debug("🖍️ - Operating on emote_set #%s", partial_emote_set.id)

        # Step 3. Remove emote(-s) if above the limit
        query = """
            SELECT tce2.emote_id
            FROM ttv_cycling_emotes tce2
            WHERE tce2.streamer_id = $1
                AND tce2.emote_set_id = $2
            ORDER BY tce2.added_at DESC
            OFFSET (
                SELECT tcer.emote_limit - 1
                FROM ttv_cycling_emote_rewards tcer
                WHERE tcer.streamer_id = $1
            )
        """
        emote_ids_to_remove: list[str] = [
            r for (r,) in await self.bot.pool.fetch(query, redemption.broadcaster.id, partial_emote_set.id)
        ]
        log.debug("🖍️ - Removing emotes #%s", emote_ids_to_remove)

        for emote_id_to_remove in emote_ids_to_remove:
            try:
                emote_name_to_remove: str = await partial_emote_set.fetch_emote_alias(emote_id=emote_id_to_remove)
                await partial_emote_set.remove_emote(emote_id=emote_id_to_remove)
            except seven_tv.EmoteNotFoundInSetError:
                log.debug("🖍️ Emote Not Found - removing #%s", emote_id_to_remove)
            else:
                # await redemption.respond(f"Removed {emote_name_to_remove} ({get_seven_tv_link(emote_id_to_remove)})")
                log.debug("🖍️ - Removed emote %s (#%s)", emote_name_to_remove, emote_id_to_remove)
        # if emote_ids_to_remove:
        #     query = """
        #         DELETE FROM ttv_cycling_emotes
        #         WHERE streamer_id = $1 AND emote_id = ANY($2);
        #     """
        #     await self.bot.pool.execute(query, redemption.broadcaster.id, emote_ids_to_remove)

        # Step 4. Add the requested emote
        try:
            partial_emote = await partial_emote_set.add_emote(emote_id=emote_id, emote_alias=emote_alias)
        except seven_tv.ConflictingEmoteNameError:
            try:
                await partial_emote_set.fetch_emote_alias(emote_id)
            except seven_tv.EmoteNotFoundInSetError:
                # This means the new emote has a conflicting name
                await refund_and_respond(
                    f"This emote has a conflicting name, consider adding it with an alias {const.FFZ.peepoPolice}"
                )
                return
            else:
                # This means the new emote was already added
                await refund_and_respond(f"This his emote was already added to this emote set {const.FFZ.peepoPolice}")
                return

        log.debug("🖍️ Added emote #%s", emote_id)

        query = """
            INSERT INTO ttv_cycling_emotes
            (emote_id, streamer_id, emote_set_id, requested_by)
            VALUES ($1, $2, $3, $4)
        """
        await self.bot.pool.execute(query, emote_id, redemption.broadcaster.id, partial_emote_set.id, redemption.user.id)

        result = f"🖍️ Added '{emote_alias}' ({partial_emote.url()}) {const.STV.DonkCrayon}"
        log.info(result)
        # await redemption.respond(result)
        await redemption.fulfill(token_for=redemption.broadcaster.id)

    @guards.is_dev()
    @commands.command(aliases=["dev_reset_cycle"])
    async def dev_cycle_reset(self, ctx: IreContext) -> None:
        """Developer command for temporary reset / testing.

        This
        * sets @Irene's `emote_limit` to 2;
        * removes all current @Irene's cycling emotes;
        * removes color emotes (Blue, Teal, Yellow) from Irene's active emote set;
        """
        query = "UPDATE ttv_cycling_emote_rewards SET emote_limit = $1 WHERE streamer_id = $2;"
        await self.bot.pool.execute(query, 2, const.UserID.Irene)

        query = "DELETE FROM ttv_cycling_emotes tce WHERE tce.streamer_id = $1;"
        await self.bot.pool.execute(query, const.UserID.Irene)

        color_ball_ids = [
            # cSpell: disable
            "01J8FC6EN0000DNWJ3ST67HH38",  # Blue
            "01J8FCA6RR0004HJ8DYSFE2PF2",  # Teal
            "01J8FCAY6R0006NP3M7JY4GDAA",  # Purple
            "01J8FCBGRG000A5QBDAQ50YRYC",  # Yellow
            "01J8FCC2B00005G1FWF2H9XPCE",  # Orange
            "01J8FCG750000D15QN0BDGKN3A",  # Pink
            "01J8FCGXKR000E0691W9XKC6X0",  # Olive
            "01J8FCHF68000E0691W9XKC6X5",  # LightBlue
            "01J8FCHZSG000C93G7AYMMNCBC",  # DarkGreen
            "01J8FCK00R0006NP3M7JY4GDB0",  # Brown
            # cSpell: enable
        ]
        for emote_id in color_ball_ids:
            with contextlib.suppress(seven_tv.EmoteNotFoundInSetError):
                await ctx.bot.stv.create_partial_emote_set(const.STV_IRENE_DEFAULT_EMOTE_SET_ID).remove_emote(emote_id)
        await ctx.send(f"Done {const.STV.DonkCrayon}")

    #########################################################################################################################
    # 7TV EMOTE STATS                                                                                                       #
    #########################################################################################################################

    @guards.is_broadcaster_or_dev()
    @stv.group(name="stats")
    async def stv_stats(self, ctx: IreContext) -> None:
        """Group command for !7tv stats."""
        await ctx.group_default_response()

    # @guards.is_broadcaster_or_dev()
    # @stv_stats.group(name="allow")
    # async def stv_stats_allow(self, ctx: IreContext) -> None:
    #     """Group command for !7tv stats."""
    #     await ctx.send("")

    @ireloop(seconds=60.0)
    async def bulk_insert(self) -> None:
        """Bulk insert gathered emoji stats in the last minute."""
        async with self._batch_lock:
            if not self._batch_last_year:
                # there was no data to commit to the database.
                return

            # TOTAL COUNT
            transformed = [
                {"guild": guild_id, "emote": emote_id, "added": count}
                for guild_id, data in self._batch_total.items()
                for emote_id, count in data.items()
            ]
            query_total = """
                INSERT INTO ttv_emote_stats_total (broadcaster_id, emote_id, total)
                    SELECT x.broadcaster, x.emote, x.added
                    FROM jsonb_to_recordset($1::jsonb) AS
                    x(
                        broadcaster TEXT,
                        emote TEXT,
                        added INT
                    )
                ON CONFLICT (broadcaster_id, emote_id) DO UPDATE
                SET total = emote_stats_total.total + excluded.total;
            """

            # LAST YEAR COUNT
            query_last_year = """
                INSERT INTO ttv_emote_stats_last_year (emote_id, broadcaster_id, author_id, used)
                    SELECT x.emote_id, x.broadcaster_id, x.author_id, x.used
                    FROM jsonb_to_recordset($1::jsonb) AS
                    x(
                        emote_id TEXT,
                        broadcaster_id TEXT,
                        author_id TEXT,
                        used TIMESTAMP
                    )
                """
            async with self.bot.pool.acquire() as connection:
                tr = connection.transaction()
                await tr.start()

                try:
                    await connection.execute(query_total, transformed)
                    await connection.execute(query_last_year, self._batch_last_year)
                except Exception:
                    await tr.rollback()
                    raise
                else:
                    await tr.commit()

            self._batch_total.clear()
            self._batch_last_year.clear()

    @ireloop(time=datetime.time(hour=12, minute=11, second=45))
    async def clean_up_old_records(self) -> None:
        """Clean up "way too old" records from the Last Year emote usage database.

        I'm kinda afraid of running out of memory so I'm just keeping a one year records max.
        If I'm proven wrong and we can hold much more data than this - I will consider extending the database.
        But for now - we clean up the database from 1 year+ records.

        Note that this doesn't affect `emote_stats_total` in any way. Everything is correct there.
        """
        async with self._batch_lock:
            clean_up_dt = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=365)

            query = """
                    DELETE FROM emote_stats_last_year
                    WHERE used < $1::date
                """
            await self.bot.pool.execute(query, clean_up_dt)

    @commands.Component.listener(name="message")
    async def collect_emote_usage_stats(self, message: twitchio.ChatMessage) -> None:
        """Collects emote usage data in batches from twitch chat messages to be ready for database INSERT.

        Parameters
        ----------
        message: twitchio.ChatMessage
            message to filter emotes from.
        """
        if not message.text:
            return

        if message.chatter.display_name and message.chatter.display_name.lower() in const.BotsLowerName:
            # Not counting known bots
            return

        if next((x for x in message.chatter.badges if x.set_id == "bot-badge"), None):
            # Not counting bots
            return


class SevenTVManagement(IrePublicComponent):
    """Seven TV Emotes Management."""

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)

    @commands.is_moderator()
    @commands.command()
    async def add(self, ctx: IreContext, emote_id: Annotated[str, UserSearchEmoteIDConverter]) -> None:
        """Add 7TV emote."""

    @commands.is_moderator()
    @commands.command()
    async def remove(self, ctx: IreContext, emote_id: Annotated[str, UserSearchEmoteIDConverter]) -> None:
        """Remove 7TV emote."""


class SevenTVEmotesStatistics(IrePublicComponent):
    """Seven TV Emotes Statistics."""

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    for component in {
        SevenTVCyclingEmotes,
        SevenTVManagement,
        SevenTVEmotesStatistics,
    }:
        await bot.add_component(component(bot))
