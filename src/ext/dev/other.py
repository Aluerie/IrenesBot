# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Other developer tools."""

from __future__ import annotations

import importlib.metadata
import sys
import unicodedata
from typing import TYPE_CHECKING, TypedDict

from twitchio.ext import commands

from core import DevComponent
from shared import clock, globs

if TYPE_CHECKING:
    from core import Bot, Context

    class RunDict(TypedDict):
        keywords: list[str]
        game: str
        desc: str


__all__ = ("OtherDevCommands",)


class OtherDevCommands(DevComponent):
    """Other Dev Commands."""

    @commands.command(aliases=["char"])
    async def charinfo(self, ctx: Context, *, characters: str) -> None:
        """Show information about character(-s).

        Only up to a 10 characters at a time though.

        Parameters
        ----------
        characters
            Input up to 10 characters to get format info about.

        """

        def to_string(c: str) -> str:
            name = unicodedata.name(c, None)
            return f"\\N{{{name}}}" if name is not None else "Name not found."

        names = " ".join(to_string(c) for c in characters[:10])
        if len(characters) > 10:
            names += "(Output was too long: displaying only first 10 chars)"
        await ctx.send(names)

    @commands.command()
    async def say(self, ctx: Context, *, message: str) -> None:
        """Make the bot repeat your message.

        Useful for making showcase of bot commands with slight edits.
        """
        await ctx.send(message)

    @commands.command()  # maybe the name "since" isn't the best but "uptime", "online" are already taken
    async def since(self, ctx: Context) -> None:
        """🔬 Get the bot's uptime.

        Uptime is time for which the bot has been online without any crashes or reboots.
        """
        await ctx.send(
            f"Last reboot {self.bot.launch_time.strftime('%H:%M %d/%b/%y')}; "
            f"It's been {clock.human_datetime_diff(self.bot.launch_time)}."
        )

    @commands.command(aliases=["version", "packages", "libraries"])
    async def versions(self, ctx: Context) -> None:
        """🔬 Get info bot's main Python Packages."""
        curious_packages = ["twitchio"]  # list of packages versions of which I'm interested the most
        pv = sys.version_info  # python version

        await ctx.send(
            f"Python {pv.major}.{pv.minor}.{pv.micro} | "
            + " | ".join(f"{package}: {importlib.metadata.version(package)}" for package in curious_packages)
        )

    @commands.command()
    async def test_digits(self, ctx: Context) -> None:
        """Test digit emotes in twitch chat.

        At the point of writing this function - the number emotes like :one: were not working
        in twitch chat powered with FFZ/7TV addons.
        So use it to check if it's fixed. if yes - then we can rewrite some functions to use these emotes.
        """
        content = " ".join(globs.DIGITS)
        await ctx.send(content)


async def setup(bot: Bot) -> None:
    """Load the extension (twitchio entry point)."""
    await bot.add_component(OtherDevCommands(bot))
