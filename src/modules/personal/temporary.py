"""Temporary Personal Commands.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, TypedDict

from twitchio.ext import commands

from core import IrePersonalComponent
from utils import const

if TYPE_CHECKING:
    from core import IreBot, IreContext

    class RunDict(TypedDict):
        keywords: list[str]
        game: str
        desc: str


__all__ = ("TemporaryCommands",)


class TemporaryCommands(IrePersonalComponent):
    """Miscellaneous commands.

    Commands that are likely to be removed in future.
    """

    @commands.group(invoke_fallback=True)
    async def gunfort(self, ctx: IreContext) -> None:
        """Commands to count my successful and failed Yolo Gunfort attempts."""
        query = "SELECT value FROM ttv_counters WHERE name = $1;"
        success: int = await self.bot.pool.fetchval(query, "gunfort_success")
        query = "SELECT value FROM ttv_counters WHERE name = $1;"
        attempts: int = await self.bot.pool.fetchval(query, "gunfort_attempts")

        stats = f" Success Rate: {success / attempts:.1%} (over {attempts} attempts)"
        await ctx.send(f"{const.STV.science} Yolo Gunfort {stats}")

    @commands.is_owner()
    @gunfort.command()
    async def no(self, ctx: IreContext) -> None:
        """Count a failed Yolo Gunfort attempt in."""
        query = "SELECT value FROM ttv_counters WHERE name = $1;"
        success: int = await self.bot.pool.fetchval(query, "gunfort_success")
        query = "UPDATE ttv_counters SET value = value + 1 WHERE name = $1 RETURNING value;"
        attempts: int = await self.bot.pool.fetchval(query, "gunfort_attempts")

        stats = f" Success Rate: {success / attempts:.1%} (over {attempts} attempts)"
        await ctx.send(f"Failed yolo gunfort? {const.STV.classic} {stats} {const.STV.buenoFail}")

    @commands.is_owner()
    @gunfort.command()
    async def yes(self, ctx: IreContext) -> None:
        """Count a successful Yolo Gunfort attempt in."""
        query = "UPDATE ttv_counters SET value = value + 1 WHERE name = $1 RETURNING value;"
        success: int = await self.bot.pool.fetchval(query, "gunfort_success")
        query = "UPDATE ttv_counters SET value = value + 1 WHERE name = $1 RETURNING value;"
        attempts: int = await self.bot.pool.fetchval(query, "gunfort_attempts")

        stats = f" Success Rate: {success / attempts:.1%} (over {attempts} attempts)"
        await ctx.send(f"Yolo Gunfort is easy {const.STV.EZdodge} {stats} {const.STV.buenoSuccess}")

    @commands.command(name="is")
    async def immortal_severance(self, ctx: IreContext) -> None:
        """Print a proper speed-run order for IS dialog."""
        msg = (
            "👶 Kuro: "
            "1. Quit "
            '2. Skip → Ask "About the flower" → Skip until item → Quit '
            "3. Skip until item → Quit "
            "4. Quit "
            "5. Skip until item → Quit "
            "💃 Emma: "
            "Quit 3 dialogs "
            "👶 Kuro again: "
            "1. Quit "
            "2. Burn incense → Skip till cutscene → Quit"
        )
        await ctx.send(msg)

    @commands.command(name="iss")
    async def immortal_severance_short(self, ctx: IreContext) -> None:
        """Print a proper speed-run order for IS dialog."""
        msg = "Kuro: 1️⃣🟥2️⃣🟩🌸🟩3️⃣🟩4️⃣🟥5️⃣🟩 → Emma:🟥3x → Kuro:1️⃣🟥2️⃣🔥🟩 "
        await ctx.send(msg)

    @commands.command()
    async def abc(self, ctx: IreContext) -> None:
        """Send all possible *uh emotes to the chat."""
        # fmt: off
        alphabet = [
            "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
            "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"
        ]
        # fmt: on
        text: str = " ".join(f"{letter}uh" for letter in alphabet)
        await ctx.send(text)

    @commands.command()
    async def based(self, ctx: IreContext) -> None:
        """Sword based."""
        msg = (
            "Sword ✨ BASED ✨ is my vision of how 'Sword Damage Only' restriction "
            "should have been defined. Boss-combat is sword-only, while Stealth/QoL actives "
            "are okay (i.e. gachiin , Bloodsmoke, Ceramics). "
            "This way the core spirit of the run is the same but running sections/SDB setups are a bit better. "
            f"I don't use yash / ako but they would be allowed I guess {const.Global.CaitThinking} "
        )
        await ctx.send(msg)

    @commands.command()
    async def run(self, ctx: IreContext) -> None:
        """My run."""
        msg = (
            "All Unique Bosses, which means I need to kill at least one boss from the same 'type', "
            "e.g. I have to choose 1 Headless (but skip other 2), 1 Lone Shadow, etc. "
            "On paper, it becomes All Memories + some extra minibosses. "
            "I also load a save-state for Emma + Isshin + Inner Father to cover them too."
        )
        await ctx.send(msg)

    @commands.cooldown(rate=1, per=dt.timedelta(seconds=60), key=commands.BucketType.channel)
    @commands.command()
    async def chat(self, ctx: IreContext, *, argument: str) -> None:
        """Repeat chatter's request.

        This is useful to bypass mod-only restriction of cyan-chat.
        """
        await ctx.send(f"!chat {argument}")


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(TemporaryCommands(bot))
