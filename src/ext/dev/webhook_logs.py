# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Webhook Logger."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from twitchio.ext import commands

from config import env
from core import DevComponent
from shared import fmt, gh
from shared.concepts.discord_logs import DiscordWebhookLogs
from utils import const

if TYPE_CHECKING:
    from core import Bot


class LogsViaWebhook(DiscordWebhookLogs, DevComponent):
    """Mirroring logs to discord webhook messages.

    This cog is responsible for rate-limiting, formatting, fine-tuning and sending the log messages.
    """

    def __init__(self, bot: Bot) -> None:
        super().__init__(env.WEBHOOK_LOGGER, bot.session)
        super(DevComponent, self).__init__(bot)

        self.extra_exact_avatar_mapping: dict[str, str] = {
            "core.bot": "https://i.imgur.com/6XZ8Roa.png",  # lady Noir
        }

    @override
    async def component_load(self) -> None:
        await self.load()
        await super().component_load()

    @override
    async def component_teardown(self) -> None:
        await self.teardown()
        await super().component_teardown()

    @commands.Component.listener(name="ready")
    async def announce_reloaded(self) -> None:
        """Announce that bot is successfully reloaded/restarted."""
        commit = gh.get_last_commit()
        message = (
            f"{const.Stv.hi} I reloaded myself: <{commit.short_sha2}> "
            f"({commit.utc_dt:%H:%M %d/%b/%y} UTC) {commit.emojified_full_title}"
        )
        await self.bot.irene().send_message(
            sender=self.bot.bot_id, message=fmt.shorten(message, const.MAX_MESSAGE_LENGTH)
        )


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(LogsViaWebhook(bot))
