"""Discord notifications..

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import TYPE_CHECKING, override

import discord
import twitchio
from twitchio.ext import commands

from config import env
from core import PersonalComponent
from shared.concepts import loop, restart_task

if TYPE_CHECKING:
    from core import Bot

log = logging.getLogger(__name__)


TWITCH_PURPLE = 0x9146FF
NOTIFICATION_ROLE_ID = 760082003495223298
OFFLINE_EDIT_DELAY = 11 * 60  # seconds to wait before treating the stream as truly ended
VOD_TIMESTAMP_TOLERANCE = dt.timedelta(minutes=1)  # allowance for clock skew between Twitch endpoints


class DiscordNotifications(PersonalComponent):
    """Discord notifications about the developer's Twitch stream.

    Posts a "went live" embed when the stream starts. Once the stream has been offline for a while, the live preview in
    old embeds is replaced with the channel's offline image.

    Attributes
    ----------
    active_notification_messages
        Discord notification messages that still show the live stream preview, oldest first. A message is dropped from
        the list once its preview has been replaced with the offline image.
    """

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)

        self.active_notification_messages: list[discord.WebhookMessage] = []

    @override
    async def component_teardown(self) -> None:
        """Cancel pending background tasks when the component is unloaded."""
        self.edit_stale_notifications.cancel()
        await super().component_teardown()

    ####################################################################################################################
    # DISCORD NOTIFICATION
    ####################################################################################################################

    @discord.utils.cached_property
    def stream_notif(self) -> discord.Webhook:
        """Webhook for stream notifications, or the logger webhook when the bot runs in test mode."""
        webhook_url = env.WEBHOOK_STREAM_NOTIF if not self.bot.test else env.WEBHOOK_LOGGER
        return discord.Webhook.from_url(url=webhook_url, session=self.bot.session)

    @commands.Component.listener(name="stream_online")
    async def send_notification(self, online: twitchio.StreamOnline) -> None:
        """Post a "went live" notification embed to Discord.

        The embed shows the stream title, the game, a live preview and, when available, a link to the VOD of this
        stream. The sent message is remembered so that its live preview can be replaced with the offline image later.
        """
        if not self.is_dev(online.broadcaster.id):
            return

        irene = await online.broadcaster.user()
        channel_info = await irene.fetch_channel_info()
        game = await channel_info.fetch_game()

        stream_url = f"https://twitch.tv/{irene.name}"

        try:
            videos = await self.bot.fetch_videos(user_id=irene.id, period="day")
        except twitchio.HTTPException:
            log.warning("Failed to fetch videos for the stream notification", exc_info=True)
            videos = []
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
    await bot.add_component(DiscordNotifications(bot))
