"""Timers.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import random
from typing import TYPE_CHECKING, override

from twitchio.ext import commands

from core import PersonalComponent
from shared import clock
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    import twitchio

    from core import Bot

MESSAGES: list[str] = [
    f"FIX YOUR POSTURE {const.Bttv.weirdChamp}",
    f"{const.Stv.Adge} {const.Stv.DankApprove}",
    f"Don't forget to stand up, stretch and scoot {const.Stv.GroupScoots}",
    f"{const.Stv.plink}",
    f"{const.Stv.uuh}",
    f"chat don't forget to {const.Stv.plink}",
    (
        "hi chat many features of this bot are WIP so, please, if you notice bugs or incorrect responses - "
        f"inform me {const.Stv.DANKHACKERMANS}"
    ),
    (
        f"Bad image quality? Overlay not working (especially chat/!showemote ones)? Sound issues? "
        f"Please, let me know about any problems {const.Stv.dankFix}"
    ),
    "!showemote ass",
    (
        f"chat I kinda need to grind affiliate on @IrenesBot account. "
        f"Please, follow it and if possible lurk there when I eventually gonna stream from it {const.Stv.DankApprove}"
    ),
]
TIMER_COOLDOWN = dt.timedelta(hours=1)  # minimum time between two timer messages
LINES_NEEDED = 200  # chat lines needed between two timer messages
MIN_WAIT_TIME = 51  # seconds
RANDOM_WAIT_TIME = 61 * 60  # seconds, upper bound of the extra random delay


class Timers(PersonalComponent):
    """Periodic messages and announcements in the developer's channel.

    Attributes
    ----------
    messages
        Shuffled timer messages for the current stream, sent in order.
    index
        Position of the next timer message in `messages`.
    lines_count
        Chat lines counted since the last timer message.
    is_live
        Whether the stream is live, which is when chat lines are counted.
    last_timer_message
        When the last timer message was sent, if any.
    """

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.messages: list[str] = []
        self.index: int = 0
        self.lines_count: int = 0
        self.is_live: bool = False
        self.last_timer_message: dt.datetime | None = None

    @override
    async def component_teardown(self) -> None:
        """Cancel pending background tasks when the component is unloaded."""
        self.send_timer_message.cancel()
        self.random_daily_announcement.cancel()
        await super().component_teardown()

    @commands.Component.listener(name="stream_online")
    async def stream_start(self, online: twitchio.StreamOnline) -> None:
        """Start counting chat lines and the periodic announcement when the stream goes live."""
        if not self.is_dev(online.broadcaster.id):
            return

        self.messages = random.sample(MESSAGES, k=len(MESSAGES))
        self.index = 0
        self.lines_count = 0
        self.is_live = True
        if not self.random_daily_announcement.is_running():
            self.random_daily_announcement.start()

    @commands.Component.listener(name="stream_offline")
    async def stream_end(self, offline: twitchio.StreamOffline) -> None:
        """Stop counting chat lines and cancel everything pending when the stream goes offline."""
        if not self.is_dev(offline.broadcaster.id):
            return

        self.is_live = False
        self.send_timer_message.cancel()
        self.random_daily_announcement.cancel()

    @commands.Component.listener(name="message")
    async def count_messages(self, message: twitchio.ChatMessage) -> None:
        """Count chat lines and schedule a timer message when the conditions are met.

        A timer message is scheduled if enough lines were sent since the previous one and the cooldown has passed.
        """
        if not self.is_live or not self.is_human_dev_message(message):
            return

        self.lines_count += 1
        if self.lines_count <= LINES_NEEDED:
            return
        if self.send_timer_message.is_running():
            return  # one is already scheduled
        if self.last_timer_message and clock.utcnow() - self.last_timer_message < TIMER_COOLDOWN:
            return

        self.send_timer_message.start(message)

    @loop(count=1)
    async def send_timer_message(self, message: twitchio.ChatMessage) -> None:
        """Send the next timer message after a random delay, so the timing is not predictable.

        Cancelled when the stream goes offline.
        """
        await asyncio.sleep(MIN_WAIT_TIME + random.randint(1, RANDOM_WAIT_TIME))
        await message.respond(self.messages[self.index % len(self.messages)])

        self.index += 1
        self.lines_count = 0
        self.last_timer_message = clock.utcnow()

    @loop(hours=5)
    async def random_daily_announcement(self) -> None:
        """Post an announcement in chat every five hours of the stream.

        The first iteration is skipped because it would run right when the stream starts. Friday nights (UTC) get a
        different message.
        """
        if self.random_daily_announcement.current_loop == 0:
            return

        now = clock.utcnow()
        message = (
            f"it's friday night gents {const.Stv.fridayNight} time to dance"
            if (now.weekday() == 4 and now.hour > 18) or (now.weekday() == 5 and now.hour < 6)
            else f"It's time to {const.Stv.Boink}"
        )
        await self.bot.create_partialuser(self.bot.owner_id).send_announcement(
            message=message, moderator=self.bot.bot_id, color="primary"
        )
