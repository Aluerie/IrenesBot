"""
Seven TV Public Features.

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
import re
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Annotated, Any, TypedDict, override

import asyncpg
import twitchio
from stv_event_api import SevenTVWebSocket  # pyright: ignore[reportMissingTypeStubs]
from stv_event_api.models import (  # pyright: ignore[reportMissingTypeStubs]
    Dispatch,
    EventType,
    ResponseTypes,
    SubscriptionCondition,
    SubscriptionData,
)
from twitchio.ext import commands

from core import IrePublicComponent, ireloop
from shared import errors, fuzzy
from shared.concepts.logs import PrefixLoggerAdapter
from shared.globs import DIGITS
from shared.seven_tv_gql.exceptions import EmoteNotFoundInSetError
from shared.seven_tv_gql.models import PartialEmote, PartialEmoteSet
from utils import const, guards

if TYPE_CHECKING:
    from core import IreBot, IreContext
    from shared.seven_tv_gql import GraphQL7TVClient

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


log = PrefixLoggerAdapter(logging.getLogger(__name__), "🤯")
log.setLevel(logging.DEBUG)

type PartialEmoteAndAlias = tuple[PartialEmote, str | None]


def regex_to_partial_emote(stv_gql: GraphQL7TVClient, emote_id_or_link: str) -> PartialEmote:
    """A function to convert a 7TV emote link to an emote_id.

    Does not do anything if the user input is already an emote_id.
    If no emote_id is provided then it errors out.
    """
    search = re.search(
        r"(?:https?:\/\/(?:www\.)?7tv\.app\/emotes\/)?(?P<emote_id>[0-7][0-9A-HJKMNP-TV-Z]{25})",
        emote_id_or_link,
    )
    if search is None:
        msg = "Bad <emote_id_or_link>, check the input"
        raise errors.BadUserInputError(msg)
    return PartialEmote(stv_gql, search["emote_id"])


async def parse_or_search_emote(
    stv_gql: GraphQL7TVClient, user_input: str, broadcaster_id: str | None = None
) -> PartialEmoteAndAlias:
    """Get emote_id from `user_input`.

    Accepts
    *
    """
    split = user_input.split()
    if len(split) > 2:
        # More than 2 words = bad
        msg = "Bad Input; I require '<emote_link_or_id> <optional_emote_alias>' - no extra words"
        raise errors.RespondWithError(msg)
    if len(split) <= 0:
        # 0 words = why
        msg = "Bad Input; why would you type an empty text?"
        raise errors.RespondWithError(msg)

    # Either
    # 2 words - 'emote_id_link_or_name + emote_alias' were provided
    # 1 word - just 'emote_id_link_or_name'
    try:
        emote_alias = split[1]
    except IndexError:
        emote_alias = None

    emote_id_link_or_name = split[0]
    try:
        # try parsing `emote_id`
        partial_emote = regex_to_partial_emote(stv_gql, emote_id_link_or_name)
    except errors.BadUserInputError:
        # `emote_name` was provided to search
        if broadcaster_id:
            # search within the broadcaster
            partial_user = stv_gql.create_partial_user(broadcaster_id)
            partial_emote = await partial_user.search_emote(emote_id_link_or_name)
        else:
            # search top globally
            partial_emote = await stv_gql.search_emote(emote_id_link_or_name)

    return (partial_emote, emote_alias)


class UserSearchEmoteConverter(commands.Converter[PartialEmoteAndAlias]):
    """Seven TV Emote Converter.

    Converts user_input from `str` type into 7TV emote_id.
    """

    @override
    async def convert(self, ctx: IreContext, user_input: str) -> PartialEmoteAndAlias:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Convert `user_input` to 7TV emote_id."""
        return await parse_or_search_emote(ctx.bot.stv, user_input, ctx.broadcaster.id)


class GlobalSearchEmoteConverter(commands.Converter[PartialEmoteAndAlias]):
    """Seven TV Emote Converter.

    Converts user_input from `str` type into 7TV emote_id.
    """

    @override
    async def convert(self, ctx: IreContext, user_input: str) -> PartialEmoteAndAlias:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Convert `user_input` to 7TV emote_id."""
        return await parse_or_search_emote(ctx.bot.stv, user_input)


class SevenTVFeatures(IrePublicComponent):
    """Cycling Emotes."""

    EMOTE = "xd"

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

            # log.debug("7TV WebSocket %s", data)

            if data.body.pulled:
                # Emote Deleted
                for pulled in data.body.pulled:
                    query = "DELETE FROM ttv_stv_cycle_emotes WHERE emote_id = $1 AND emote_set_id = $2;"
                    emote_id: str = pulled.old_value["id"]  # pyright: ignore[reportOptionalSubscript, reportUnknownVariableType]
                    emote_set_id = data.body.id

                    await self.bot.pool.execute(query, emote_id, emote_set_id)  # pyright: ignore[reportUnknownArgumentType]

        self.stv_ws = SevenTVWebSocket(callback=ws_callback, websocket_url="wss://events.7tv.io/v3/")

    async def stv_ws_subscribe(self, emote_set_id: str) -> None:
        """Make 7TV WebSocket Subscription."""
        condition = SubscriptionCondition(object_id=emote_set_id)  # your emote-set id
        subscription = SubscriptionData(subscription_type=EventType.EMOTE_SET_ALL, condition=condition)
        await self.stv_ws.subscribe(subscription_data=subscription)

    async def stv_ws_multi_subscribe(self) -> None:
        """Make 7TV WebSocket Subscriptions."""
        query = "SELECT DISTINCT emote_set_id FROM ttv_stv_users;"
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
        await self.stv_ws.close()
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
        query = "SELECT reward_id FROM ttv_stv_cycle_rewards"
        self.reward_ids_cache = {r for (r,) in await self.bot.pool.fetch(query)}

    @stv.group(name="cycle")
    async def stv_cycle(self, ctx: IreContext) -> None:
        """Group command for `!7tv cycle`.

        These commands manage 7tv cycling emotes and channel points reward.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

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
            INSERT INTO ttv_stv_cycle_rewards
            (broadcaster_id, reward_id, emote_limit, emote_set_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (broadcaster_id)
                DO NOTHING
            returning broadcaster_id
        """
        broadcaster_id: str | None = await self.bot.pool.fetchval(
            query,
            ctx.broadcaster.id,
            custom_reward.id,
            emote_limit,
            partial_emote_set.id,
        )
        if broadcaster_id is None:
            msg = "This channel already has 7TV emote cycle channel reward"
            raise errors.RespondWithError(msg)

        await self.fill_known_rewards()
        await ctx.send(
            f"Created a 7tv emote cycle channel points reward {const.STV.DankApprove} "
            "PS. if you want to edit it (e.g. text or color) - visit your creator dashboard "
            f"(dashboard.twitch.tv/u/{ctx.broadcaster.name}/viewer-rewards/channel-points/rewards). "
            "Just don't remove `Require Viewer to Enter Text`, please."
        )
        await self.stv_ws_subscribe(partial_emote_set.id)

    @guards.is_broadcaster_or_dev()
    @stv_cycle.command(name="remove", aliases=["delete"])
    async def stv_cycle_remove(self, ctx: IreContext, emote_id: Annotated[str, UserSearchEmoteConverter]) -> None:
        """Remove an emote from the cycling list.

        Useful when a streamer wants an emote to stop from being cycled out.
        """
        query = "DELETE FROM ttv_stv_cycle_emotes WHERE emote_id = $1 AND broadcaster_id = $2"
        await self.bot.pool.execute(query, emote_id, ctx.broadcaster.id)
        await ctx.send(f"The {emote_id} was removed from the cycling emote list {const.STV.DonkCrayon}")

    @stv_cycle.command(name="status")
    async def stv_cycle_status(self, ctx: IreContext) -> None:
        """Get 7TV Cycling emote channel points reward's status."""
        query = """
            SELECT r.reward_id,
                r.emote_limit,
                (SELECT COUNT(*)
                    FROM ttv_stv_cycle_emotes e
                    WHERE e.broadcaster_id = r.broadcaster_id) AS emote_count,
                u.emote_set_id
            FROM ttv_stv_cycle_rewards r
                    JOIN ttv_stv_users u ON u.broadcaster_id = r.broadcaster_id
            WHERE u.broadcaster_id = $1;
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
            raise errors.SomethingWentWrongError(msg)

        content = (
            f"title={reward.title} cost={reward.cost} reward_id={row['reward_id']} emote_limit={row['emote_limit']} "
            f"emote_count={row['emote_count']} emote_set_id={row['emote_set_id']}"
        )
        await ctx.send(content)

    @guards.is_broadcaster_or_dev()
    @stv_cycle.command(name="limit")
    async def stv_cycle_limit(self, ctx: IreContext, new_limit: int) -> None:
        """Change 7TV Cycling emote channel points reward's limit."""
        query = """
            UPDATE ttv_stv_cycle_rewards
            SET emote_limit = $1
            WHERE broadcaster_id = $2
            RETURNING (SELECT emote_limit FROM ttv_stv_cycle_rewards WHERE broadcaster_id = $2);
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
            INSERT INTO ttv_stv_cycle_rewards
                (broadcaster_id, reward_id)
            VALUES ($1, $2)
            ON CONFLICT(broadcaster_id)
                DO UPDATE SET reward_id = $2;
        """
        await self.bot.pool.execute(query, ctx.broadcaster.id, find.id)
        await self.fill_known_rewards()
        await ctx.send(f"Attached cycling emotes reward to the channel points redeem `{find.title}` ({find.id})")

    @commands.Component.listener(name="custom_redemption_add")
    async def channel_points_redeem(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Somebody redeemed a custom channel points reward."""
        if redemption.reward.id not in self.reward_ids_cache:
            return

        if self.is_dev(redemption.user.id):
            # Refund the points for Irene because you know, testing costs :D
            await redemption.refund(token_for=redemption.broadcaster.id)

        log.debug(
            "User @%s (%s) requested cycle-emote at broadcaster @%s (%s) with input: '%s'",
            redemption.user.display_name,
            redemption.user.id,
            redemption.broadcaster.display_name,
            redemption.broadcaster.id,
            redemption.user_input,
        )

        # Step 1. Parse User Input

        emote, alias = await parse_or_search_emote(self.bot.stv, redemption.user_input)
        log.debug("Parsed user input: emote_id=%s emote_alias=%s", emote.id, alias)

        # Step 2. Get Emote Set

        partial_emote_set = PartialEmoteSet(
            self.bot.stv, emote_set_id=await self.select_emote_set_id(redemption.broadcaster.id)
        )
        log.debug("Operating on emote_set #%s", partial_emote_set.id)

        # Step 3. Remove emote(-s) if above the limit
        query = """
            SELECT tce2.emote_id
            FROM ttv_stv_cycle_emotes tce2
            WHERE tce2.broadcaster_id = $1
                AND tce2.emote_set_id = $2
            ORDER BY tce2.added_at DESC
            OFFSET (
                SELECT tcer.emote_limit - 1
                FROM ttv_stv_cycle_rewards tcer
                WHERE tcer.broadcaster_id = $1
            )
        """
        emote_ids_to_remove: list[str] = [
            r for (r,) in await self.bot.pool.fetch(query, redemption.broadcaster.id, partial_emote_set.id)
        ]
        log.debug("Removing emotes #%s", emote_ids_to_remove)

        for emote_id_to_remove in emote_ids_to_remove:
            try:
                emote_name_to_remove: str = await partial_emote_set.fetch_emote_alias(emote_id=emote_id_to_remove)
                await partial_emote_set.remove_emote(emote_id=emote_id_to_remove)
            except EmoteNotFoundInSetError:
                log.debug("Emote Not Found #%s - skipping", emote_id_to_remove)
            else:
                # await redemption.respond(f"Removed {emote_name_to_remove} ({get_seven_tv_link(emote_id_to_remove)})")
                log.debug("Removed emote %s (#%s)", emote_name_to_remove, emote_id_to_remove)

        # Step 4. Add the requested emote
        await partial_emote_set.add_emote(emote_id=emote.id, emote_alias=alias)
        log.debug("Added emote #%s", emote.id)

        query = """
            INSERT INTO ttv_stv_cycle_emotes
            (emote_id, broadcaster_id, emote_set_id, requested_by)
            VALUES ($1, $2, $3, $4)
        """
        await self.bot.pool.execute(query, emote.id, redemption.broadcaster.id, partial_emote_set.id, redemption.user.id)

        result = f"Added '{alias}' ({emote.url()}) {const.STV.DonkCrayon}"
        log.info(result)
        # await redemption.respond(result)
        with contextlib.suppress(twitchio.HTTPException):
            await redemption.fulfill(token_for=redemption.broadcaster.id)

    #########################################################################################################################
    # DEVELOPER TESTING COMMANDS                                                                                            #
    #########################################################################################################################

    @guards.is_dev()
    @commands.command()
    async def balls(self, ctx: IreContext) -> None:
        """Balls."""
        # cSpell: disable-next-line
        content = "Blue 01J8FC6EN0000DNWJ3ST67HH38 Teal 01J8FCA6RR0004HJ8DYSFE2PF2 Purple 01J8FCAY6R0006NP3M7JY4GDAA"
        await ctx.send(content)

    @guards.is_dev()
    @commands.command(aliases=["dev_reset_cycle"])
    async def dev_cycle_reset(self, ctx: IreContext) -> None:
        """Developer command for temporary reset / testing.

        This
        * sets @Irene's `emote_limit` to 2;
        * removes all current @Irene's cycling emotes;
        * removes color emotes (Blue, Teal, Yellow) from Irene's active emote set;
        """
        query = "UPDATE ttv_stv_cycle_rewards SET emote_limit = $1 WHERE broadcaster_id = $2;"
        await self.bot.pool.execute(query, 2, const.UserID.Irene)

        query = "DELETE FROM ttv_stv_cycle_emotes tce WHERE tce.broadcaster_id = $1;"
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
            with contextlib.suppress(EmoteNotFoundInSetError):
                partial_emote_set = ctx.bot.stv.create_partial_emote_set(const.SevenTV.IRENE_EMOTE_SET_ID)
                await partial_emote_set.remove_emote(emote_id)
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

    #########################################################################################################################
    # 7TV EMOTE MANAGEMENT                                                                                                  #
    #########################################################################################################################

    @guards.is_broadcaster_or_dev()
    @commands.command()
    async def add(
        self, ctx: IreContext, *, emote_and_alias: Annotated[PartialEmoteAndAlias, GlobalSearchEmoteConverter]
    ) -> None:
        """Add 7TV emote."""
        await ctx.send(str(emote_and_alias))

    @guards.is_broadcaster_or_dev()
    @commands.command()
    async def remove(
        self, ctx: IreContext, *, emote_and_alias: Annotated[PartialEmoteAndAlias, UserSearchEmoteConverter]
    ) -> None:
        """Remove 7TV emote."""
        await ctx.send(str(emote_and_alias))

    #########################################################################################################################
    # 7TV EDITOR STATUS / ACCEPT                                                                                            #
    #########################################################################################################################

    @guards.is_broadcaster_or_dev()
    @stv.group(name="editor")
    async def stv_editor(self, ctx: IreContext) -> None:
        """Editor."""
        await ctx.group_default_response()

    @stv_editor.command(name="status", aliases=["check"])
    async def stv_editor_status(self, ctx: IreContext) -> None:
        """Status."""
        partial_user = ctx.bot.stv.create_partial_user(ctx.broadcaster.id)
        editor_for = await partial_user.check_bot_editor()

        if not editor_for.is_enough_permissions:
            content = "7tv editor invite doesn't have required permissions (it needs 'Emote Sets > Manage')"
        elif editor_for.state != "ACCEPTED":
            content = (
                f"7tv editor invite permissions are okay, invite state={editor_for.state}, "
                f"please use '{ctx.prefix}7tv editor accept' command to make the bot accept it"
            )
        else:
            content = "7tv editor invite is accepted and permissions are good"
        await ctx.send(content)

    @stv_editor.command(name="guide")
    async def stv_editor_guide(self, ctx: IreContext) -> None:
        """Guide."""
        content = (
            f"{DIGITS[1]} Go to 7tv.app/settings/editors "
            f"{DIGITS[2]} Add Editor > @IrenesBot, make sure 'Emote Sets > Manage' permission is given "
            f"{DIGITS[3]} Use '{ctx.prefix}7tv editor accept' command to make the bot accept the editor role "
        )
        await ctx.send(content)

    @stv_editor.command(name="accept")
    async def stv_editor_accept(self, ctx: IreContext) -> None:
        """Accept."""
        partial_user = ctx.bot.stv.create_partial_user(ctx.broadcaster.id)
        res = await partial_user.accept_editor()
        insert_response = await self.insert_into_to_stv_users(ctx.broadcaster.id)
        content = f"Just {res.lower()} your 7TV editor request; also {insert_response}"
        await ctx.send(content)

    async def insert_into_to_stv_users(self, broadcaster_id: str, emote_set_id: str | None = None) -> str:
        """Add to `stv_users` table."""
        partial_user = self.bot.stv.create_partial_user(broadcaster_id)
        user_info = await partial_user.fetch_info()

        query = """
            INSERT INTO ttv_stv_users
                (broadcaster_id, stv_user_id, emote_set_id)
            VALUES ($1, $2, $3)
            ON CONFLICT(broadcaster_id)
                DO UPDATE SET stv_user_id  = $2,
                            emote_set_id = $3;
        """
        if emote_set_id and emote_set_id != user_info.active_emote_set_id:
            # we need to fetch its name
            emote_set_info = await self.bot.stv.create_partial_emote_set(emote_set_id).fetch_info()
            emote_set_name = emote_set_info.name
        else:
            emote_set_name = user_info.active_emote_set_name
            emote_set_id = user_info.active_emote_set_id
        await self.bot.pool.execute(query, broadcaster_id, user_info.id, emote_set_id)
        return f"linked bot's 7tv features to your '{emote_set_name}' emote set ({emote_set_id})"

    #########################################################################################################################
    # 7TV EMOTESET                                                                                                          #
    #########################################################################################################################

    @guards.is_broadcaster_or_dev()
    @stv.group(name="emoteset")
    async def stv_emoteset(self, ctx: IreContext) -> None:
        """Editor."""
        await ctx.group_default_response()

    @stv_emoteset.command(name="attach")
    async def stv_emoteset_attach(self, ctx: IreContext, emote_set_id: str | None = None) -> None:
        """Link."""
        insert_response = await self.insert_into_to_stv_users(ctx.broadcaster.id, emote_set_id=emote_set_id)
        await ctx.send(f"Successfully {insert_response}")

    async def select_emote_set_id(self, broadcaster_id: str) -> str:
        """Select emote set id."""
        query = "SELECT emote_set_id FROM ttv_stv_users WHERE broadcaster_id = $1;"
        emote_set_id: str | None = await self.bot.pool.fetchval(query, broadcaster_id)
        if emote_set_id is None:
            msg = "7tv features are not linked to any emote set"
            raise errors.RespondWithError(msg)
        return emote_set_id

    @stv_emoteset.command(name="status")
    async def stv_emoteset_status(self, ctx: IreContext) -> None:
        """Status."""
        emote_set_id = await self.select_emote_set_id(ctx.broadcaster.id)
        await ctx.send(f"emote_set_id={emote_set_id}")


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(SevenTVFeatures(bot))
