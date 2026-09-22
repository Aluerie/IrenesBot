from __future__ import annotations

import asyncio
import datetime
import random
from typing import TYPE_CHECKING, Any

from twitchio.ext import commands

from core import IrePersonalComponent, ireloop
from utils import const

if TYPE_CHECKING:
    import twitchio

    from core import IreBot

MESSAGES: list[str] = [
    f"FIX YOUR POSTURE {const.BTTV.weirdChamp}",
    f"{const.STV.Adge} {const.STV.DankApprove}",
    f"Don't forget to stand up, stretch and scoot {const.STV.GroupScoots}",
    f"{const.STV.plink}",
    f"{const.STV.uuh}",
    f"chat don't forget to {const.STV.plink}",
    (
        "hi chat many features of this bot are WIP so, please, if you notice bugs or incorrect responses - "
        f"inform me {const.STV.DANKHACKERMANS}"
    ),
    (
        f"Bad image quality? Overlay not working (especially chat/!showemote ones)? Sound issues? "
        f"Please, let me know about any problems {const.STV.dankFix}"
    ),
    "!showemote ass",
    (
        f"chat I kinda need to grind affiliate on @IrenesBot account. "
        f"Please, follow it and if possible lurk there when I eventually gonna stream from it {const.STV.DankApprove}"
    ),
    # (
    #     "hey chat I'm making a small web-page to describe the bot's features (WIP)."
    #     "You can see it here: (not implemented xdd)"
    # ),
    # "Discord discord.gg/K8FuDeP",
]
LINES_NEEDED_CD = 151
MIN_WAIT_TIME = 51
RANDOM_WAIT_TIME = 61 * 60


class Timers(IrePersonalComponent):
    """Periodic messages/announcements in Aluerie's channel."""

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)

        self.lines_count: int = 0
        self.index: int = 0
        self.cooldown: datetime.timedelta = datetime.timedelta(hours=1)
        self._most_recent: datetime.datetime | None = None
        self._lock: asyncio.Lock = asyncio.Lock()

        self.messages = MESSAGES

    @commands.Component.listener(name="stream_online")
    async def stream_online_start_the_task(self, online: twitchio.StreamOffline) -> None:
        """Start counting messages when stream goes online."""
        if not self.is_dev(online.broadcaster.id):
            return

        random.shuffle(self.messages)
        self.index = 0
        self.lines_count = 0
        self.bot.add_listener(self.count_messages, event="event_message")
        self.random_daily_announcement.start()

    @commands.Component.listener(name="stream_offline")
    async def stream_offline_cancel_the_task(self, offline: twitchio.StreamOffline) -> None:
        """Cancel the counting messages listener when stream goes offline."""
        if not self.is_dev(offline.broadcaster.id):
            return

        self.bot.remove_listener(self.count_messages)
        self.random_daily_announcement.cancel()

    # @commands.Component.listener(name="message")
    async def count_messages(self, message: twitchio.ChatMessage) -> None:
        """The listener responsible for sending timer-messages.

        Timer messages are sent if the following conditions are met
        * there were X amount of messages in the chat between bot timer-messages
        * Y time passed between those.

        If these two are fulfilled then the bot sends a semi-periodic message in the chat.
        """
        if not self.is_dev(message.broadcaster.id):
            return

        if message.chatter.name in const.BotsLowerName:
            # do not count messages from known bot accounts
            return

        self.lines_count += 1
        async with self._lock:
            if self._most_recent and (datetime.datetime.now(datetime.UTC) - self._most_recent) < self.cooldown:
                # we already have a timer to send
                return

            if self.lines_count > LINES_NEEDED_CD:
                await asyncio.sleep(MIN_WAIT_TIME + random.randint(1, RANDOM_WAIT_TIME))
                await message.respond(self.messages[self.index % len(self.messages)])

                # reset the index vars
                self.index += 1
                self.lines_count = 0
                self._most_recent = datetime.datetime.now(datetime.UTC)

    @ireloop(hours=5)
    async def random_daily_announcement(self) -> None:
        """It's time to boink."""
        if self.random_daily_announcement.current_loop == 0:
            return

        now = datetime.datetime.now(datetime.UTC)
        message = (
            f"it's friday night gents {const.STV.fridayNight} time to dance"
            if (now.weekday == 4 and now.hour > 18) or (now.weekday == 5 and now.hour < 6)
            else f"It's time to {const.STV.Boink}"
        )
        await self.bot.create_partialuser(self.bot.owner_id).send_announcement(
            message=message, moderator=self.bot.bot_id, color="primary"
        )


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(Timers(bot))
