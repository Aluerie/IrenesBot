from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine, Sequence
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, override

import discord
from discord.utils import MISSING

from shared.concepts import tasks

if TYPE_CHECKING:
    import datetime

    from core import IreBot

    class HasBotAttribute(Protocol):
        bot: IreBot


log = logging.getLogger(__name__)

__all__ = ("ireloop",)


_func = Callable[..., Coroutine[Any, Any, Any]]
LF = TypeVar("LF", bound=_func)


class IreLoop(tasks.CustomLoop[LF]):
    """My subclass for discord.ext.tasks.Loop.

    Just extra boilerplate functionality.

    Notes
    -----
    Sorry to twitchio guys, but at the moment of writing this `discord.ext.tasks` is way more fleshed out
    and offers a bit more functionality than `twitchio.ext.routines`.

    Warning
    -------
    The task should be initiated in a class that has `.bot` of IreBot type. Otherwise, it will just fail.
    All my tasks (and all my code is in cogs that do have `.bot` but still)

    """

    @override
    async def _wait_for_ready(self, cog: HasBotAttribute) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        await cog.bot.wait_until_ready()

    @override
    async def _error(self, cog: HasBotAttribute, exception: Exception) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Same `_error` as in parent class but with `exc_manager` integrated."""
        embed = discord.Embed(title=f"Task Error `{self.coro.__qualname__}`", colour=0x1A7A8A)
        if exception_data := getattr(exception, "data", None):
            embed = cog.bot.add_codeblock_field(embed, f"Extra {exception.__class__.__name__} Debug Data", exception_data)
        await cog.bot.error_manager.register(exception, embed)


@discord.utils.copy_doc(tasks.custom_loop)
def ireloop(
    *,
    seconds: float = MISSING,
    minutes: float = MISSING,
    hours: float = MISSING,
    time: datetime.time | Sequence[datetime.time] = MISSING,
    count: int | None = None,
    reconnect: bool = True,
    name: str | None = None,
    wait_for_ready: bool = False,
) -> Callable[[LF], IreLoop[LF]]:
    """Copy-pasted `loop` decorator from `discord.ext.tasks` corresponding to AluLoop class.

    Notes
    -----
    * if `discord.ext.tasks` gets extra cool features which will be represented in a change of `tasks.loop`
        decorator/signature we would need to manually update this function (or maybe even AluLoop class)

    """

    def decorator(func: LF) -> IreLoop[LF]:
        return IreLoop(
            func,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            count=count,
            time=time,
            reconnect=reconnect,
            name=name,
            wait_for_ready=wait_for_ready,
        )

    return decorator
