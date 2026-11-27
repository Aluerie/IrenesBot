# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Reminders: ``!remind 10m stretch`` pings you in chat when the time comes.

* One-off ("10m", "tomorrow 3pm", "18:00 MSK") or repeating ("every friday 18:00") reminders.
* ``!remind live <text>`` pings you when the channel goes live.
* ``!remind tz MSK`` remembers your timezone, so "3pm" means 3pm on your clocks.

Reminders are jobs of `shared.scheduler`, so they survive restarts. A reminder arrives as a reply
to the chat message it was set with (or as a plain message if that one is gone).
"""

from __future__ import annotations

import datetime as dt
import textwrap
import zoneinfo
from typing import TYPE_CHECKING, Final, TypedDict

import twitchio
from loguru import logger
from twitchio.ext import commands

from core import Component
from shared import clock, errors, scheduler
from shared.timeparse import describe, describe_rule, resolve_timezone, split_time
from utils import const
lazy from shared.scheduler import Job

if TYPE_CHECKING:
    from core import Bot, Context

__all__ = ("Reminders",)

KIND: Final = "reminder"
LIVE_KIND: Final = "live_reminder"
"""Reminders for when the stream starts: the `stream_online` event runs them right away (`Scheduler.run_now`)."""
LIVE_EXPIRES_AFTER: Final = dt.timedelta(days=30)
"""A stream-start reminder whose stream didn't start this long is dropped quietly (its due time is this expiry)."""
TIMEZONE: Final = "UTC"
"""Clock times like "3pm" are read on these clocks, unless the chatter saved a timezone (``!remind tz``)
or names one ("3pm EST", "18:00 MSK"): Twitch doesn't tell the bot anybody's timezone."""
MAX_TEXT_LENGTH: Final = 300
MAX_REMINDERS_PER_USER: Final = 10
"""Limit per chatter (the bot owner has none), so the chat doesn't turn into a reminder spam."""
LATE_AFTER: Final = dt.timedelta(minutes=5)
"""Reminders later than this apologize for it (e.g. the bot was offline at the time)."""
USAGE: Final = (
    'Usage: "!remind 10m stretch", "!remind tomorrow 3pm water the plants", "!remind every friday 18:00 MSK lunch", '
    '"!remind live <text>". Also: "!remind list", "!remind delete <id>", "!remind clear", "!remind tz <timezone>".'
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
        self._timezones: dict[int, str | None] = {}
        """Cache of the chatters' saved timezones (`None`: they have none)."""

    # --- TIMEZONES ----------------------------------------------------------------------------------------------------

    async def chatter_timezone(self, user_id: int) -> str | None:
        """Get the timezone a chatter saved with ``!remind tz``, if any."""
        if user_id not in self._timezones:
            query = "SELECT timezone FROM chatter_timezones WHERE user_id = $1"
            self._timezones[user_id] = await self.bot.pool.fetchval(query, user_id)
        return self._timezones[user_id]

    # --- COMMANDS -----------------------------------------------------------------------------------------------------

    def name_of(self, ctx: Context) -> str:
        """Get the chatter's name to mention them."""
        return ctx.chatter.display_name or ctx.chatter.name or ctx.chatter.id

    async def check_limit(self, ctx: Context) -> None:
        """Refuse a new reminder to chatters (but the owner) who have the most they may have."""
        if self.is_dev(ctx.chatter.id):
            return
        user_id = int(ctx.chatter.id)
        total = await self.jobs.count(KIND, user_id=user_id) + await self.jobs.count(LIVE_KIND, user_id=user_id)
        if total >= MAX_REMINDERS_PER_USER:
            msg = f"You have {MAX_REMINDERS_PER_USER} reminders already, delete some with !remind delete <id> first."
            raise errors.BadUserInputError(msg)

    @commands.cooldown(rate=3, per=30, key=commands.BucketType.chatter)
    @commands.group(name="remind", aliases=["remindme", "reminder"], invoke_fallback=True)
    async def remind_group(self, ctx: Context, *, text: str = "") -> None:
        """Remind you in chat after some time, at some time, or again and again.

        Start with the time, then say what to remind of: ``!remind 10m stretch``,
        ``!remind tomorrow 3pm water the plants``, ``!remind every friday 18:00 lunch``.
        Clock times like "3pm" are in UTC, unless you name your timezone (``!remind 18:00 MSK stretch``)
        or save it with ``!remind tz MSK``. The reminder arrives as a reply to your message.
        """
        if not text.strip():
            raise errors.BadUserInputError(USAGE)

        now = clock.utcnow()
        timezone = await self.chatter_timezone(int(ctx.chatter.id)) or TIMEZONE
        parsed, rest = split_time(text, now=now, timezone=timezone)
        rest = rest or "⏰"
        if len(rest) > MAX_TEXT_LENGTH:
            msg = f"Reminders must be at most {MAX_TEXT_LENGTH} characters long."
            raise errors.BadUserInputError(msg)
        await self.check_limit(ctx)

        data: ReminderData = {"text": rest, "user_name": self.name_of(ctx), "message_id": ctx.message.id}
        job = await self.jobs.schedule(
            KIND,
            parsed.when,
            data=data,
            user_id=int(ctx.chatter.id),
            guild_id=int(ctx.broadcaster.id),
            rule=parsed.rule,
        )
        await ctx.send(
            f"@{self.name_of(ctx)} okay, reminder #{job.id}: "
            f"{describe(parsed, now=now, timezone=timezone)} {const.Stv.DankApprove}"
        )

    @remind_group.command(name="live", aliases=["stream", "online"])
    async def remind_live(self, ctx: Context, *, text: str = "") -> None:
        """Remind you when this channel goes live, e.g. ``!remind live watch the start``."""
        if len(text) > MAX_TEXT_LENGTH:
            msg = f"Reminders must be at most {MAX_TEXT_LENGTH} characters long."
            raise errors.BadUserInputError(msg)
        await self.check_limit(ctx)
        data: ReminderData = {"text": text or "🔴", "user_name": self.name_of(ctx), "message_id": ctx.message.id}
        job = await self.jobs.schedule(
            LIVE_KIND,
            clock.utcnow() + LIVE_EXPIRES_AFTER,
            data=data,
            user_id=int(ctx.chatter.id),
            guild_id=int(ctx.broadcaster.id),
        )
        days = LIVE_EXPIRES_AFTER.days
        await ctx.send(
            f"@{self.name_of(ctx)} okay, reminder #{job.id}: I'll ping you when the stream starts "
            f"(if it does within {days} days) {const.Stv.DankApprove}"
        )

    @remind_group.command(name="list", aliases=["all"])
    async def remind_list(self, ctx: Context) -> None:
        """Show your reminders in this channel."""
        user_id, channel_id = int(ctx.chatter.id), int(ctx.broadcaster.id)
        jobs: list[Job[ReminderData]] = [
            *await self.jobs.fetch(KIND, user_id=user_id, guild_id=channel_id),
            *await self.jobs.fetch(LIVE_KIND, user_id=user_id, guild_id=channel_id),
        ]
        if not jobs:
            await ctx.send(f"@{self.name_of(ctx)} you don't have any reminders here.")
            return
        now = clock.utcnow()
        entries: list[str] = []
        for job in jobs:
            if job.kind == LIVE_KIND:
                when = "🔴 when live"
            else:
                when = f"in {clock.human_datetime_diff(job.fire_at, relative_to=now, max_units=1)}"
                if job.rule is not None:
                    when += f" (🔁 {describe_rule(job.rule)})"
            entries.append(f"#{job.id} {when}: {shorten(job.data['text'], 40)}")
        await ctx.chunk_send(f"@{self.name_of(ctx)} your reminders: " + " | ".join(entries))

    @remind_group.command(name="delete", aliases=["cancel", "remove", "del", "stop"])
    async def remind_delete(self, ctx: Context, reminder_id: int) -> None:
        """Delete one of your reminders by its ID (a repeating one stops), e.g. ``!remind delete 12``."""
        user_id = int(ctx.chatter.id)
        deleted = await self.jobs.delete(reminder_id, kind=KIND, user_id=user_id) or await self.jobs.delete(
            reminder_id, kind=LIVE_KIND, user_id=user_id
        )
        if deleted is None:
            msg = f"You don't have a reminder #{reminder_id}, see !remind list."
            raise errors.BadUserInputError(msg)
        await ctx.send(f"@{self.name_of(ctx)} deleted reminder #{reminder_id}: {shorten(deleted.data['text'])}")

    @remind_group.command(name="clear")
    async def remind_clear(self, ctx: Context) -> None:
        """Delete all your reminders in this channel."""
        user_id, channel_id = int(ctx.chatter.id), int(ctx.broadcaster.id)
        deleted = [
            *await self.jobs.delete_where(KIND, user_id=user_id, guild_id=channel_id),
            *await self.jobs.delete_where(LIVE_KIND, user_id=user_id, guild_id=channel_id),
        ]
        await ctx.send(f"@{self.name_of(ctx)} deleted {len(deleted)} reminders.")

    @remind_group.command(name="tz", aliases=["timezone"])
    async def remind_timezone(self, ctx: Context, *, timezone: str = "") -> None:
        """Save your timezone for reminders (``!remind tz MSK``), show it (``!remind tz``) or forget it (``clear``)."""
        user_id = int(ctx.chatter.id)
        if not timezone.strip():
            saved = await self.chatter_timezone(user_id)
            if saved is not None:
                content = f"your timezone is {saved}."
            else:
                content = f"you haven't saved a timezone, times are in {TIMEZONE}."
            await ctx.send(f"@{self.name_of(ctx)} {content} Save one with e.g. !remind tz MSK")
            return
        if timezone.strip().lower() in {"clear", "reset", "forget", "none"}:
            await self.bot.pool.execute("DELETE FROM chatter_timezones WHERE user_id = $1", user_id)
            self._timezones[user_id] = None
            await ctx.send(f"@{self.name_of(ctx)} forgot your timezone, times are in {TIMEZONE} again.")
            return

        key = resolve_timezone(timezone)
        query = """
            INSERT INTO chatter_timezones (user_id, timezone) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET timezone = EXCLUDED.timezone, updated_at = NOW()
        """
        await self.bot.pool.execute(query, user_id, key)
        self._timezones[user_id] = key
        local = clock.utcnow().astimezone(zoneinfo.ZoneInfo(key))
        await ctx.send(
            f"@{self.name_of(ctx)} saved: {key} (it's {local:%H:%M} there now). "
            f"Your reminders' times are read in it from now on {const.Stv.DankApprove}"
        )

    # --- ARRIVING -----------------------------------------------------------------------------------------------------

    @commands.Component.listener(name="stream_online")
    async def run_live_reminders(self, online: twitchio.StreamOnline) -> None:
        """Fire the stream-start reminders of the channel that just went live."""
        jobs = await self.jobs.fetch(LIVE_KIND, guild_id=int(online.broadcaster.id))
        for job in jobs:
            await self.jobs.run_now(job.id, kind=LIVE_KIND)
        if jobs:
            logger.info("Stream of {} is live: firing {} stream-start reminders.", online.broadcaster.id, len(jobs))

    @scheduler.handler(KIND, retry_delay=dt.timedelta(seconds=30))
    async def send_reminder(self, job: Job[ReminderData]) -> None:
        """Ping the chatter in the channel: a reply to the message the reminder was set with."""
        data = job.data
        message = f"@{data['user_name']} ⏰ {data['text']}"
        if job.lateness > LATE_AFTER:
            late = clock.human_timedelta(job.lateness, max_units=1)
            message += f" (sorry, {late} late, I was offline {const.Stv.uuh})"
        elif job.rule is not None:
            message += f" (🔁 {describe_rule(job.rule)}, !remind delete {job.id} to stop)"
        else:
            message += f" (set {clock.human_datetime_diff(job.created_at, max_units=1)} ago)"
        await self.send(job, message)

    @scheduler.handler(LIVE_KIND, retry_delay=dt.timedelta(seconds=30))
    async def send_live_reminder(self, job: Job[ReminderData]) -> None:
        """Ping the chatter when the stream started (`run_now` sets `retry_at`); at the expiry, drop it quietly."""
        if job.retry_at is None:
            logger.info("Stream-start reminder {} expired: the stream didn't start in time.", job.id)
            return
        await self.send(job, f"@{job.data['user_name']} 🔴 the stream is live: {job.data['text']}")

    async def send(self, job: Job[ReminderData], message: str) -> None:
        """Send a reminder to the job's channel, as a reply to the message it was set with if that still works."""
        message = message[: const.MAX_MESSAGE_LENGTH]
        message_id = job.data["message_id"]
        broadcaster = self.bot.create_partialuser(str(job.guild_id))
        try:
            sent = await broadcaster.send_message(message, sender=self.bot.bot_id, reply_to_message_id=message_id)
        except twitchio.HTTPException as exc:
            if message_id is None or exc.status >= 500:
                raise  # retried
            # the message to reply to is gone (deleted, or too old to reply to): no reply then
            sent = await broadcaster.send_message(message, sender=self.bot.bot_id)
        if not sent.sent:
            # dropped by Twitch (e.g. AutoMod): retrying would be dropped again
            logger.warning("Reminder {} was dropped: {} {}", job.id, sent.dropped_code, sent.dropped_message)


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(Reminders(bot))
