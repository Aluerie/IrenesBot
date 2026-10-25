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
    import twitchio

    from . import Bot, Context


__all__ = (
    "Component",
    "DevComponent",
    "PersonalComponent",
)


class ComponentBase(commands.Component):
    """Base component to use within IreBot."""

    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    def is_dev(self, user_id: str) -> bool:
        """Check whether the user is a bot owner."""
        return user_id == self.bot.owner_id


class Component(ComponentBase):
    """Component."""


class PersonalComponent(ComponentBase):
    """Base component to use for personal components.

    Features in personal components are only available in Irene's main and secondary twitch channels.
    """

    @override
    async def component_before_invoke(self, ctx: Context) -> None:  # ty: ignore[invalid-method-override]
        if not self.is_dev(ctx.broadcaster.id):
            msg = "Command is not allowed anywhere except Irene's channel"
            raise errors.NotAllowedError(msg, policy=errors.SILENT)

    def is_human_dev_message(self, message: twitchio.ChatMessage) -> bool:
        """Check that a message has text, was sent in the developer's channel and was not sent by a known bot."""
        return (
            self.is_dev(message.broadcaster.id)
            and bool(message.text)
            and message.chatter.name not in const.BotsLowerName
        )


class DevComponent(ComponentBase):
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
