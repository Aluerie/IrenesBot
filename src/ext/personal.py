"""Personal.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from twitchio.ext import commands

from core import PersonalComponent
from shared import clock, fmt
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    import twitchio

    from core import Bot

log = logging.getLogger(__name__)


class Personal(PersonalComponent):
    """Personal.

    Mostly, EventSub events that are nice to have a notification in twitch chat for.
    """

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.ban_list: set[str] = set()

    ####################################################################################################################
    # ALERTS
    ####################################################################################################################

    @commands.Component.listener(name="raid")
    async def raids(self, raid: twitchio.ChannelRaid) -> None:
        """Somebody raided the channel."""
        if not self.is_dev(raid.to_broadcaster.id):
            return

        streamer = await raid.to_broadcaster.user()
        raider_channel_info = await raid.from_broadcaster.fetch_channel_info()

        await streamer.send_shoutout(to_broadcaster=raid.from_broadcaster.id, moderator=const.UserID.Bot)
        await streamer.send_announcement(
            moderator=const.UserID.Bot,
            message=(
                f"@{raid.from_broadcaster.display_name} just raided us! "
                f'They were playing {raider_channel_info.game_name} with title "{raider_channel_info.title}". '
                f"chat be nice to raiders {const.Stv.donkHappy} raiders, feel free to raid and run tho."
            ),
        )

    @commands.Component.listener(name="stream_online")
    async def stream_start(self, online: twitchio.StreamOnline) -> None:
        """Stream started (went live)."""
        if not self.is_dev(online.broadcaster.id):
            return

        channel_info = await online.broadcaster.fetch_channel_info()
        # notification
        await online.respond(
            f"Stream just started {const.Stv.FeelsBingMan} Game: {channel_info.game_name} | Title: {channel_info.title}"
        )
        # 0 minutes reminder for the streamer
        await online.respond(
            f"{online.broadcaster.mention} a few reminders {const.Stv.ALERT} "
            f"pin some info {const.Stv.ALERT} "
            f"start recording {const.Stv.ALERT} "
            f"Turn music on {const.Stv.ALERT} "
            f"Check if chat overlay shows emotes properly {const.Stv.ALERT}"
        )
        # 10 minutes reminder about some things
        if self.reminder_to_turn_recording_on.is_running():
            self.reminder_to_turn_recording_on.restart(online)
        else:
            self.reminder_to_turn_recording_on.start(online)

        # 12 hours reminder to end the stream;
        if self.reminder_to_stop_streaming.is_running():
            self.reminder_to_stop_streaming.restart(online)
        else:
            self.reminder_to_stop_streaming.start(online)

    @loop(count=1)
    async def reminder_to_turn_recording_on(self, online: twitchio.StreamOnline) -> None:
        """Reminder task to turn recording on.

        Just an extra reminder for the streamer.
        """
        await asyncio.sleep(10 * 60)
        # if stream goes offline, this task gets cancelled in `.stream_end`
        await online.respond(
            f"Irene {const.Stv.ALERT} "
            f"last reminder {const.Stv.ALERT} "
            f"start recording please {const.Stv.ALERT} "
            f'chat spam " {const.Stv.ALERT} "'
        )

    @loop(count=1)
    async def reminder_to_stop_streaming(self, online: twitchio.StreamOnline) -> None:
        """Reminder task to stop streaming after a long time.

        YouTube only allows 12 hours of VODs so let's warn ourselves just in case.
        """
        youtube_vod_limit = 11 * 3600 + 40 * 60  # 11 hours 40 minutes + 10 minute of `asyncio.sleep` above
        await asyncio.sleep(youtube_vod_limit)
        # if stream goes offline, this task gets cancelled in `.stream_end`
        await online.respond(
            f"Irene {const.Stv.ALERT} "
            f"you've been streaming for almost 12h {const.Stv.ALERT} "
            f"remember youtube vod time limit {const.Stv.ALERT} "
            f"{const.Stv.OVERWORKING} wrap it up {const.Stv.ALERT} "
        )

    @commands.Component.listener(name="stream_offline")
    async def stream_end(self, offline: twitchio.StreamOffline) -> None:
        """Stream ended (went offline)."""
        if not self.is_dev(offline.broadcaster.id):
            return

        await offline.respond(f"Stream is now offline {const.Bttv.Offline}")
        self.reminder_to_turn_recording_on.cancel()
        self.reminder_to_stop_streaming.cancel()

    @commands.Component.listener(name="ad_break")
    async def ad_break(self, ad_break: twitchio.ChannelAdBreakBegin) -> None:
        """Ad break."""
        if not self.is_dev(ad_break.broadcaster.id):
            return

        word = "automatic" if ad_break.automatic else "manual"
        human_delta = clock.human_timedelta(seconds=ad_break.duration, mode="short")
        await ad_break.respond(f"{human_delta} {word} ad starting {const.Stv.peepoAds}")

    @commands.Component.listener(name="ban")
    async def bans_timeouts(self, ban: twitchio.Ban) -> None:
        """Bans."""
        if not self.is_dev(ban.broadcaster.id):
            return

        self.ban_list.add(ban.user.id)

    @commands.Component.listener(name="message")
    async def first_message(self, message: twitchio.ChatMessage) -> None:
        """Greet first time chatters with FirstTimeChadder treatment.

        This functions filters out spam-bots that should be perma-banned right away by other features or other bots.
        """
        if not self.is_dev(message.broadcaster.id):
            return

        if not message.text:
            return

        query = "SELECT COUNT(1) FROM ttv_chatters WHERE user_id = $1"
        if await self.bot.pool.fetchval(query, message.chatter.id) == 1:
            # a known chatter
            return

        await asyncio.sleep(4.0)  # wait for auto-mod / WizeBot to ban super-sus users - 4 sec is probably enough.
        if message.chatter.id in self.ban_list:
            await message.respond(const.Stv.LastTimeChatter)
            return

        query = """
            INSERT INTO ttv_chatters
            (user_id, name_lower)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
                DO NOTHING;
        """
        await self.bot.pool.execute(query, message.chatter.id, message.chatter.name)

        await message.respond(
            f"{const.Stv.FirstTimeChadder} or {const.Stv.FirstTimeDentge} "
            f"\N{WHITE QUESTION MARK ORNAMENT} {const.Stv.DankThink}"
        )

    @commands.Component.listener(name="subscription")
    async def subscription(self, subscription: twitchio.ChannelSubscribe) -> None:
        """Subscriptions."""
        if not self.is_dev(subscription.broadcaster.id):
            return

        await subscription.respond(f"{subscription.user.mention} just subscribed {const.Stv.Donki} thanks")

    @commands.Component.listener(name="subscription_message")
    async def subscription_message(self, subscription_message: twitchio.ChannelSubscriptionMessage) -> None:
        """Subscriptions."""
        if not self.is_dev(subscription_message.broadcaster.id):
            return

        await subscription_message.respond(
            f"{subscription_message.user.mention} just subscribed for "
            f"{fmt.ordinal(subscription_message.months)} months "
            f"{const.Stv.Donki} thanks a lot"
        )


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(Personal(bot))
