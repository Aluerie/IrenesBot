"""Developer control features.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Annotated, override

import discord
from twitchio.ext import commands

from core import DevComponent
from shared.concepts import loop
from utils import const, guards

if TYPE_CHECKING:
    from core import Bot, Context

log = logging.getLogger(__name__)


class ExtConverter(commands.Converter[str]):
    """Simple converter to add `ext.` prefix to user input.

    So I can use !reload and similar commands like this `!reload personal.emotes_check`.
    """

    @override
    async def convert(self, ctx: Context, arg: str) -> str:  # ty: ignore[invalid-method-override]
        # TODO: do something like where "stv" and "public.stv" are allowed to be used
        return f"ext.{arg}"


class Control(DevComponent):
    """Dev Only Commands."""

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.heartbeat_task.add_exception_type(discord.HTTPException)

    @override
    async def component_load(self) -> None:
        self.heartbeat_task.start()
        await super().component_load()

    @override
    async def component_teardown(self) -> None:
        self.heartbeat_task.stop()
        await super().component_teardown()

    @guards.is_production()
    @commands.command(aliases=["kill"])
    async def maintenance(self, ctx: Context) -> None:
        """Kill the bot process on VPS.

        Usable for bot testing so I don't have double responses.

        Note that this will turn off the whole bot functionality so things like main bot alerts will also stop.
        """
        await ctx.send("Shutting down the bot in 3 2 1")
        await asyncio.sleep(3.0)
        try:
            await asyncio.create_subprocess_shell("sudo systemctl stop irebot")
        except Exception:
            log.exception("Failed to Stop the bot's process", stack_info=True)
            # it might not go off
            await ctx.send("Something went wrong.")

    @guards.is_production()
    @commands.command(aliases=["restart"])
    async def reboot(self, ctx: Context) -> None:
        """Restart the bot process on VPS.

        Usable to restart the bot without logging to VPS machine or committing something.
        """
        await ctx.send("Rebooting in 3 2 1")
        await asyncio.sleep(3.0)
        try:
            await asyncio.create_subprocess_shell("sudo systemctl restart irebot")
        except Exception:
            log.exception("Failed to Restart the bot's process")
            # it might not go off
            await ctx.send("Something went wrong.")

    @commands.command()
    async def unload(self, ctx: Context, *, modules: Annotated[str, ExtConverter]) -> None:
        """Unload the modules (I also call them 'extensions')."""
        await self.bot.unload_module(modules)
        log.info("!unload - unloaded %s", modules)
        await ctx.send(f"{const.Stv.DankApprove} unloaded {modules}")

    @commands.command()
    async def reload(self, ctx: Context, *, modules: Annotated[str, ExtConverter]) -> None:
        """Reload the modules (I also call them 'extensions')."""
        await self.bot.reload_module(modules)
        log.info("!reload - reloaded %s", modules)
        await ctx.send(f"{const.Stv.DankApprove} reloaded {modules}")

    @commands.command()
    async def load(self, ctx: Context, *, modules: Annotated[str, ExtConverter]) -> None:
        """Load the modules (I also call them 'extensions')."""
        await self.bot.load_module(modules)
        log.info("!load - loaded %s", modules)
        await ctx.send(f"{const.Stv.DankApprove} loaded {modules}")

    @commands.command(name="modules", aliases=["extensions", "components"])  # module != component but whatever
    async def list_modules(self, ctx: Context) -> None:
        """List modules that are currently loaded by the bot.

        Examples
        --------
        * "ext.personal.dev ext.public.states"
        """
        index: dict[str, list[str]] = {"personal": [], "public": [], "dev": [], "other": []}
        for module in ctx.bot.modules.values():
            name = module.__name__
            for category in ("public", "personal", "dev"):
                if name.startswith(f"ext.{category}."):
                    index[category].append(name.removeprefix(f"ext.{category}."))
                    break
            else:
                index["other"].append(name.removeprefix("ext."))

        for c, m in index.items():
            if m:
                await ctx.send(f"{const.Stv.DankDolmes} {c}: {', '.join(m)}")

    @loop(minutes=10)
    async def heartbeat_task(self) -> None:
        """Send heartbeat reports to a discord channel with a small information."""
        await self.bot.heartbeat_webhook.send("Alive")


async def setup(bot: Bot) -> None:
    """Load the extension (twitchio entry point)."""
    await bot.add_component(Control(bot))
