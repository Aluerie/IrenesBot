# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""7TV token renewal.

7TV sessions hard-expire 30 days after login with no way to refresh them.
A few days before expiry the bot logs into 7TV again by itself; if that fails,
it pings the developers to submit a new token manually.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, override

from discord import Embed
from loguru import logger
from twitchio.ext import commands

from core import DevComponent
from core.stv_token import STV_TOKEN_PAGE_PATH, StvLoginError, renew_stv_token
from shared import clock
from shared.concepts import loop

if TYPE_CHECKING:
    from core import Bot, Context


RENEW_BEFORE = dt.timedelta(days=5)


class StvTokenRenewal(DevComponent):
    """Keep the bot's 7TV token alive: renew it automatically and ping developers if that fails."""

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

    async def renew(self) -> str:
        """Renew the token automatically; on failure ping developers with manual instructions.

        Returns
        -------
        str
            Human-readable outcome.
        """
        try:
            return await renew_stv_token(self.bot)
        except (StvLoginError, ValueError) as exc:
            logger.warning("Automatic 7TV token renewal failed: {}", exc)
            embed = Embed(
                title="7TV token needs replacing",
                description=(
                    f"{self.status()}\n"
                    f"Automatic renewal failed: {exc}\n\n"
                    "If the twitch.tv `persistent` cookie expired, copy a fresh one from the browser logged in as "
                    "the bot into `TWITCH_BOT_PERSISTENT_COOKIE`. Or log into 7tv.app as the bot, copy the token "
                    f"from dev tools and submit it at {self.bot.domain}{STV_TOKEN_PAGE_PATH}"
                ),
                colour=0x3493EE,
            )
            await self.bot.notify_developers(embed=embed)
            return f"Automatic 7TV token renewal failed: {exc}"

    @loop(hours=12, wait_for_ready=True)
    async def check_stv_token(self) -> None:
        """Renew the 7TV token when it is about to expire (checked on start-up and every 12 hours)."""
        expires_at = self.bot.stv.token_expires_at
        if expires_at is not None and expires_at - clock.utcnow() > RENEW_BEFORE:
            logger.debug(self.status())
            return
        await self.renew()

    @commands.command(aliases=["stv_token"])
    async def stv_token_status(self, ctx: Context) -> None:
        """Show when the bot's 7TV token expires."""
        await ctx.send(self.status())

    @commands.command()
    async def stv_renew(self, ctx: Context) -> None:
        """Renew the bot's 7TV token right now."""
        await ctx.send(await self.renew())


async def setup(bot: Bot) -> None:
    """Load StvTokenRenewal."""
    await bot.add_component(StvTokenRenewal(bot))
