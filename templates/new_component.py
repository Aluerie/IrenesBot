"""New module.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from twitchio.ext import commands

from core import PersonalComponent

if TYPE_CHECKING:
    from core import Bot, Context


class NewCog(PersonalComponent):
    """New Cog."""

    @commands.command()
    async def new_command(self, ctx: Context) -> None:
        """Send this."""
        await ctx.send("Not implemented yet!")


async def setup(bot: Bot) -> None:
    """Load IreBot's module. Framework of twitchio."""
    await bot.add_component(NewCog(bot))
