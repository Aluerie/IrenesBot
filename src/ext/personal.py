"""Personal.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import random
import re
from typing import TYPE_CHECKING, override

import discord
import twitchio
from twitchio.ext import commands

from config import env
from core import Context, PersonalComponent
from shared import clock, fmt
from shared.concepts import loop, restart_task
from utils import const

if TYPE_CHECKING:
    from core import Bot

log = logging.getLogger(__name__)

ERM_PATTERN = re.compile(r"\bErm\b")
ERM_NOTIFICATION_CHANCE = 0.005
ERM_NOTIFICATION_COOLDOWN = 180

TWITCH_PURPLE = 0x9146FF
NOTIFICATION_ROLE_ID = 760082003495223298
OFFLINE_EDIT_DELAY = 11 * 60  # seconds to wait before treating the stream as truly ended
VOD_TIMESTAMP_TOLERANCE = dt.timedelta(minutes=1)  # allowance for clock skew between Twitch endpoints


class Personal(PersonalComponent):
    """Features for the developer's own Twitch channel.

    Covers chat alerts (raids, ad breaks, bans, subscriptions, first-time chatter greetings), stream reminders, the Erm
    counter and the Discord "went live" notifications. Every listener ignores events from channels other than the
    developer's own. Several listeners may subscribe to the same event, so their method names carry the feature name
    and the event is given explicitly in the decorator.

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
    reminders
        One-shot reminder tasks tied to the lifetime of a single stream.
    last_erm_notification
        When the bot last posted an Erm total in chat. Used to rate-limit the random Erm notifications.
    active_notification_messages
        Discord notification messages that still show the live stream preview, oldest first. A message is dropped from
        the list once its preview has been replaced with the offline image.
    """

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.ban_list: set[str] = set()
        self.known_chatters: set[str] = set()
        self.greeting_in_progress: set[str] = set()

        self.reminders = (
            self.reminder_to_turn_recording_on,
            self.reminder_to_stop_streaming,
        )

        self.last_erm_notification: dt.datetime = clock.utcnow()

        self.active_notification_messages: list[discord.WebhookMessage] = []

    @override
    async def component_teardown(self) -> None:
        """Cancel pending background tasks when the component is unloaded.

        Without this, the sleeping reminder and notification-edit tasks would outlive the component and fire from an
        orphaned instance after a reload.
        """
        self.cancel_reminders()
        self.edit_stale_notifications.cancel()
        await super().component_teardown()

    ####################################################################################################################
    # ALERTS
    ####################################################################################################################

    @commands.Component.listener(name="raid")
    async def raids(self, raid: twitchio.ChannelRaid) -> None:
        """Announce a raid in chat and give the raiding channel a shoutout.

        The announcement goes first because the shoutout can be rejected by Twitch (cooldowns, raider not live), and
        that failure should not cost the announcement.

        Parameters
        ----------
        raid
            The raid payload.
        """
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

        try:
            await streamer.send_shoutout(to_broadcaster=raid.from_broadcaster.id, moderator=const.UserID.Bot)
        except twitchio.HTTPException:
            log.warning("Failed to shoutout the raider %s", raid.from_broadcaster.display_name, exc_info=True)

    @commands.Component.listener(name="ad_break")
    async def ad_break(self, ad_break: twitchio.ChannelAdBreakBegin) -> None:
        """Warn chat that an ad break has started.

        The message includes the ad length and whether the ad was scheduled automatically or started manually.

        Parameters
        ----------
        ad_break
            The ad break payload.
        """
        if not self.is_dev(ad_break.broadcaster.id):
            return

        word = "automatic" if ad_break.automatic else "manual"
        human_delta = clock.human_timedelta(seconds=ad_break.duration, mode="short")
        await ad_break.respond(f"{human_delta} {word} ad starting {const.Stv.peepoAds}")

    @commands.Component.listener(name="ban")
    async def bans_timeouts(self, ban: twitchio.Ban) -> None:
        """Remember banned users so the first-message greeting can skip them.

        Parameters
        ----------
        ban
            The ban payload.
        """
        if not self.is_dev(ban.broadcaster.id):
            return

        self.ban_list.add(ban.user.id)

    @commands.Component.listener(name="message")
    async def greet_first_time_chatter(self, message: twitchio.ChatMessage) -> None:
        """Greet first-time chatters with the FirstTimeChadder treatment.

        Chatters missing from the ``ttv_chatters`` table get a greeting and are recorded there. The greeting is delayed
        by a few seconds so that auto-mod and other moderation bots can remove spam-bots first. Anyone banned during
        that window gets the LastTimeChatter emote instead and is not recorded.

        Parameters
        ----------
        message
            The chat message payload.
        """
        if not self.is_dev(message.broadcaster.id):
            return
        if message.chatter.name in const.BotsLowerName or not message.text:
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
        """Thank a new subscriber in chat.

        Parameters
        ----------
        subscription
            The subscription payload.
        """
        if not self.is_dev(subscription.broadcaster.id):
            return

        await subscription.respond(f"{subscription.user.mention} just subscribed {const.Stv.Donki} thanks")

    @commands.Component.listener(name="subscription_message")
    async def subscription_message(self, subscription_message: twitchio.ChannelSubscriptionMessage) -> None:
        """Thank a resubscriber who shared a resubscription message, mentioning their month count.

        Parameters
        ----------
        subscription_message
            The resubscription message payload.
        """
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
        """Start all stream reminders, restarting those that are already running.

        Parameters
        ----------
        online
            The stream online payload that the reminders respond to.
        """
        for reminder in self.reminders:
            restart_task(reminder, online)

    def cancel_reminders(self) -> None:
        """Cancel all stream reminders. Reminders that are not running are left alone."""
        for reminder in self.reminders:
            reminder.cancel()

    @commands.Component.listener(name="stream_online")
    async def chat_stream_start(self, online: twitchio.StreamOnline) -> None:
        """Announce the stream going live in chat and start the stream reminders.

        Reminders are started first so that a failed API call or chat message below cannot prevent them from being
        scheduled. Chat then gets the game and title, followed by an immediate checklist for the streamer.

        Parameters
        ----------
        online
            The stream online payload.
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
    async def chat_stream_end(self, offline: twitchio.StreamOffline) -> None:
        """Announce the stream going offline in chat and clean up the per-stream state.

        Cancels the pending reminders and clears ``ban_list``, since bans only matter for first-message checks within
        the current stream.

        Parameters
        ----------
        offline
            The stream offline payload.
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

        Parameters
        ----------
        online
            The stream online payload used to post the reminder.
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

        Parameters
        ----------
        online
            The stream online payload used to post the reminder.
        """
        youtube_vod_limit = 11 * 3600 + 40 * 60  # 11 hours 40 minutes
        await asyncio.sleep(youtube_vod_limit)
        await online.respond(
            f"Irene {const.Stv.ALERT} "
            f"you've been streaming for almost 12h {const.Stv.ALERT} "
            f"remember youtube vod time limit {const.Stv.ALERT} "
            f"{const.Stv.OVERWORKING} wrap it up {const.Stv.ALERT}"
        )

    ####################################################################################################################
    # ERM COUNTERS
    ####################################################################################################################

    async def fetch_erm_count(self) -> int:
        """Fetch the current Erm count from the database."""
        query = "SELECT value FROM ttv_counters WHERE name = $1"
        return await self.bot.pool.fetchval(query, "erm") or 0

    @commands.Component.listener(name="message")
    async def count_erms(self, message: twitchio.ChatMessage) -> None:
        """Count Erm emotes in chat and occasionally announce the total.

        Every message containing the emote increments the counter once. Each thousandth Erm gets a milestone
        announcement. Otherwise a short total is posted at random, at most once per three minutes.

        Parameters
        ----------
        message
            The chat message payload.
        """
        if not self.is_dev(message.broadcaster.id):
            return
        if message.chatter.name in const.BotsLowerName or not message.text:
            return
        if not ERM_PATTERN.search(message.text):
            return

        query = """
            INSERT INTO ttv_counters (name, value)
            VALUES ($1, 1)
            ON CONFLICT (name)
                DO UPDATE SET value = ttv_counters.value + 1
            RETURNING value;
        """
        erm_amount_milestone: int = await self.bot.pool.fetchval(query, "erm")

        now = clock.utcnow()
        # milestone
        if erm_amount_milestone % 1000 == 0:
            self.last_erm_notification = now
            await message.respond(
                f"{const.Stv.wow} we reached a milestone of {erm_amount_milestone} {const.Stv.Erm} in chat"
            )
            return

        # random notification/reminder
        if (
            random.random() < ERM_NOTIFICATION_CHANCE
            and (now - self.last_erm_notification).total_seconds() > ERM_NOTIFICATION_COOLDOWN
        ):
            self.last_erm_notification = now  # claim the slot before any await
            await asyncio.sleep(3)
            await message.respond(f"{await self.fetch_erm_count()} {const.Stv.Erm} in chat.")

    @commands.command(aliases=["erm"])
    async def erms(self, ctx: Context) -> None:
        """Show how many Erms chat has sent so far."""
        await ctx.send(f"{await self.fetch_erm_count()} {const.Stv.Erm} in chat.")

    ####################################################################################################################
    # DISCORD NOTIFICATION
    ####################################################################################################################

    @discord.utils.cached_property
    def stream_notif(self) -> discord.Webhook:
        """Webhook for stream notifications, or the logger webhook when the bot runs in test mode."""
        webhook_url = env.WEBHOOK_STREAM_NOTIF if not self.bot.test else env.WEBHOOK_LOGGER
        return discord.Webhook.from_url(url=webhook_url, session=self.bot.session)

    @commands.Component.listener(name="stream_online")
    async def discord_stream_start(self, online: twitchio.StreamOnline) -> None:
        """Post a "went live" notification embed to Discord.

        The embed shows the stream title, the game, a live preview and, when available, a link to the VOD of this
        stream. The sent message is remembered so that its live preview can be replaced with the offline image later.

        Parameters
        ----------
        online
            The stream online payload.
        """
        if not self.is_dev(online.broadcaster.id):
            return

        irene = await online.broadcaster.user()
        channel_info = await irene.fetch_channel_info()
        game = await channel_info.fetch_game()

        stream_url = f"https://twitch.tv/{irene.name}"

        videos = await self.bot.fetch_videos(user_id=irene.id, period="day")
        cutoff = online.started_at - VOD_TIMESTAMP_TOLERANCE
        current_vod = next((video for video in videos if video.created_at >= cutoff), None)
        current_vod_link = f"/[VOD]({current_vod.url})" if current_vod else ""

        embed = (
            discord
            .Embed(
                color=TWITCH_PURPLE,
                title=channel_info.title,
                url=stream_url,
                description=f"Playing {channel_info.game_name}\n/[Watch Stream]({stream_url}){current_vod_link}",
            )
            .set_author(
                name=f"{irene.display_name} just went live on Twitch!",
                icon_url=irene.profile_image,
                url=stream_url,
            )
            .set_thumbnail(url=game.box_art if game else irene.profile_image)
            .set_image(
                url=f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{irene.name}-1280x720.jpg"
                "?format=webp&width=720&height=405"
            )
        )

        message = await self.stream_notif.send(
            content=f"<@&{NOTIFICATION_ROLE_ID}> and chat, **`@{irene.display_name}`** just went live!",
            wait=True,
            embed=embed,
        )
        self.active_notification_messages.append(message)

    @commands.Component.listener(name="stream_offline")
    async def discord_stream_end(self, offline: twitchio.StreamOffline) -> None:
        """Schedule replacing the live previews in old notifications with the offline image.

        Every offline event restarts the delay, so a stream that keeps flapping gets its full grace period each time.

        Parameters
        ----------
        offline
            The stream offline payload.
        """
        if not self.is_dev(offline.broadcaster.id):
            return

        restart_task(self.edit_stale_notifications, offline)

    @loop(count=1)
    async def edit_stale_notifications(self, offline: twitchio.StreamOffline) -> None:
        """Replace the live preview in old notifications with the offline image.

        Waits for a while first, so a short disconnect is not treated as the end of the stream. If the stream is live
        again by then, the newest notification is left alone since it belongs to the running stream. Messages leave
        ``active_notification_messages`` one by one as they are handled, so a cancelled run does not lose the rest.

        Parameters
        ----------
        offline
            The stream offline payload.
        """
        await asyncio.sleep(OFFLINE_EDIT_DELAY)

        notifications = self.active_notification_messages
        stale = notifications[:-1] if self.bot.is_online(offline.broadcaster.id) else notifications.copy()
        if not stale:
            return

        offline_image = (await offline.broadcaster.user()).offline_image or None  # `None` removes the image
        for message in stale:
            embed = message.embeds[0]
            embed.set_image(url=offline_image)
            try:
                await message.edit(embed=embed)
            except discord.HTTPException:
                # e.g. the message was deleted, drop it anyway so it does not fail on every future run
                log.warning("Failed to edit stream notification %s", message.id, exc_info=True)
            notifications.remove(message)


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(Personal(bot))
