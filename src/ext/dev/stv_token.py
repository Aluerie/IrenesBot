# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""7TV token expiry reminders.

7TV sessions hard-expire 30 days after login with no way to refresh them,
so the bot reminds the developers a few days in advance to submit a new token.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, override

from discord import Embed
from loguru import logger
from twitchio.ext import commands

from core import DevComponent
from core.stv_token import STV_TOKEN_PAGE_PATH
from shared import clock
from shared.concepts import loop

if TYPE_CHECKING:
    from core import Bot, Context


WARN_BEFORE = dt.timedelta(days=3)


class StvTokenReminder(DevComponent):
    """Remind developers to replace the bot's 7TV token before it expires."""

    @override
    async def component_load(self) -> None:
        self.check_stv_token.start()
        await super().component_load()

    @override
    async def component_teardown(self) -> None:
        self.check_stv_token.cancel()
        await super().component_teardown()

    def status(self) -> str:
        """Describe when the current 7TV token expires."""
        expires_at = self.bot.stv.token_expires_at
        if expires_at is None:
            return "7TV token expiry date is unknown (token is not a readable JWT)."
        left = expires_at - clock.utcnow()
        if left <= dt.timedelta(0):
            return f"7TV token expired at {expires_at:%Y-%m-%d %H:%M} UTC."
        return f"7TV token expires at {expires_at:%Y-%m-%d %H:%M} UTC (in {left.days}d {left.seconds // 3600}h)."

    @loop(time=[dt.time(hour=10, minute=0)])
    async def check_stv_token(self) -> None:
        """Ping developers once a day while the 7TV token is about to expire or already expired."""
        expires_at = self.bot.stv.token_expires_at
        if expires_at is not None and expires_at - clock.utcnow() > WARN_BEFORE:
            logger.debug(self.status())
            return

        embed = Embed(
            title="7TV token needs replacing",
            description=(
                f"{self.status()}\n"
                "7TV sessions can't be refreshed, so log into 7tv.app as the bot, copy the token from dev tools "
                f"and submit it at {self.bot.domain}{STV_TOKEN_PAGE_PATH}"
            ),
            colour=0x3493EE,
        )
        await self.bot.notify_developers(embed=embed)

    @commands.command(aliases=["stv_token"])
    async def stv_token_status(self, ctx: Context) -> None:
        """Show when the bot's 7TV token expires."""
        await ctx.send(self.status())


async def setup(bot: Bot) -> None:
    """Load StvTokenReminder."""
    await bot.add_component(StvTokenReminder(bot))
