# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Chatter."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import random
import re
from typing import TYPE_CHECKING

from twitchio.ext import commands

from core import Context, PersonalComponent
from shared import clock
from utils import const

if TYPE_CHECKING:
    import twitchio

    from core import Bot

log = logging.getLogger(__name__)

ERM_PATTERN = re.compile(r"\bErm\b")
ERM_NOTIFICATION_CHANCE = 0.005
ERM_NOTIFICATION_COOLDOWN = 180

KEYWORD_PATTERN = re.compile(r"\b(?:Pog|gg|GG|bueno)\b")
KEYWORD_RESPONSE_COOLDOWN = 7 * 60  # seconds
KEYWORD_RESPONSE_CHANCE = 0.02


class Chatter(PersonalComponent):
    """Light chat features for the developer's own Twitch channel.

    Covers
    * the Erm counter
    * the keyword echo responses

    last_erm_notification
        When the bot last posted an Erm total in chat. Used to rate-limit the random Erm notifications.
    last_keyword_response
        When the bot last echoed a keyword in chat. Used to rate-limit keyword responses.
    """

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)

        self.last_erm_notification: dt.datetime = clock.utcnow()
        self.last_keyword_response: dt.datetime = clock.utcnow() - dt.timedelta(seconds=KEYWORD_RESPONSE_COOLDOWN)

    ####################################################################################################################
    # ERM COUNTERS
    ####################################################################################################################

    async def fetch_erm_count(self) -> int:
        """Fetch the current Erm count from the database."""
        query = "SELECT value FROM ttv_counters WHERE name = $1"
        return await self.bot.pool.fetchval(query, "erm") or 0

    @commands.Component.listener(name="message")
    async def count_erms(self, message: twitchio.ChatMessage) -> None:
        """Count Erm emotes in chat and occasionally announce the total.

        Every message containing the emote increments the counter once. Each thousandth Erm gets a milestone
        announcement. Otherwise a short total is posted at random, at most once per three minutes.
        """
        if not self.is_human_dev_message(message):
            return
        if not ERM_PATTERN.search(message.text):
            return

        query = """
            INSERT INTO ttv_counters (name, value)
            VALUES ($1, 1)
            ON CONFLICT (name)
                DO UPDATE SET value = ttv_counters.value + 1
            RETURNING value;
        """
        erm_amount_milestone: int = await self.bot.pool.fetchval(query, "erm")

        now = clock.utcnow()
        # milestone
        if erm_amount_milestone % 1000 == 0:
            self.last_erm_notification = now
            await message.respond(
                f"{const.Stv.wow} we reached a milestone of {erm_amount_milestone} {const.Stv.Erm} in chat"
            )
            return

        # random notification/reminder
        if (
            random.random() < ERM_NOTIFICATION_CHANCE
            and (now - self.last_erm_notification).total_seconds() > ERM_NOTIFICATION_COOLDOWN
        ):
            self.last_erm_notification = now  # claim the slot before any await
            await asyncio.sleep(3)
            await message.respond(f"{await self.fetch_erm_count()} {const.Stv.Erm} in chat.")

    @commands.command(aliases=["erm"])
    async def erms(self, ctx: Context) -> None:
        """Show how many Erms chat has sent so far."""
        await ctx.send(f"{await self.fetch_erm_count()} {const.Stv.Erm} in chat.")

    ####################################################################################################################
    # KEYWORDS
    ####################################################################################################################

    @commands.Component.listener(name="message")
    async def keywords_response(self, message: twitchio.ChatMessage) -> None:
        """Echo a keyword or key phrase spotted in chat as a flavour message.

        Only whole words count. To avoid spam, a response is sent with a low chance and at most once per cooldown
        period, even if a message contains several keywords.
        """
        if not self.is_human_dev_message(message):
            return

        match = KEYWORD_PATTERN.search(message.text)
        if match is None:
            return

        now = clock.utcnow()
        if (now - self.last_keyword_response).total_seconds() < KEYWORD_RESPONSE_COOLDOWN:
            return  # the keyword was recently triggered
        if random.random() >= KEYWORD_RESPONSE_CHANCE:
            return  # most keywords are ignored so that the bot doesn't spam

        self.last_keyword_response = now  # claim the cooldown before any await
        await message.respond(match.group())


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(Chatter(bot))
