from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING, Any

from twitchio.ext import commands

from core import IrePersonalComponent, ireloop
from shared import fmt
from utils import const

if TYPE_CHECKING:
    import twitchio

    from core import IreBot

log = logging.getLogger(__name__)


class Alerts(IrePersonalComponent):
    """Twitch Chat Alerts.

    Mostly, EventSub events that are nice to have a notification in twitch chat for.
    """

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.ban_list: set[str] = set()

    # SECTION 1.
    # Channel Points beta test event (because it's the easiest event to test out)

    @commands.Component.listener(name="custom_redemption_add")
    async def channel_points_redeem(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Somebody redeemed a custom channel points reward."""
        if not self.is_dev(redemption.broadcaster.id):
            return

        # just testing
        print(f"{redemption.user.display_name} redeemed {redemption.reward.title}.")  # noqa: T201

    # SECTION 2
    # Actual events

    # Turn it off for a foreseeable future, anonymized follows are better.
    # @commands.Component.listener(name="follow")
    async def follows(self, follow: twitchio.ChannelFollow) -> None:
        """Somebody followed the channel."""
        if not self.is_dev(follow.broadcaster.id):
            return

        random_phrase = random.choice(
            ["welcome in", "I appreciate it", "enjoy your stay", "nice to see you", "enjoy the show"]
        )
        random_emote = random.choice(
            [const.STV.donkHappy, const.BTTV.PogU, const.STV.dankHey, const.STV.donkHey, const.BTTV.peepoHey, const.STV.Hey]
        )
        await follow.respond(f"@{follow.user.display_name} just followed! Thanks, {random_phrase} {random_emote}")

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
                f"chat be nice to raiders {const.STV.donkHappy} raiders, feel free to raid and run tho."
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
            f"Stream just started {const.STV.FeelsBingMan} Game: {channel_info.game_name} | Title: {channel_info.title}"
        )
        # 0 minutes reminder for the streamer
        await online.respond(
            f"{online.broadcaster.mention} a few reminders {const.STV.ALERT} "
            f"pin some info {const.STV.ALERT} "
            f"start recording {const.STV.ALERT} "
            f"Turn music on {const.STV.ALERT} "
            f"Check if chat overlay shows emotes properly {const.STV.ALERT}"
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

    @ireloop(count=1)
    async def reminder_to_turn_recording_on(self, online: twitchio.StreamOnline) -> None:
        """Reminder task to turn recording on.

        Just an extra reminder for the streamer.
        """
        await asyncio.sleep(10 * 60)
        # if stream goes offline, this task gets cancelled in `.stream_end`
        await online.respond(
            f"Irene {const.STV.ALERT} "
            f"last reminder {const.STV.ALERT} "
            f"start recording please {const.STV.ALERT} "
            f'chat spam " {const.STV.ALERT} "'
        )

    @ireloop(count=1)
    async def reminder_to_stop_streaming(self, online: twitchio.StreamOnline) -> None:
        """Reminder task to stop streaming after a long time.

        YouTube only allows 12 hours of VODs so let's warn ourselves just in case.
        """
        youtube_vod_limit = 11 * 3600 + 40 * 60  # 11 hours 40 minutes + 10 minute of `asyncio.sleep` above
        await asyncio.sleep(youtube_vod_limit)
        # if stream goes offline, this task gets cancelled in `.stream_end`
        await online.respond(
            f"Irene {const.STV.ALERT} "
            f"you've been streaming for almost 12h {const.STV.ALERT} "
            f"remember youtube vod time limit {const.STV.ALERT} "
            f"{const.STV.OVERWORKING} wrap it up {const.STV.ALERT} "
        )

    @commands.Component.listener(name="stream_offline")
    async def stream_end(self, offline: twitchio.StreamOffline) -> None:
        """Stream ended (went offline)."""
        if not self.is_dev(offline.broadcaster.id):
            return

        await offline.respond(f"Stream is now offline {const.BTTV.Offline}")
        self.reminder_to_turn_recording_on.cancel()
        self.reminder_to_stop_streaming.cancel()

    @commands.Component.listener(name="ad_break")
    async def ad_break(self, ad_break: twitchio.ChannelAdBreakBegin) -> None:
        """Ad break."""
        if not self.is_dev(ad_break.broadcaster.id):
            return

        word = "automatic" if ad_break.automatic else "manual"
        human_delta = fmt.timedelta_to_words(seconds=ad_break.duration, fmt=fmt.TimeDeltaFormat.Short)
        await ad_break.respond(f"{human_delta} {word} ad starting {const.STV.peepoAds}")

        # this is pointless probably
        # await asyncio.sleep(payload.duration)
        # await channel.send("Ad break is over")

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

        query = """--sql
            SELECT COUNT(1)
            FROM ttv_chatters
            WHERE user_id = $1
        """
        if await self.bot.pool.fetchval(query, message.chatter.id) == 1:
            # if in database: a known chatter
            return

        await asyncio.sleep(4.0)  # wait for auto-mod / WizeBot to ban super-sus users - 4 sec is probably enough.
        if message.chatter.id in self.ban_list:
            await message.respond(const.STV.LastTimeChatter)
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
            f"{const.STV.FirstTimeChadder} or {const.STV.FirstTimeDentge} "
            f"\N{WHITE QUESTION MARK ORNAMENT} {const.STV.DankThink}"
        )

    @commands.Component.listener(name="subscription")
    async def subscription(self, subscription: twitchio.ChannelSubscribe) -> None:
        """Subscriptions."""
        if not self.is_dev(subscription.broadcaster.id):
            return

        await subscription.respond(f"{subscription.user.mention} just subscribed {const.STV.Donki} thanks")

    @commands.Component.listener(name="subscription_message")
    async def subscription_message(self, subscription_message: twitchio.ChannelSubscriptionMessage) -> None:
        """Subscriptions."""
        if not self.is_dev(subscription_message.broadcaster.id):
            return

        await subscription_message.respond(
            f"{subscription_message.user.mention} just subscribed for {fmt.ordinal(subscription_message.months)} months "
            f"{const.STV.Donki} thanks a lot"
        )


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(Alerts(bot))
