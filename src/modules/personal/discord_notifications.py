from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import discord
from twitchio.ext import commands

from config import env
from core import IrePersonalComponent

if TYPE_CHECKING:
    import twitchio

    from core import IreBot

log = logging.getLogger(__name__)


class DiscordNotifications(IrePersonalComponent):
    """Discord Notifications.

    Sends messages with @StreamerLover role ping in my small discord server.
    """

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        # it's a list just in case my internet goes crazy and we trigger multiple notifications in a row;
        self.active_notification_messages: list[discord.WebhookMessage] = []

    @discord.utils.cached_property
    def notification_webhook(self) -> discord.Webhook:
        """A shortcut to error webhook."""
        webhook_url = env.WEBHOOK_STREAM_NOTIFS if not self.bot.subset_mode else env.WEBHOOK_LOGGER
        return discord.Webhook.from_url(url=webhook_url, session=self.bot.session)

    @commands.Component.listener(name="stream_online")
    async def stream_start(self, online: twitchio.StreamOnline) -> None:
        """Stream started (went live)."""
        if not self.is_dev(online.broadcaster.id):
            return

        irene = await online.broadcaster.user()
        channel_info = await irene.fetch_channel_info()
        game = await channel_info.fetch_game()

        stream_url = f"https://twitch.tv/{irene.name}"
        current_vod = next(iter(await self.bot.fetch_videos(user_id=irene.id, period="day")), None)
        current_vod_link = f"/[VOD]({current_vod.url})" if current_vod else ""
        self.active_notification_messages.append(
            await self.notification_webhook.send(
                content=f"<@&760082003495223298> and chat, **`@{irene.display_name}`** just went live!",
                wait=True,
                embed=discord.Embed(
                    color=0x9146FF,
                    title=f"{channel_info.title}",
                    url=stream_url,
                    description=(f"Playing {channel_info.game_name}\n/[Watch Stream]({stream_url}){current_vod_link}"),
                )
                .set_author(
                    name=f"{irene.display_name} just went live on Twitch!",
                    icon_url=irene.profile_image,
                    url=stream_url,
                )
                .set_thumbnail(url=game.box_art if game else irene.profile_image)
                .set_image(
                    url=(
                        # Live preview URL
                        f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{irene.display_name}-1280x720.jpg"
                        "?format=webp&width=720&height=405"
                    ),
                ),
            )
        )

    @commands.Component.listener("stream_offline")
    async def twitch_tv_offline_edit_notification(self, offline: twitchio.StreamOffline) -> None:
        """Starts the task to edit the notification message."""
        if not self.is_dev(offline.broadcaster.id):
            return

        await asyncio.sleep(11 * 60)
        messages = (
            self.active_notification_messages[:-1]
            if self.bot.is_online(offline.broadcaster.id)
            else self.active_notification_messages
        )
        for message in messages:
            embed = message.embeds[0]
            embed.set_image(url=(await offline.broadcaster.user()).offline_image)
            await message.edit(embed=embed)


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(DiscordNotifications(bot))
