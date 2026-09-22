from __future__ import annotations

import datetime
import itertools
import random
import re
from typing import TYPE_CHECKING, Any, TypedDict

from twitchio.ext import commands

from core import IrePersonalComponent
from utils import const

if TYPE_CHECKING:
    import twitchio

    from core import IreBot

    class KeywordDict(TypedDict):
        aliases: list[str]
        response: str
        dt: datetime.datetime


__all__ = ("Keywords",)


class Keywords(IrePersonalComponent):
    """React to specific key word / key phrases with bot's own messages.

    Mostly used to make a small feeling of a crowd - something like many users are Pog-ing.
    """

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.cooldown_dt = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)

        response_search = {
            # response: search in chat
            "Pog": ["Pog", "PogU"],
            "gg": ["gg"],
            "GG": ["GG"],
            "bueno": ["bueno"],
        }

        self.keywords: dict[str, str] = {
            keyword: response for response, search in response_search.items() for keyword in itertools.chain(search)
        }
        self.compiled_regex = re.compile(r"\b(" + r"|".join(self.keywords) + r")\b", flags=re.VERBOSE)

    @commands.Component.listener(name="message")
    async def keywords_response(self, message: twitchio.ChatMessage) -> None:
        """Sends a flavour message if a keyword/key phrase was spotted in the chat."""
        if not self.is_dev(message.broadcaster.id):
            return

        now = datetime.datetime.now(datetime.UTC)
        if (now - self.cooldown_dt).seconds < 7 * 60:
            # the keyword was recently triggered
            return
        if message.chatter.name in const.BotsLowerName or not message.text or random.randint(1, 100) > 10:
            # restrict `keywords` functionality from
            # 1. invited bots
            # 2. weird empty messages
            # 3. ~90% chance to fail just so the bot doesn't spam it too much (even though we have cd)
            return

        if found := self.compiled_regex.search(message.text):
            await message.respond(self.keywords[found[0]])
            self.cooldown_dt = now


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(Keywords(bot))
