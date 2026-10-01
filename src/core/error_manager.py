from __future__ import annotations

import asyncio
import datetime
import logging
import platform
import re
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from discord.utils import MISSING

if TYPE_CHECKING:
    from collections.abc import Generator

    import discord

    from .bot import IreBot


log = logging.getLogger("exc_manager")


class ErrorManager:
    """Error Manager."""

    __slots__: tuple[str, ...] = ("_lock", "_most_recent", "bot", "cooldown")

    def __init__(self, bot: IreBot, *, cooldown: datetime.timedelta = MISSING) -> None:
        self.bot: IreBot = bot
        self.cooldown: datetime.timedelta = cooldown or datetime.timedelta(seconds=5)

        self._lock: asyncio.Lock = asyncio.Lock()
        self._most_recent: datetime.datetime | None = None

    def _yield_code_chunks(self, iterable: str, *, chunks_size: int = 2000) -> Generator[str]:
        codeblocks: str = "```py\n{}```"
        max_chars_in_code = chunks_size - (len(codeblocks) - 2)  # chunks_size minus code blocker size

        for i in range(0, len(iterable), max_chars_in_code):
            yield codeblocks.format(iterable[i : i + max_chars_in_code])

    async def register(self, error: BaseException, embed: discord.Embed, *, mention: bool = True) -> None:
        """Register, analyse error and put it into queue to send to developers."""
        log.error("%s: `%s`.", error.__class__.__name__, embed.footer.text, exc_info=error)

        if platform.system() == "Linux":
            slash = "/"
            # TODO: fix python 3.12 to be read from info
            venv_path = f"{Path.cwd()}{slash}.venv{slash}lib{slash}python3.14{slash}site-packages"
        else:
            # windows
            slash = "\\"
            # For some reason Python loves referencing venvs with a lowercase disk name
            venv_path = f"{Path.cwd()}{slash}.venv{slash}Lib{slash}site-packages".replace("D:\\", "d:\\")

        src_path = f"{Path.cwd()}{slash}src"

        replacements = {
            # Just making code blocks shorter without losing much information;
            venv_path: "<venv>",
            src_path: "<src>",
        }
        regex_pattern = re.compile("|".join(map(re.escape, replacements.keys())))
        traceback_string = regex_pattern.sub(lambda mo: replacements[mo.group()], "".join(traceback.format_exception(error)))

        async with self._lock:
            if self._most_recent and (delta := datetime.datetime.now(datetime.UTC) - self._most_recent) < self.cooldown:
                # We have to wait
                total_seconds = delta.total_seconds()
                log.debug("Waiting %s seconds to send the error.", total_seconds)
                await asyncio.sleep(total_seconds)

            self._most_recent = datetime.datetime.now(datetime.UTC)
            await self.send_report(traceback_string, embed, mention=mention)

    async def send_report(self, traceback: str, embed: discord.Embed, *, mention: bool) -> None:
        """Send an error to the webhook.

        It is not recommended to call this yourself, call `register` instead.
        """
        code_chunks = list(self._yield_code_chunks(traceback))

        if mention:
            await self.bot.error_webhook.send(self.bot.error_ping)

        for chunk in code_chunks:
            await self.bot.error_webhook.send(chunk)

        if mention:
            await self.bot.error_webhook.send(embed=embed)
