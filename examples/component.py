from __future__ import annotations

from typing import TYPE_CHECKING

from src.core import IrePersonalComponent
from twitchio.ext import commands

if TYPE_CHECKING:
    from src.core import IreBot, IreContext


class NewCog(IrePersonalComponent):
    """."""

    @commands.command()
    async def new_command(self, ctx: IreContext) -> None:
        """."""
        await ctx.send("Not implemented yet!")


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(NewCog(bot))
