"""Webhook Logger.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, override

from twitchio.ext import commands

from config import env
from core import IreDevComponent
from shared import gh
from shared.concepts.discord_logs import DiscordWebhookLogs
from utils import const

if TYPE_CHECKING:
    from core import IreBot

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class LogsViaWebhook(DiscordWebhookLogs, IreDevComponent):
    """Mirroring logs to discord webhook messages.

    This cog is responsible for rate-limiting, formatting, fine-tuning and sending the log messages.
    """

    def __init__(self, bot: IreBot) -> None:
        super().__init__(env.WEBHOOK_LOGGER, bot.session)
        super(IreDevComponent, self).__init__(bot)

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
        fmt_commit = f"'{commit.emojified_title}' <{commit.short_sha2}> ({commit.utc_dt.strftime('%H:%M%p %d/%b/%y')})"
        await self.bot.irene().send_message(
            sender=self.bot.bot_id, message=f"{const.STV.hi} I reloaded myself; Commit: {fmt_commit}"
        )


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(LogsViaWebhook(bot))
