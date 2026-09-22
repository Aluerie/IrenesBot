from __future__ import annotations

from typing import TYPE_CHECKING, override

from twitchio.ext import commands

from shared import errors
from utils import const

if TYPE_CHECKING:
    from core import IreBot, IreContext


__all__ = ("IreDevComponent", "IrePersonalComponent", "IrePublicComponent")


class IreComponent(commands.Component):
    """Base component to use within IreBot."""

    def __init__(self, bot: IreBot) -> None:
        self.bot: IreBot = bot

    def is_dev(self, user_id: str) -> bool:
        """A check whether the user is a bot owner."""
        return user_id == self.bot.owner_id


class IrePublicComponent(IreComponent):
    """Base component to use for public modules."""


class IrePersonalComponent(IreComponent):
    """Base component to use for personal modules.

    Features in personal components are only available in Irene's main and secondary twitch channels.
    """

    @override
    async def component_before_invoke(self, ctx: IreContext) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        if not self.is_dev(ctx.broadcaster.id):
            msg = "Command is not allowed anywhere except Irene's channel"
            raise errors.SilentError(msg)


class IreDevComponent(IreComponent):
    """Base component to use for developer modules.

    Double-ensures that commands have owner-only check.
    """

    @override
    async def component_before_invoke(self, ctx: IreContext) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        if ctx.chatter.id != ctx.bot.owner_id:
            msg = f"Command is not allowed by anybody else except Irene {const.FFZ.peepoPolice}"
            if ctx.broadcaster.id == ctx.bot.owner_id:
                raise errors.RespondWithError(msg)
            raise errors.SilentError(msg)
