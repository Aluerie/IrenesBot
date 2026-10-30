# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""First! redeem feature.

Manages the channel point reward (usually called "First!") which only one chatter (the very first one) can redeem.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import logging
import re
from typing import TYPE_CHECKING, TypedDict, override

import twitchio
from discord import Embed
from twitchio.ext import commands

from core import Component
from shared import clock, errors, fmt, globs
from shared.concepts import loop
from utils import const, guards

if TYPE_CHECKING:
    from core import Bot, Context

    class FirstRedeemsRow(TypedDict):
        """FirstRedeemsRow."""

        user_id: str
        first_times: int

    class FirstChatterRewardsQueryRow(TypedDict):
        """FirstChatterRewardsQueryRow."""

        streamer_id: str
        reward_id: str
        original_title: str


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


DEFAULT_FIRST_REWARD_TITLE = "First!"

# Title that the bot sets after somebody redeems the reward, i.e. "@Irene was 1st today!".
# Twitch display names can contain digits and non-ASCII characters, so we match any non-whitespace run.
BOT_REWARD_TITLE_PATTERN = re.compile(r"@\S+ was 1st today!")


class FirstChatterChannelRewardManagement(Component):
    """Manage the "First!" channel point reward: setup, validation, redeem counters and title resets."""

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
    async def setup_first_reward(self, ctx: Context) -> None:
        """Set up First Chatter Channel Reward in the broadcaster channel."""
        query = """--sql
            SELECT COUNT(1)
            FROM ttv_first_chatter_rewards
            WHERE streamer_id = $1;
        """
        if await self.bot.pool.fetchval(query, ctx.broadcaster.id) == 1:
            msg = "This channel already had First Chatter Channel Reward"
            raise errors.RespondWithError(msg)

        custom_reward = await ctx.broadcaster.create_custom_reward(
            title=DEFAULT_FIRST_REWARD_TITLE,
            cost=1,
            max_per_stream=1,
            max_per_user=1,
            redemptions_skip_queue=True,
        )
        query = """--sql
            INSERT INTO ttv_first_chatter_rewards
            (streamer_id, reward_id)
            VALUES ($1, $2)
            ON CONFLICT (streamer_id)
                DO NOTHING
            RETURNING streamer_id;
        """
        streamer_id: str | None = await self.bot.pool.fetchval(query, ctx.broadcaster.id, custom_reward.id)
        if streamer_id is None:
            msg = "This channel already has First Chatter Channel Reward"
            raise errors.RespondWithError(msg)
        await ctx.send(
            "Successfully created channel reward 'First'! If you want to edit it (e.g. text or color) - "
            "visit your creator dashboard "
            f"(dashboard.twitch.tv/u/{ctx.broadcaster.name}/viewer-rewards/channel-points/rewards)",
        )

    @guards.is_broadcaster_or_dev()
    @commands.command()
    async def fix_first_reward(self, ctx: Context) -> None:
        """Fix First Chatter Channel Reward attributes in the broadcaster channel."""
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
            WHERE reward_id = $1;
        """
        return await self.bot.pool.fetchval(query, reward_id) == 1

    async def fetch_reward(self, streamer_id: str) -> FirstChatterRewardsQueryRow | None:
        """Fetch row for First Chatter Reward by `streamer_id`."""
        query = """--sql
            SELECT streamer_id, reward_id, original_title
            FROM ttv_first_chatter_rewards
            WHERE streamer_id = $1;
        """
        return await self.bot.pool.fetchrow(query, streamer_id)

    async def fetch_all_rewards(self) -> list[FirstChatterRewardsQueryRow]:
        """Fetch rows for all First Chatter Rewards."""
        query = """--sql
            SELECT streamer_id, reward_id, original_title
            FROM ttv_first_chatter_rewards;
        """
        return await self.bot.pool.fetch(query)

    # TWITCH HELPERS

    async def fetch_twitch_reward(
        self,
        broadcaster: twitchio.PartialUser,
        reward_id: str,
    ) -> twitchio.CustomReward | None:
        """Fetch the custom reward from Twitch.

        Returns
        -------
        twitchio.CustomReward | None
            The reward or `None` if Twitch returned nothing for the `reward_id`.
        """
        rewards = await broadcaster.fetch_custom_rewards(ids=[reward_id])
        return next(iter(rewards), None)

    # LISTENERS

    @commands.Component.listener(name="custom_reward_update")
    async def update_reward_title_in_database(self, reward: twitchio.ChannelPointsRewardUpdate) -> None:
        """Update reward title in the database."""
        if BOT_REWARD_TITLE_PATTERN.fullmatch(reward.title):
            # then it's highly likely it was not a title from the user but from the bot
            # the `@Irene was 1st today!`
            return

        query = """--sql
            UPDATE ttv_first_chatter_rewards
            SET original_title = $1
            WHERE reward_id = $2;
        """
        await self.bot.pool.execute(query, reward.title, reward.id)

    @commands.Component.listener(name="custom_reward_update")
    async def validate_reward_attributes(self, reward: twitchio.ChannelPointsRewardUpdate) -> None:
        """Check if reward attributes make sense.

        This is in case the streamer changes those attributes to illogical values.
        """
        if not await self.is_reward_in_database(reward.id):
            return

        if reward.max_per_stream is None:
            problem = "For some reason `reward.max_per_stream` was set to `None` which is wrong."
        elif not reward.max_per_stream.enabled:
            problem = "Are you sure you want `Limit Redemptions Per Stream` to be disabled?"
        elif reward.max_per_stream.value != 1:
            problem = f"Are you sure you want `Limit Redemptions Per Stream` to be {reward.max_per_stream.value}."
        else:
            return

        await reward.respond(
            f"{reward.broadcaster.mention} settings for `First Chatter Redeem` were just changed. "
            f"{problem} "
            "Please, fix or run `!fix_first_reward`."
        )

    @commands.Component.listener(name="custom_reward_remove")
    async def remind_reward_remove(self, reward: twitchio.ChannelPointsRewardRemove) -> None:
        """Check if the removed reward was "First Chatter Reward".

        If so we might want to remind the streamer to redo the setup.
        """
        if not await self.is_reward_in_database(reward.id):
            return

        query = """--sql
            DELETE FROM ttv_first_chatter_rewards
            WHERE reward_id = $1;
        """
        await self.bot.pool.execute(query, reward.id)
        await reward.respond(
            f"{reward.broadcaster.mention} I've noticed you've just removed the `First Chatter Channel Reward` "
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
        name = redemption.user.display_name
        if count == 1:
            msg = f'@{name}, gratz on your very first "First!" {const.Stv.gg}'
        else:
            msg = f"@{name}, Gratz! you've been first {count} times {const.Stv.gg} {globs.TwitchEmote.EZ}"

        await redemption.respond(msg)
        with contextlib.suppress(twitchio.HTTPException):
            await redemption.fulfill(token_for=redemption.broadcaster.id)
        await redemption.broadcaster.update_custom_reward(
            id=redemption.reward.id,
            title=f"@{name} was 1st today!",
        )

    async def helper_reset_redeem_title_to_original(
        self,
        broadcaster: twitchio.PartialUser,
        reward_id: str,
        original_title: str,
    ) -> None:
        """Reset First Chatter Reward title's to normal.

        Title gets replaced by "@User was 1st today!" during the streams.
        This replaces it back to the original.

        Parameters
        ----------
        broadcaster
            The channel owner.
        reward_id
            ID of the First Chatter Reward.
        original_title
            The title to restore. Falls back to the default title if empty.
        """
        first_reward = await self.fetch_twitch_reward(broadcaster, reward_id)
        if first_reward is None:
            log.warning("🥇 First: reward %s of streamer %s was not found on Twitch.", reward_id, broadcaster.id)
            return

        intended_title = original_title or DEFAULT_FIRST_REWARD_TITLE
        if first_reward.title != intended_title:
            await first_reward.update(title=intended_title)

    @commands.Component.listener(name="stream_offline")
    async def reset_first_redeem_title(self, offline: twitchio.StreamOffline) -> None:
        """Reset the title of the "First!" redeem back to its original state.

        Currently, it should be changed when somebody redeems to "@user was 1st today!".
        """
        if reward_row := await self.fetch_reward(offline.broadcaster.id):
            await self.helper_reset_redeem_title_to_original(
                offline.broadcaster,
                reward_row["reward_id"],
                reward_row["original_title"],
            )

    @loop(hours=6)
    async def double_check(self) -> None:
        """Double Check the information.

        Sometimes, the bot is offline during streamer stream ends so it doesn't catch some events.
        """
        log.debug("🥇 First: Double check Task starts now.")
        await self.bot.streamers_index_ready.wait()

        for row in await self.fetch_all_rewards():
            try:
                if self.bot.get_streamer(row["streamer_id"]).online:
                    continue
                await self.helper_reset_redeem_title_to_original(
                    self.bot.create_partialuser(row["streamer_id"]),
                    row["reward_id"],
                    row["original_title"],
                )
            except Exception:
                # one broken channel (revoked token, deleted reward, etc.) must not stop the others
                log.exception("🥇 First: Double check failed for streamer %s.", row["streamer_id"])

    @loop(time=[dt.time(hour=3, minute=59)])
    async def check_first_reward(self) -> None:
        """Task that ensures the reward "First" under a specific id exists.

        Just a fool proof measure in case I randomly snap and delete it.
        """
        if clock.utcnow().day != 14:
            # simple way to make a task run once/month
            return

        log.debug("🥇 First: Checking if all rewards in the database exist.")

        for row in await self.fetch_all_rewards():
            partial_user = self.bot.create_partialuser(row["streamer_id"])
            try:
                first_reward = await self.fetch_twitch_reward(partial_user, row["reward_id"])
            except twitchio.HTTPException:
                log.exception("🥇 First: Failed to fetch the reward for streamer %s.", row["streamer_id"])
                continue

            if first_reward is None:
                embed = Embed(
                    description=(
                        f"Looks like something wrong with streamer {row['streamer_id']}: "
                        'the "First!" channel points reward is missing from the channel.'
                    ),
                    colour=0x345245,
                )
                await self.bot.notify_developers(embed=embed)

    # USER COMMANDS

    @commands.command(aliases=["first"])
    async def firsts(self, ctx: Context) -> None:
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
            msg = "This channel doesn't have `First!` feature set up or nobody has redeemed it yet."
            raise errors.RespondWithError(msg)

        # a single API request instead of one per row
        users = await self.bot.fetch_users(ids=[row["user_id"] for row in rows])
        names = {user.id: user.display_name for user in users}

        rank_medals = [
            "\N{FIRST PLACE MEDAL}",
            "\N{SECOND PLACE MEDAL}",
            "\N{THIRD PLACE MEDAL}",
            globs.DIGITS[4],
            globs.DIGITS[5],
        ]
        leaderboard = " ".join(
            f"{medal} {names.get(row['user_id'], row['user_id'])}: {fmt.plural(number=row['first_times']):time};"
            for medal, row in zip(rank_medals, rows, strict=False)
        )
        await ctx.send(f'{const.Bttv.DankG} Top5 "First!" redeemers: {leaderboard}')


async def setup(bot: Bot) -> None:
    """Load the extension (twitchio entry point)."""
    await bot.add_component(FirstChatterChannelRewardManagement(bot))
