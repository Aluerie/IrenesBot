from __future__ import annotations

import asyncio
import datetime
import random
import re
from typing import TYPE_CHECKING, Any, TypedDict

from twitchio.ext import commands

from core import IrePersonalComponent
from utils import const

if TYPE_CHECKING:
    import twitchio

    from core import IreBot, IreContext

    class FirstRedeemsRow(TypedDict):
        user_name: str
        first_times: int


__all__ = ("Counters",)

FIRST_ID: str = "902e931b-3d09-4a2e-9996-1d1ad599761d"


class Counters(IrePersonalComponent):
    """Track some silly number counters of how many times this or that happened."""

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.last_erm_notification: datetime.datetime = datetime.datetime.now(datetime.UTC)

    # ERM COUNTERS

    @commands.Component.listener(name="message")
    async def erm_counter(self, message: twitchio.ChatMessage) -> None:
        """Erm Counter."""
        if not self.is_dev(message.broadcaster.id):
            return
        if message.chatter.name in const.BotsLowerName or not message.text:
            return
        if not re.search(r"\bErm\b", message.text):
            return

        query = """--sql
            UPDATE ttv_counters
            SET value = value + 1
            where name = $1
            RETURNING value;
        """
        erm_amount_milestone: int = await self.bot.pool.fetchval(query, "erm")

        # milestone
        if erm_amount_milestone % 1000 == 0:
            await message.respond(
                f"{const.STV.wow} we reached a milestone of {erm_amount_milestone} {const.STV.Erm} in chat"
            )
            return

        # random notification/reminder
        now: datetime.datetime = datetime.datetime.now(datetime.UTC)
        if random.randint(0, 150) < 2 and (now - self.last_erm_notification).seconds > 180:
            await asyncio.sleep(3)
            query = "SELECT value FROM ttv_counters WHERE name = $1"
            erm_amount_random: int = await self.bot.pool.fetchval(query, "erm")
            await message.respond(f"{erm_amount_random} {const.STV.Erm} in chat.")
            return

    @commands.command(aliases=["erm"])
    async def erms(self, ctx: IreContext) -> None:
        """Get an erm_counter value."""
        query = "SELECT value FROM ttv_counters WHERE name = $1"
        value: int = await self.bot.pool.fetchval(query, "erm")
        await ctx.send(f"{value} {const.STV.Erm} in chat.")


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(Counters(bot))
