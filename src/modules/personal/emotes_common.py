from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any, override

from discord import Embed
from twitchio.ext import commands

from core import IrePersonalComponent, ireloop
from utils import const

if TYPE_CHECKING:
    from enum import StrEnum

    from core import IreBot, IreContext

log = logging.getLogger(__name__)


class EmoteChecker(IrePersonalComponent):
    """Check if emotes from 3rd party services like 7TV, FFZ, BTTV are valid.

    Usable in case I remove an emote that is used in bot's responses.
    Bot will notify me that emote was used so I can make adjustments.
    """

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)

    @override
    async def component_load(self) -> None:
        self.check_emotes.start()
        await super().component_load()

    @override
    async def component_teardown(self) -> None:
        self.check_emotes.cancel()
        await super().component_teardown()

    async def send_error_embed(self, emotes_to_send: list[str], service: str, colour: int) -> None:
        """Helper function to send a ping to Aluerie that something is wrong with emote services."""
        content = self.bot.error_ping
        embed = Embed(
            title=f"Problem with {service} emotes",
            description=(
                "Looks like the following emote(-s) are no longer present in the channel.\n"
                f"```\n{', '.join(emotes_to_send)}```"
            ),
            colour=colour,
        ).set_footer(text="but it was previously used for @IrenesBot emotes")
        await self.bot.error_webhook.send(content=content, embed=embed)

    async def cross_check_emotes(self, api_emotes: list[str], bot_emotes: type[StrEnum], color: int) -> None:
        """Cross check between emote list in `utils.const` and list from 3rd party emote service API."""
        emotes_to_send: list[str] = [e for e in bot_emotes if e not in api_emotes]

        log_prefix = "Checked 7TV, FFZ & BTTV emotes from 'const.py'"
        if emotes_to_send:
            await self.send_error_embed(emotes_to_send, bot_emotes.__name__, color)
            log.debug("%s - %s emotes are not in order: %s", log_prefix, len(emotes_to_send), ", ".join(emotes_to_send))
        else:
            log.debug("Checked 7TV, FFZ & BTTV emotes from 'const.py' - all seems good.")

    @ireloop(time=[datetime.time(hour=5, minute=59)])
    async def check_emotes(self) -> None:
        """The task to check emotes."""
        if datetime.datetime.now(datetime.UTC).weekday() != 5:
            # simple way to make a task run once/week
            return

        broadcaster_id = const.UserID.Irene
        # SEVEN TV
        async with self.bot.session.get(f"https://7tv.io/v3/users/twitch/{broadcaster_id}") as resp:
            stv_json = await resp.json()
            stv_emote_list = [emote["name"] for emote in stv_json["emote_set"]["emotes"]]
            await self.cross_check_emotes(stv_emote_list, const.STV, 0x3493EE)

        # FFZ
        async with self.bot.session.get(f"https://api.frankerfacez.com/v1/room/id/{broadcaster_id}") as resp:
            ffz_json = await resp.json()  # if we ever need this "654554" then it exists as `ffz_json["room"]["set"]`
            ffz_emote_list = [emote["name"] for emote in ffz_json["sets"]["654554"]["emoticons"]]
            await self.cross_check_emotes(ffz_emote_list, const.FFZ, 0x271F3E)

        # BTTV
        async with self.bot.session.get(f"https://api.betterttv.net/3/cached/users/twitch/{broadcaster_id}") as resp:
            bttv_json = await resp.json()
            bttv_emote_list = [emote["code"] for emote in bttv_json["channelEmotes"] + bttv_json["sharedEmotes"]]
            await self.cross_check_emotes(bttv_emote_list, const.BTTV, 0xD50014)

    @commands.command(aliases=["potatbotat"])
    async def potat(self, ctx: IreContext) -> None:
        """Get a note on what command to use when merging 7tv sets using @PotatBotat tool.

        Link to the tool: https://potat.app/help/mergeset.
        Using this command will trigger @PotatBotat automatically as it listens to other bots messages too.
        """
        await ctx.send(
            f'#mergeset {const.SevenTV.IRENE_EMOTE_SET_ID} 01JS1XW1PAAKP34984FDYZVDR7 as:"Default but Dota 2"'
        )


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(EmoteChecker(bot))
