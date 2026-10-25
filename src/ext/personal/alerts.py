"""Alerts.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, override

from twitchio.ext import commands

from core import PersonalComponent
from shared import clock, fmt
from shared.concepts import loop, restart_task
from utils import const

if TYPE_CHECKING:
    import twitchio

    from core import Bot

log = logging.getLogger(__name__)


class Alerts(PersonalComponent):
    """Alerts.

    Attributes
    ----------
    ban_list
        IDs of users banned during the current stream. Lets the first-message greeting tell spam-bots apart from real
        newcomers. Cleared when the stream ends.
    known_chatters
        IDs of chatters already confirmed to exist in the ``ttv_chatters`` table. An in-memory cache that spares a
        database query for every chat message.
    greeting_in_progress
        IDs of chatters whose first-message greeting is currently being processed. Prevents duplicate greetings when a
        newcomer sends several messages in quick succession.
    stream_reminders
        One-shot reminder tasks tied to the lifetime of a single stream.
    """

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.ban_list: set[str] = set()
        self.known_chatters: set[str] = set()
        self.greeting_in_progress: set[str] = set()

        self.stream_reminders = (
            self.reminder_to_turn_recording_on,
            self.reminder_to_stop_streaming,
        )

    @override
    async def component_teardown(self) -> None:
        """Cancel pending background tasks when the component is unloaded."""
        self.cancel_reminders()
        await super().component_teardown()

    ####################################################################################################################
    # ALERTS
    ####################################################################################################################

    @commands.Component.listener(name="raid")
    async def raids(self, raid: twitchio.ChannelRaid) -> None:
        """Announce a raid in chat and give the raiding channel a shoutout."""
        if not self.is_dev(raid.to_broadcaster.id):
            return

        streamer = await raid.to_broadcaster.user()
        raider_channel_info = await raid.from_broadcaster.fetch_channel_info()

        await streamer.send_announcement(
            moderator=const.UserID.Bot,
            message=(
                f"@{raid.from_broadcaster.display_name} just raided us! "
                f'They were playing {raider_channel_info.game_name} with title "{raider_channel_info.title}". '
                f"chat be nice to raiders {const.Stv.donkHappy} raiders, feel free to raid and run."
            ),
        )

        await streamer.send_shoutout(to_broadcaster=raid.from_broadcaster.id, moderator=const.UserID.Bot)

    @commands.Component.listener(name="ad_break")
    async def ad_break(self, ad_break: twitchio.ChannelAdBreakBegin) -> None:
        """Warn chat that an ad break has started.

        The message includes the ad length and whether the ad was scheduled automatically or started manually.
        """
        if not self.is_dev(ad_break.broadcaster.id):
            return

        word = "automatic" if ad_break.automatic else "manual"
        human_delta = clock.human_timedelta(seconds=ad_break.duration, mode="short")
        await ad_break.respond(f"{human_delta} {word} ad starting {const.Stv.peepoAds}")

    @commands.Component.listener(name="ban")
    async def bans_timeouts(self, ban: twitchio.Ban) -> None:
        """Remember banned users so the first-message greeting can skip them."""
        if not self.is_dev(ban.broadcaster.id):
            return

        self.ban_list.add(ban.user.id)

    @commands.Component.listener(name="message")
    async def greet_first_time_chatter(self, message: twitchio.ChatMessage) -> None:
        """Greet first-time chatters with the FirstTimeChadder treatment.

        Chatters missing from the ``ttv_chatters`` table get a greeting and are recorded there. The greeting is delayed
        by a few seconds so that auto-mod and other moderation bots can remove spam-bots first. Anyone banned during
        that window gets the LastTimeChatter emote instead and is not recorded.
        """
        if not self.is_human_dev_message(message):
            return

        chatter_id = message.chatter.id
        if chatter_id in self.known_chatters or chatter_id in self.greeting_in_progress:
            return

        self.greeting_in_progress.add(chatter_id)  # no await between the check and the add
        try:
            query = "SELECT EXISTS (SELECT 1 FROM ttv_chatters WHERE user_id = $1)"
            if await self.bot.pool.fetchval(query, chatter_id):
                self.known_chatters.add(chatter_id)
                return

            await asyncio.sleep(4.0)  # wait for auto-mod / WizeBot to ban super-sus users
            if chatter_id in self.ban_list:
                await message.respond(const.Stv.LastTimeChatter)
                return

            query = """
                INSERT INTO ttv_chatters
                (user_id, name_lower)
                VALUES ($1, $2)
                ON CONFLICT (user_id)
                    DO NOTHING;
            """
            await self.bot.pool.execute(query, chatter_id, message.chatter.name)
            self.known_chatters.add(chatter_id)
            await message.respond(
                f"{const.Stv.FirstTimeChadder} or {const.Stv.FirstTimeDentge} "
                f"\N{WHITE QUESTION MARK ORNAMENT} {const.Stv.DankThink}"
            )
        finally:
            self.greeting_in_progress.discard(chatter_id)

    @commands.Component.listener(name="subscription")
    async def subscription(self, subscription: twitchio.ChannelSubscribe) -> None:
        """Thank a new subscriber in chat."""
        if not self.is_dev(subscription.broadcaster.id):
            return

        await subscription.respond(f"{subscription.user.mention} just subscribed {const.Stv.Donki} thanks")

    @commands.Component.listener(name="subscription_message")
    async def subscription_message(self, subscription_message: twitchio.ChannelSubscriptionMessage) -> None:
        """Thank a resubscriber who shared a resubscription message, mentioning their month count."""
        if not self.is_dev(subscription_message.broadcaster.id):
            return

        await subscription_message.respond(
            f"{subscription_message.user.mention} just subscribed for "
            f"{fmt.ordinal(subscription_message.months)} months "
            f"{const.Stv.Donki} thanks a lot"
        )

    ####################################################################################################################
    # STREAM REMINDERS
    ####################################################################################################################

    def start_reminders(self, online: twitchio.StreamOnline) -> None:
        """Start all stream reminders, restarting those that are already running."""
        for reminder in self.stream_reminders:
            restart_task(reminder, online)

    def cancel_reminders(self) -> None:
        """Cancel all stream reminders. Reminders that are not running are left alone."""
        for reminder in self.stream_reminders:
            reminder.cancel()

    @commands.Component.listener(name="stream_online")
    async def chat_stream_start(self, online: twitchio.StreamOnline) -> None:
        """Announce the stream going live in chat and start the stream reminders.

        Reminders are started first so that a failed API call or chat message below cannot prevent them from being
        scheduled. Chat then gets the game and title, followed by an immediate checklist for the streamer.
        """
        if not self.is_dev(online.broadcaster.id):
            return

        self.start_reminders(online)

        channel_info = await online.broadcaster.fetch_channel_info()
        await online.respond(
            f"Stream just started {const.Stv.FeelsBingMan} Game: {channel_info.game_name} | Title: {channel_info.title}"
        )
        await online.respond(
            f"Irene {const.Stv.ALERT} a few reminders {const.Stv.ALERT} "
            f"pin some info {const.Stv.ALERT} "
            f"start recording {const.Stv.ALERT} "
            f"Turn music on {const.Stv.ALERT} "
            f"Check if chat overlay shows emotes properly {const.Stv.ALERT}"
        )

    @commands.Component.listener(name="stream_offline")
    async def stream_end(self, offline: twitchio.StreamOffline) -> None:
        """Announce the stream going offline in chat and clean up the per-stream state.

        Cancels the pending reminders and clears ``ban_list``, since bans only matter for first-message checks within
        the current stream.
        """
        if not self.is_dev(offline.broadcaster.id):
            return

        await offline.respond(f"Stream is now offline {const.Bttv.Offline}")
        self.cancel_reminders()
        self.ban_list.clear()

    @loop(count=1)
    async def reminder_to_turn_recording_on(self, online: twitchio.StreamOnline) -> None:
        """Remind the streamer to start recording, ten minutes after going live.

        An extra nudge on top of the checklist posted in `chat_stream_start`. Cancelled by `chat_stream_end` if the
        stream goes offline before the delay is over.
        """
        await asyncio.sleep(10 * 60)
        await online.respond(
            f"Irene {const.Stv.ALERT} last reminder {const.Stv.ALERT} start recording please {const.Stv.ALERT}"
        )

    @loop(count=1)
    async def reminder_to_stop_streaming(self, online: twitchio.StreamOnline) -> None:
        """Warn the streamer that the stream is about to hit YouTube's 12-hour VOD limit.

        Fires 11 hours 40 minutes after going live, which leaves 20 minutes to wrap up. Cancelled by `chat_stream_end`
        if the stream goes offline before the delay is over.
        """
        youtube_vod_limit = 11 * 3600 + 40 * 60  # 11 hours 40 minutes
        await asyncio.sleep(youtube_vod_limit)
        await online.respond(
            f"Irene {const.Stv.ALERT} "
            f"you've been streaming for almost 12h {const.Stv.ALERT} "
            f"remember youtube vod time limit {const.Stv.ALERT} "
            f"{const.Stv.OVERWORKING} wrap it up {const.Stv.ALERT}"
        )


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(Alerts(bot))
