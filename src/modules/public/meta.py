from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

import twitchio  # noqa: TC002
from twitchio.ext import commands

from core import IrePublicComponent
from utils import const, guards

if TYPE_CHECKING:
    from core import IreBot, IreContext

    class RunDict(TypedDict):
        keywords: list[str]
        game: str
        desc: str


__all__ = ("MetaCommands",)


class MetaCommands(IrePublicComponent):
    """Meta commands."""

    @commands.command()
    async def about(self, ctx: IreContext) -> None:
        """A bit bio information about the bot."""
        await ctx.send(f"I'm a personal Irene's bot, made by Irene. {const.STV.AYAYA}")

    @guards.is_online()
    @commands.command()
    async def clip(self, ctx: IreContext, *, title: str | None = None) -> None:
        """Create a clip."""
        # TODO: include `duration` argument
        # (I guess we have to use some regex converter cause twitchio doesnt have duration = None, *, title: str support)
        # TODO: try to experiment with edit_url
        clip = await ctx.broadcaster.create_clip(token_for=const.UserID.Bot, title=title)
        await ctx.send(f"clips.twitch.tv/{clip.id}")
        await ctx.send(f"Editing Link: {clip.edit_url}")

    @clip.error
    async def clip_error(self, payload: commands.CommandErrorPayload) -> None:
        """Error handler for !clip command."""
        error = payload.exception
        if isinstance(error, ValueError):
            # clip duration is bad value
            await payload.context.send(str(error))
            return
        # Unresolved
        raise error

    @commands.command(name="commands", aliases=["help", "irenesbot"])
    async def command_list(self, ctx: IreContext) -> None:
        """Get a list of bot commands."""
        await ctx.send("aluerie.github.io/IreBot")

    @commands.command(aliases=["hi", "yo", "hallo"])
    async def hello(self, ctx: IreContext) -> None:
        """Hello."""
        await ctx.send(f"{const.STV.hello} Hello!")

    @commands.command()
    async def irene(self, ctx: IreContext) -> None:
        """Just a random command that is unlikely to be in other bots."""
        await ctx.send(const.Global.FeelsDankMan)

    @commands.command()
    async def ping(self, ctx: IreContext) -> None:
        """Ping the bot.

        Currently doesn't provide any useful info.
        """
        await ctx.send("\N{TABLE TENNIS PADDLE AND BALL} Pong!")

    @commands.command()
    async def source(self, ctx: IreContext) -> None:
        """Get the link to the bot's GitHub repository."""
        await ctx.send("github.com/Aluerie/IreBot")

    @commands.command(aliases=["id", "twitchid"])
    async def twitch_id(self, ctx: IreContext, *, user: twitchio.User | None = None) -> None:
        """Get mentioned @user numeric twitch_id."""
        who = user or ctx.author
        await ctx.send(f"Twitch ID for {who.mention}: {who.id} {const.STV.donkDetective}")


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(MetaCommands(bot))
