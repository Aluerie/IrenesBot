"""Component.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from twitchio.ext import commands

from shared import errors
from utils import const

if TYPE_CHECKING:
    from . import Context, IreBot


__all__ = ("IreDevComponent", "IrePersonalComponent", "IrePublicComponent")


class IreComponent(commands.Component):
    """Base component to use within IreBot."""

    def __init__(self, bot: IreBot) -> None:
        self.bot: IreBot = bot

    def is_dev(self, user_id: str) -> bool:
        """Check whether the user is a bot owner."""
        return user_id == self.bot.owner_id


class IrePublicComponent(IreComponent):
    """Base component to use for public components."""


class IrePersonalComponent(IreComponent):
    """Base component to use for personal components.

    Features in personal components are only available in Irene's main and secondary twitch channels.
    """

    @override
    async def component_before_invoke(self, ctx: Context) -> None:  # ty: ignore[invalid-method-override]
        if not self.is_dev(ctx.broadcaster.id):
            msg = "Command is not allowed anywhere except Irene's channel"
            raise errors.NotAllowedError(msg, policy=errors.SILENT)


class IreDevComponent(IreComponent):
    """Base component to use for developer components.

    Double-ensures that commands have owner-only check.
    """

    @override
    async def component_before_invoke(self, ctx: Context) -> None:  # ty: ignore[invalid-method-override]
        if ctx.chatter.id != ctx.bot.owner_id:
            msg = f"Command is not allowed by anybody else except Irene {const.Ffz.peepoPolice}"
            if ctx.broadcaster.id == ctx.bot.owner_id:
                raise errors.NotAllowedError(msg)
            raise errors.NotAllowedError(msg, policy=errors.SILENT)
