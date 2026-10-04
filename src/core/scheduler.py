"""Scheduler.

Sources
-------
The code below is largely taken/inspired by these (a lot to learn from these):
* @mikeshardmind's scheduler https://github.com/mikeshardmind/discord-scheduler
* @Rapptz's reminders cog https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/reminder.py

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

# from __future__ import annotations

# import asyncio
# from typing import Self

# __all__ = ("Scheduler",)


# class Scheduler:
#     def __init__(self, *, use_threads: bool = False) -> None:
#         self._use_threads: bool = use_threads

#     # async def __aenter__(self: Self) -> Self:
#     #     self._zones = _setup_db(self._connection)
#     #     self._ready = True
#     #     self._loop_task = asyncio.create_task(self._loop())
#     #     self._loop_task.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
#     #     return self
