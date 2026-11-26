# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Reminders: ``!remind 10m stretch`` pings you in chat when the time comes.

Reminders are jobs of `shared.scheduler`, so they survive restarts. A reminder arrives as a reply
to the chat message it was set with (or as a plain message if that one is gone).
"""

from __future__ import annotations

import datetime as dt
import textwrap
from typing import TYPE_CHECKING, Final, TypedDict

import twitchio
from loguru import logger
from twitchio.ext import commands

from core import Component
from shared import clock, errors, scheduler
from shared.timeparse import describe, split_time
from utils import const
lazy from shared.scheduler import Job

if TYPE_CHECKING:
    from core import Bot, Context

__all__ = ("Reminders",)

KIND: Final = "reminder"
TIMEZONE: Final = "UTC"
"""Clock times like "3pm" are read on these clocks: Twitch chatters can't set their own timezone."""
MAX_TEXT_LENGTH: Final = 300
MAX_REMINDERS_PER_USER: Final = 10
"""Limit per chatter (the bot owner has none), so the chat doesn't turn into a reminder spam."""
LATE_AFTER: Final = dt.timedelta(minutes=5)
"""Reminders later than this apologize for it (e.g. the bot was offline at the time)."""
MAX_MESSAGE_LENGTH: Final = 500
USAGE: Final = (
    'Usage: "!remind 10m stretch", "!remind tomorrow 3pm water the plants", "!remind eow to send the report". '
    'Also: "!remind list", "!remind delete <id>", "!remind clear".'
)


class ReminderData(TypedDict, closed=True):
    """Data of a reminder job; the chatter is the job's `user_id`, the channel (broadcaster) its `guild_id`."""

    text: str
    user_name: str
    """Display name of the chatter, to mention them."""
    message_id: str | None
    """The chat message the reminder replies to when it arrives."""


def shorten(text: str, width: int = 60) -> str:
    """Shorten the text of a reminder for chat replies."""
    return textwrap.shorten(text, width=width, placeholder="…")


class Reminders(Component):
    """Reminders in chat."""

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.jobs: scheduler.Scheduler = bot.scheduler

    # --- COMMANDS -----------------------------------------------------------------------------------------------------

    @commands.cooldown(rate=3, per=30, key=commands.BucketType.chatter)
    @commands.group(name="remind", aliases=["remindme", "reminder"], invoke_fallback=True)
    async def remind_group(self, ctx: Context, *, text: str = "") -> None:
        """Remind you in chat after some time or at some time.

        Start with the time, then say what to remind of: ``!remind 10m stretch``,
        ``!remind tomorrow 3pm water the plants``, ``!remind eow to send the report``.
        Clock times like "3pm" are in UTC. The reminder arrives as a reply to your message.
        """
        if not text.strip():
            raise errors.BadUserInputError(USAGE)

        now = clock.utcnow()
        parsed, rest = split_time(text, now=now, timezone=TIMEZONE)
        rest = rest or "⏰"
        if len(rest) > MAX_TEXT_LENGTH:
            msg = f"Reminders must be at most {MAX_TEXT_LENGTH} characters long."
            raise errors.BadUserInputError(msg)

        user_id = int(ctx.chatter.id)
        if not self.is_dev(ctx.chatter.id) and await self.jobs.count(KIND, user_id=user_id) >= MAX_REMINDERS_PER_USER:
            msg = f"You have {MAX_REMINDERS_PER_USER} reminders already, delete some with !remind delete <id> first."
            raise errors.BadUserInputError(msg)

        user_name = ctx.chatter.display_name or ctx.chatter.name or ctx.chatter.id
        data: ReminderData = {"text": rest, "user_name": user_name, "message_id": ctx.message.id}
        job = await self.jobs.schedule(KIND, parsed.when, data=data, user_id=user_id, guild_id=int(ctx.broadcaster.id))
        await ctx.send(
            f"@{ctx.chatter.display_name} okay, reminder #{job.id}: "
            f"{describe(parsed, now=now, timezone=TIMEZONE)} {const.Stv.DankApprove}"
        )

    @remind_group.command(name="list", aliases=["all"])
    async def remind_list(self, ctx: Context) -> None:
        """Show your reminders in this channel."""
        jobs: list[Job[ReminderData]] = await self.jobs.fetch(
            KIND, user_id=int(ctx.chatter.id), guild_id=int(ctx.broadcaster.id)
        )
        if not jobs:
            await ctx.send(f"@{ctx.chatter.display_name} you don't have any reminders here.")
            return
        now = clock.utcnow()
        entries = [
            f"#{job.id} in {clock.human_datetime_diff(job.fire_at, relative_to=now, max_units=1)}: "
            f"{shorten(job.data['text'], 40)}"
            for job in jobs
        ]
        await ctx.chunk_send(f"@{ctx.chatter.display_name} your reminders: " + " | ".join(entries))

    @remind_group.command(name="delete", aliases=["cancel", "remove", "del"])
    async def remind_delete(self, ctx: Context, reminder_id: int) -> None:
        """Delete one of your reminders by its ID, e.g. ``!remind delete 12``."""
        deleted = await self.jobs.delete(reminder_id, kind=KIND, user_id=int(ctx.chatter.id))
        if deleted is None:
            msg = f"You don't have a reminder #{reminder_id}, see !remind list."
            raise errors.BadUserInputError(msg)
        await ctx.send(f"@{ctx.chatter.display_name} deleted reminder #{reminder_id}: {shorten(deleted.data['text'])}")

    @remind_group.command(name="clear")
    async def remind_clear(self, ctx: Context) -> None:
        """Delete all your reminders in this channel."""
        deleted = await self.jobs.delete_where(KIND, user_id=int(ctx.chatter.id), guild_id=int(ctx.broadcaster.id))
        await ctx.send(f"@{ctx.chatter.display_name} deleted {len(deleted)} reminders.")

    # --- ARRIVING -----------------------------------------------------------------------------------------------------

    @scheduler.handler(KIND, retry_delay=dt.timedelta(seconds=30))
    async def send_reminder(self, job: Job[ReminderData]) -> None:
        """Ping the chatter in the channel: a reply to the message the reminder was set with."""
        data = job.data
        message = f"@{data['user_name']} ⏰ {data['text']}"
        if job.lateness > LATE_AFTER:
            late = clock.human_timedelta(job.lateness, max_units=1)
            message += f" (sorry, {late} late, I was offline {const.Stv.uuh})"
        else:
            message += f" (set {clock.human_datetime_diff(job.created_at, max_units=1)} ago)"
        message = message[:MAX_MESSAGE_LENGTH]

        broadcaster = self.bot.create_partialuser(str(job.guild_id))
        try:
            sent = await broadcaster.send_message(
                message, sender=self.bot.bot_id, reply_to_message_id=data["message_id"]
            )
        except twitchio.HTTPException as exc:
            if data["message_id"] is None or exc.status >= 500:
                raise  # retried
            # the message to reply to is gone (deleted, or too old to reply to): no reply then
            sent = await broadcaster.send_message(message, sender=self.bot.bot_id)
        if not sent.sent:
            # dropped by Twitch (e.g. AutoMod): retrying would be dropped again
            logger.warning("Reminder {} was dropped: {} {}", job.id, sent.dropped_code, sent.dropped_message)


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(Reminders(bot))
