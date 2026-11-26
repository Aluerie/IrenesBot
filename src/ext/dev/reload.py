# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Developer control features."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Annotated, override

import aiohttp
from loguru import logger
from twitchio.ext import commands

from config import env
from core import DevComponent
from shared import systemd
from shared.concepts import loop
from utils import const, guards

if TYPE_CHECKING:
    from core import Bot, Context


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
        self.heartbeat_task.add_exception_type(aiohttp.ClientError, TimeoutError)

    @override
    async def component_load(self) -> None:
        # only the systemd service in prod pings, so a bot running elsewhere doesn't keep the check green
        if systemd.is_systemd_service():
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
            logger.exception("Failed to Stop the bot's process")
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
            logger.exception("Failed to Restart the bot's process")
            # it might not go off
            await ctx.send("Something went wrong.")

    @commands.command()
    async def unload(self, ctx: Context, *, modules: Annotated[str, ExtConverter]) -> None:
        """Unload the modules (I also call them 'extensions')."""
        await self.bot.unload_module(modules)
        logger.info("!unload - unloaded {}", modules)
        await ctx.send(f"{const.Stv.DankApprove} unloaded {modules}")

    @commands.command()
    async def reload(self, ctx: Context, *, modules: Annotated[str, ExtConverter]) -> None:
        """Reload the modules (I also call them 'extensions')."""
        await self.bot.reload_module(modules)
        logger.info("!reload - reloaded {}", modules)
        await ctx.send(f"{const.Stv.DankApprove} reloaded {modules}")

    @commands.command()
    async def load(self, ctx: Context, *, modules: Annotated[str, ExtConverter]) -> None:
        """Load the modules (I also call them 'extensions')."""
        await self.bot.load_module(modules)
        logger.info("!load - loaded {}", modules)
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

    @loop(minutes=5, wait_for_ready=True)
    async def heartbeat_task(self) -> None:
        """Ping the healthchecks.io check, which alerts me when these pings stop coming.

        Skips the ping unless every conduit websocket shard is connected to Twitch and the database answers.
        """
        if not env.HEALTHCHECK_URL:
            return
        sockets = self.bot.conduit_info.websockets
        if not sockets or not all(socket.connected for socket in sockets.values()):
            logger.warning("Healthcheck: skipping the ping, not every conduit websocket is connected: {}", sockets)
            return
        try:
            await self.bot.pool.fetchval("SELECT 1")
        except Exception as exc:  # ruff: ignore[blind-except] any database failure just means "not healthy"
            logger.warning("Healthcheck: skipping the ping, the database doesn't answer: {!r}", exc)
            return
        async with self.bot.session.get(env.HEALTHCHECK_URL, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(Control(bot))
