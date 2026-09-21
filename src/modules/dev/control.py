from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Annotated, override

import discord
from twitchio.ext import commands

from core import IreDevComponent, ireloop
from utils import const, guards

if TYPE_CHECKING:
    from core import IreBot, IreContext

log = logging.getLogger(__name__)


class ModuleConverter(commands.Converter[str]):
    """Simple converter to add `modules.` prefix to user input.

    So I can use !reload and similar commands like this `!reload personal.emotes_check`.
    """

    @override
    async def convert(self, ctx: IreContext, arg: str) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        return f"modules.{arg}"


class Control(IreDevComponent):
    """Dev Only Commands."""

    def __init__(self, bot: IreBot) -> None:
        super().__init__(bot)
        # I'm not sure if it's the right way but one day our 10 minutes loop task
        # got rate-limited with
        # `discord.errors.HTTPException: 429 Too Many Requests (error code: 40062): Service resource is being rate limited`
        self.heartbeat_task.add_exception_type(discord.HTTPException)

    @override
    async def component_load(self) -> None:
        self.heartbeat_task.start()
        await super().component_load()

    @override
    async def component_teardown(self) -> None:
        self.heartbeat_task.stop()
        await super().component_teardown()

    @guards.is_vps()
    @commands.command(aliases=["kill"])
    async def maintenance(self, ctx: IreContext) -> None:
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

    @guards.is_vps()
    @commands.command(aliases=["restart"])
    async def reboot(self, ctx: IreContext) -> None:
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
    async def unload(self, ctx: IreContext, *, modules: Annotated[str, ModuleConverter]) -> None:
        """Unload the modules."""
        await self.bot.unload_module(modules)
        log.info("!unload - unloaded %s", modules)
        await ctx.send(f"{const.STV.DankApprove} unloaded {modules}")

    @commands.command()
    async def reload(self, ctx: IreContext, *, modules: Annotated[str, ModuleConverter]) -> None:
        """Reload the modules."""
        await self.bot.reload_module(modules)
        log.info("!reload - reloaded %s", modules)
        await ctx.send(f"{const.STV.DankApprove} reloaded {modules}")

    @commands.command()
    async def load(self, ctx: IreContext, *, modules: Annotated[str, ModuleConverter]) -> None:
        """Load the modules."""
        await self.bot.load_module(modules)
        log.info("!load - loaded %s", modules)
        await ctx.send(f"{const.STV.DankApprove} loaded {modules}")

    @commands.command(name="modules", aliases=["extensions", "components"])  # module != component but whatever
    async def list_modules(self, ctx: IreContext) -> None:
        """List modules that are currently loaded by the bot.

        Examples
        --------
        * "modules.personal.dev modules.public.states"
        """
        index: dict[str, list[str]] = {"personal": [], "public": [], "dev": [], "other": []}
        for module in ctx.bot.modules.values():
            name = module.__name__
            for category in ("public", "personal", "dev"):
                if name.startswith(f"modules.{category}."):
                    index[category].append(name.removeprefix(f"modules.{category}."))
                    break
            else:
                index["other"].append(name.removeprefix("modules."))

        for c, m in index.items():
            if m:
                await ctx.send(f"{const.STV.DankDolmes} {c}: {', '.join(m)}")

    @ireloop(minutes=10)
    async def heartbeat_task(self) -> None:
        """Send heartbeat reports to a discord channel with a small information."""
        await self.bot.heartbeat_webhook.send("Alive")


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(Control(bot))
