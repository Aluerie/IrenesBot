from __future__ import annotations

import contextlib
import datetime
from typing import TYPE_CHECKING, Any, TypedDict

import twitchio
from twitchio.ext import commands

from core import IrePersonalComponent, ireloop
from utils import const, guards

if TYPE_CHECKING:
    from core import IreBot, IreContext

    class Tracked(TypedDict):
        game: str
        title: str
        game_dt: datetime.datetime
        title_dt: datetime.datetime


__all__ = ("StreamInformation",)


# specific exception so I can use shortcuts over typing full names
GAME_KEYWORDS = {
    "dota": "Dota 2",
    "er": "Elden Ring",
    "sk": "Sekiro",
    "hk": "Hollow Knight",
    "ss": "Hollow Knight: Silksong",
    "mom": "With Your Mom's Tits",
    "dev": "Software and Game Development",
    "code": "Software and Game Development",
}


class StreamInformation(IrePersonalComponent):
    """Commands replicating "Edit Stream Information" window.

    Such as
    * Edit stream title
    * Edit stream game
    The commands are designed to be a little bit smart.
    """

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)

        self.game: str = "idk"
        self.game_dt: datetime.datetime = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
        self.title: str = "idk"
        self.title_dt: datetime.datetime = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)

        self.start_tracking.start()

    @ireloop(count=1)
    async def start_tracking(self) -> None:
        """Start tracking my channel info.

        Unfortunately, twitch eventSub payloads for channel update events do not have before/after and
        do not say what exactly changed, they just send newest `twitchio.ChannelUpdate` payload.

        This is why we need to track the past ourselves.
        """
        channel_info = await self.bot.create_partialuser(self.bot.owner_id).fetch_channel_info()
        self.game = channel_info.game_name
        self.title = channel_info.title

    @commands.command(name="game", aliases=["category"])
    async def game_command(self, ctx: IreContext, *, game_name: str | None = None) -> None:
        """Either get current channel game or update it."""
        if not game_name:
            # 1. No argument
            # respond with current game name the channel is playing
            channel_info = await ctx.broadcaster.fetch_channel_info()
            game_name = channel_info.game_name or "No game category"
            await ctx.send(f"{game_name} {const.STV.DankDolmes}")
            return

        # 2. Argument "game_name" is provided
        # Set the game to it
        if not ctx.chatter.moderator:
            # a. non-mod case
            await ctx.send(f"Only moderators are allowed to change game name {const.FFZ.peepoPolice}")
            return

        if game_name.lower() == "clear":
            # b. A keyword to clear the game category, sets it uncategorized
            self.game_dt = datetime.datetime.now(datetime.UTC)
            await ctx.broadcaster.modify_channel(game_id="0")
            await ctx.send(f'Set game to "No game category" {const.STV.uuh}')
            return

        # c. specified game
        game_name = GAME_KEYWORDS.get(game_name, game_name)

        game = next(iter(await self.bot.fetch_games(names=[game_name])), None)
        if not game:
            await ctx.send(f"Couldn't find any games with such a name {const.STV.How2Read}")
            return

        self.game_dt = datetime.datetime.now(datetime.UTC)
        await ctx.broadcaster.modify_channel(game_id=game.id)
        await ctx.send(f'Changed game to "{game.name}" {const.STV.DankMods}')
        return

    async def update_title(self, streamer: twitchio.PartialUser, title: str) -> None:
        """Helper function to update the streamer's title."""
        self.title_dt = datetime.datetime.now(datetime.UTC)
        await streamer.modify_channel(title=title)

    @commands.group(name="title", invoke_fallback=True)
    async def title_group(self, ctx: IreContext, *, title: str = "") -> None:
        """Callback for !title group commands.

        Can be used with subcommands. But when used on its - it either shows the title or updates it,
        whether the title argument was provided and user has moderator permissions.

        Examples
        --------
            * !title - shows current title.
            * !title Hello World - title changes to "Hello World" (if mod)
        """
        if not title:
            # 1. No argument
            # respond with current game name the channel is playing
            channel_info = await ctx.broadcaster.fetch_channel_info()
            await ctx.send(channel_info.title)
        # 2. Argument "title" is provided
        elif not ctx.chatter.moderator:
            # a. non-mod case: give a warning for the chatter
            await ctx.send(f"Only moderators are allowed to change title {const.FFZ.peepoPolice}")
        else:
            # b. mod case: actually update the title
            await self.update_title(ctx.broadcaster, title=title)
            await ctx.send(f'{const.STV.donkHappy} Changed title to "{title}"')

    @commands.is_moderator()
    @title_group.command(name="set")
    async def title_set(self, ctx: IreContext, *, title: str) -> None:
        """Set the title for the stream."""
        await self.update_title(ctx.broadcaster, title=title)
        await ctx.send(f'{const.STV.donkHappy} Set title to "{title}"')

    @commands.Component.listener(name="channel_update")
    async def channel_update(self, update: twitchio.ChannelUpdate) -> None:
        """Channel Info (game, title, etc) got updated."""
        if not self.is_dev(update.broadcaster.id):
            return

        now = datetime.datetime.now(datetime.UTC)
        # time check is needed so we don't repeat notification that comes from !game !title commands.

        if self.game != update.category_name:
            new_category = update.category_name or "No category"
            if (now - self.game_dt).seconds > 15:
                # time condition so the bot doesn't announce changes done via !game command
                await update.respond(f'{const.STV.donkDetective} Game was changed to "{new_category}"')

            if self.bot.is_online(update.broadcaster.id):
                with contextlib.suppress(twitchio.HTTPException):
                    await update.broadcaster.create_stream_marker(
                        token_for=const.UserID.Irene, description=f"Game: {new_category}"
                    )

        if self.title != update.title and (now - self.title_dt).seconds > 15:
            # time condition so the bot doesn't announce changes done via !title command
            await update.respond(f'{const.STV.DankThink} Title was changed to "{update.title}"')

        self.game = update.category_name
        self.title = update.title

    @guards.is_online()
    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    @commands.command()
    async def marker(self, ctx: IreContext, description: str) -> None:
        """Create a stream marker.

        Stream marker is a just a timestamp to mark in Twitch.tv Video Highlighter.
        """
        await ctx.broadcaster.create_stream_marker(token_for=const.UserID.Irene, description=description)
        await ctx.send(f"Successfully created a marker. {const.STV.DankApprove}")


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(StreamInformation(bot))
