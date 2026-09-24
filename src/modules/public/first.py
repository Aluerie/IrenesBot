"""
First feature.

Manages the channel point reward (usually called "First!") which only one chatter (the very first one) can redeem.

License
-------
* License: MPL-2.0, see LICENSE for more details.
* Copyright: (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import contextlib
import datetime
import logging
import re
from typing import TYPE_CHECKING, TypedDict, override

import twitchio
from discord import Embed
from twitchio.ext import commands

from core import IrePublicComponent, ireloop
from shared import errors, fmt, globs
from utils import const, guards

if TYPE_CHECKING:
    from core import IreBot, IreContext

    class FirstRedeemsRow(TypedDict):
        user_id: str
        first_times: int

    class FirstChatterRewardsQueryRow(TypedDict):
        streamer_id: str
        reward_id: str
        original_title: str


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

__all__ = ("FirstChatterChannelRewardManagement",)

DEFAULT_FIRST_REWARD_TITLE = "First!"


class FirstChatterChannelRewardManagement(IrePublicComponent):
    """Track some silly number counters of how many times this or that happened."""

    @override
    async def component_load(self) -> None:
        self.double_check.start()
        self.check_first_reward.start()
        await super().component_load()

    @override
    async def component_teardown(self) -> None:
        self.double_check.cancel()
        self.check_first_reward.cancel()
        await super().component_teardown()

    # MANAGEMENT COMMANDS

    @guards.is_broadcaster_or_dev()
    @commands.command()
    async def setup_first_reward(self, ctx: IreContext) -> None:
        """Setup First Chatter Channel Reward in the broadcaster channel."""
        query = """
            SELECT COUNT(1)
            FROM ttv_first_chatter_rewards
            WHERE streamer_id = $1;
        """
        if await self.bot.pool.fetchval(query, ctx.broadcaster.id) == 1:
            msg = "This channel already had First Chatter Channel Reward"
            raise errors.RespondWithError(msg)

        custom_reward = await ctx.broadcaster.create_custom_reward(
            title="First!",
            cost=1,
            max_per_stream=1,
            max_per_user=1,
            redemptions_skip_queue=True,
        )
        query = """
            INSERT INTO ttv_first_chatter_rewards
            (streamer_id, reward_id)
            VALUES ($1, $2)
            ON CONFLICT (streamer_id)
                DO NOTHING
            returning streamer_id
        """
        streamer_id: str | None = await self.bot.pool.fetchval(query, ctx.broadcaster.id, custom_reward.id)
        if streamer_id is None:
            msg = "This channel already has First Chatter Channel Reward"
            raise errors.RespondWithError(msg)
        await ctx.send(
            "Successfully created channel reward 'First'! If you want to edit it (e.g. text or color) - "
            "visit your creator dashboard "
            f"(dashboard.twitch.tv/u/{ctx.broadcaster.name}/viewer-rewards/channel-points/rewards)"
        )

    @guards.is_broadcaster_or_dev()
    @commands.command()
    async def fix_first_reward(self, ctx: IreContext) -> None:
        """Setup First Chatter Channel Reward in the broadcaster channel."""
        if (reward_row := await self.fetch_reward(ctx.broadcaster.id)) is None:
            msg = (
                "This stream does not have First Chatter Channel Reward set up. "
                "You can use !setup_first_reward to create it."
            )
            raise errors.RespondWithError(msg)

        await ctx.broadcaster.update_custom_reward(
            id=reward_row["reward_id"],
            max_per_user=1,
            max_per_stream=1,
        )
        await ctx.send("Successfully fixed the First Chatter Channel Reward!")

    # COMMON DATABASE REQUESTS

    async def is_reward_in_database(self, reward_id: str) -> bool:
        """Check whether the reward with `reward_id` is present in the database."""
        query = """--sql
            SELECT COUNT(1)
            FROM ttv_first_chatter_rewards
            WHERE reward_id = $1
        """
        return await self.bot.pool.fetchval(query, reward_id) == 1

    async def fetch_reward(self, streamer_id: str) -> FirstChatterRewardsQueryRow | None:
        """Fetch row for First Chatter Reward by `streamer_id`."""
        query = """
            SELECT streamer_id, reward_id, original_title
            FROM ttv_first_chatter_rewards
            WHERE streamer_id = $1;
        """
        return await self.bot.pool.fetchrow(query, streamer_id)

    # LISTENERS

    @commands.Component.listener(name="custom_reward_update")
    async def update_reward_title_in_database(self, reward: twitchio.ChannelPointsRewardUpdate) -> None:
        """Update reward title in the database."""
        match = re.search(r"^@[a-zA-Z_]+ was 1st today!$", reward.title)
        if match is not None:
            # then it's highly likely it was not a title from the user but from the bot
            # the `@Irene was 1st today!`
            return

        query = """
            UPDATE ttv_first_chatter_rewards
            SET original_title = $1
            WHERE reward_id = $2
        """
        await self.bot.pool.execute(query, reward.title, reward.id)

    @commands.Component.listener(name="custom_reward_update")
    async def validate_reward_attributes(self, reward: twitchio.ChannelPointsRewardUpdate) -> None:
        """Check if reward attributes make sense.

        This is in case the streamer changes those attributes to illogical values.
        """
        if not await self.is_reward_in_database(reward.id):
            return

        def get_response(msg: str) -> str:
            """Add message prefix and suffix to `msg`."""
            return (
                f"{reward.broadcaster.mention} settings for `First Chatter Redeem` were just changed. "
                f"{msg} "
                "Please, fix or run `!fix_first_reward`."
            )

        if reward.max_per_stream is None:
            msg = get_response("For some reason `reward.max_per_stream` was set to `None` which is wrong.")
            await reward.respond(msg)
            return
        if not reward.max_per_stream.enabled:
            msg = get_response("Are you sure you want `Limit Redemptions Per Stream` to be disabled?")
            await reward.respond(msg)
            return
        if reward.max_per_stream.value != 1:
            msg = get_response(f"Are you sure you want `Limit Redemptions Per Stream` to be {reward.max_per_stream.value}.")
            await reward.respond(msg)
            return

    @commands.Component.listener(name="custom_reward_remove")
    async def remind_reward_remove(self, reward: twitchio.ChannelPointsRewardRemove) -> None:
        """Check if the removed reward was "First Chatter Reward".

        If so we might want to remind the streamer to redo the setup.
        """
        if not await self.is_reward_in_database(reward.id):
            return

        query = """
            DELETE FROM ttv_first_chatter_rewards
            WHERE reward_id = $1;
        """
        await self.bot.pool.execute(query, reward.id)
        await reward.respond(
            f"{reward.broadcaster.mention} I've noticed you've just removed the `First Chatter Channel Reward`"
            "that was set up with this bot. If you want to recreate it, use `!setup_first_reward`."
        )

    @commands.Component.listener(name="custom_redemption_add")
    async def first_counter(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Process First Chatter Channel Point redeem.

        * Count all redeems for the reward 'First'.
        * Responds to the user.
        """
        if not await self.is_reward_in_database(redemption.reward.id):
            return

        query = """--sql
            INSERT INTO ttv_first_chatter_redeems
            (user_id, streamer_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id, streamer_id) DO
                UPDATE SET first_times = ttv_first_chatter_redeems.first_times + 1
            RETURNING first_times;
        """
        count: int = await self.bot.pool.fetchval(query, redemption.user.id, redemption.broadcaster.id)
        msg = (
            f'@{redemption.user.display_name}, gratz on your very first "First!" {const.STV.gg}'
            if count == 1
            else f"@{redemption.user.display_name}, Gratz! you've been first {count} times {const.STV.gg} {const.Global.EZ}"
        )
        await redemption.respond(msg)
        with contextlib.suppress(twitchio.HTTPException):
            await redemption.fulfill(token_for=redemption.broadcaster.id)
        await redemption.broadcaster.update_custom_reward(
            id=redemption.reward.id,
            title=f"@{redemption.user.display_name} was 1st today!",
        )

    async def helper_reset_redeem_title_to_original(
        self,
        broadcaster: twitchio.PartialUser,
        reward_id: str,
        original_title: str,
    ) -> None:
        """Helper function to reset First Chatter Reward title's to normal.

        Title gets replaces by "@User was first today!" during the streams.
        This replaces it back to the original.
        """
        first_reward = next(iter(await broadcaster.fetch_custom_rewards(ids=[reward_id])))
        intended_title = original_title or DEFAULT_FIRST_REWARD_TITLE
        if first_reward.title != intended_title:
            await first_reward.update(title=intended_title)

    @commands.Component.listener(name="stream_offline")
    async def reset_first_redeem_title(self, offline: twitchio.StreamOffline) -> None:
        """Reset the title of the "First!" redeem back to its original state.

        Currently, it should be changed when somebody redeems to "@user was first!
        """
        if reward_row := await self.fetch_reward(offline.broadcaster.id):
            await self.helper_reset_redeem_title_to_original(
                offline.broadcaster,
                reward_row["reward_id"],
                reward_row["original_title"],
            )

    @ireloop(hours=6)
    async def double_check(self) -> None:
        """Double Check the information.

        Sometimes, the bot is offline during streamer stream ends so it doesn't catch some events.
        """
        log.debug("🥇 First: Double check Task starts now.")
        await self.bot.streamers_index_ready.wait()
        query = """
            SELECT streamer_id, reward_id, original_title
            FROM ttv_first_chatter_rewards;
        """
        rows: list[FirstChatterRewardsQueryRow] = await self.bot.pool.fetch(query)
        for row in rows:
            streamer = self.bot.get_streamer(row["streamer_id"])
            if streamer.online:
                continue
            await self.helper_reset_redeem_title_to_original(
                self.bot.create_partialuser(row["streamer_id"]),
                row["reward_id"],
                row["original_title"],
            )

    @ireloop(time=[datetime.time(hour=3, minute=59)])
    async def check_first_reward(self) -> None:
        """The task that ensures the reward "First" under a specific id exists.

        Just a fool proof measure in case I randomly snap and delete it.
        """
        if datetime.datetime.now(datetime.UTC).day != 14:
            # simple way to make a task run once/month
            return

        log.debug("🥇 First: Checking if all rewards in the database exist.")
        query = """
            SELECT streamer_id, reward_id, original_title
            FROM ttv_first_chatter_rewards;
        """
        rows: list[FirstChatterRewardsQueryRow] = await self.bot.pool.fetch(query)

        for row in rows:
            partial_user = self.bot.create_partialuser(row["streamer_id"])
            first_reward = next(iter(await partial_user.fetch_custom_rewards(ids=[row["reward_id"]])))
            if not first_reward:
                content = self.bot.error_ping
                embed = Embed(
                    description=(
                        f"Looks like something wrong with streamer @{partial_user.name} ({row['streamer_id']}) "
                        'deleted "First!" channel points reward from the channel.'
                    ),
                    colour=0x345245,
                )
                await self.bot.error_webhook.send(content=content, embed=embed)

    # USER COMMANDS

    @commands.command(aliases=["first"])
    async def firsts(self, ctx: IreContext) -> None:
        """Get top5 first redeemers."""
        query = """--sql
            SELECT user_id, first_times
            FROM ttv_first_chatter_redeems
            WHERE streamer_id = $1
            ORDER BY first_times DESC
            LIMIT 5;
        """
        rows: list[FirstRedeemsRow] = await self.bot.pool.fetch(query, ctx.broadcaster.id)
        if not rows:
            msg = "This channel doesn't have `First!` feature setup."
            raise errors.RespondWithError(msg)

        content = f'{const.BTTV.DankG} Top5 "First!" redeemers: '
        rank_medals = [
            "\N{FIRST PLACE MEDAL}",
            "\N{SECOND PLACE MEDAL}",
            "\N{THIRD PLACE MEDAL}",
            globs.DIGITS[4],
            globs.DIGITS[5],
        ]
        content += " ".join(
            [
                f"{rank_medals[i]} {(await self.bot.create_partialuser(row['user_id']).user()).display_name}: "
                f"{fmt.plural(number=row['first_times']):time};"
                for i, row in enumerate(rows)
            ]
        )
        await ctx.send(content)


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(FirstChatterChannelRewardManagement(bot))
