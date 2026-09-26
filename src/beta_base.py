"""
Base class for BetaCog for `modules.beta.py`.

In `modules.beta.py` I quickly beta-test some things. It's a bit silly but very efficient.

The purpose of the current file is to minimize amount of imports and lines of code
for anything we're going to do while beta-testing. The performance cost of extra imports is probably
negligible compared to annoyance to type them manually out every time we need them.

For an example of how starting template for `modules.beta.py` looks - you can look in `examples` folder.
"""

#  pyright: basic

from __future__ import annotations

import asyncio
import datetime
import itertools
import logging
import platform
from typing import TYPE_CHECKING, Any, Literal, override

import aiohttp
import twitchio
from twitchio.ext import commands

from config import env
from core import IreDevComponent, ireloop
from shared import errors
from utils import const

if TYPE_CHECKING:
    from core import IreBot, IreContext

log = logging.getLogger(__name__)


class BetaCog(IreDevComponent):
    """Base Class for BetaTest cog.

    Used to test random code snippets.
    """

    def __init__(self, bot: IreBot) -> None:
        super().__init__(bot)
        self.beta_test.start()

    @ireloop(count=1)
    async def beta_test(self) -> None:
        """Task that is supposed to run just once to test stuff out."""
        await self.beta_test_task_count_1()

    async def beta_test_task_count_1(self) -> None:
        """Worker function for `self.beta_test` ireloop task."""
        raise NotImplementedError
