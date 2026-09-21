"""My custom guards.

Notes
-----
1. Remember, group guards apply to children as well.
2. Due to my weird implementation - each guard also needs an error message
    defined directly in the `IreBot.event_command_error`
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from twitchio.ext import commands

from shared import errors

from . import const

if TYPE_CHECKING:
    from core import IreContext

__all__ = (
    "is_online",
    "is_vps",
)


def is_vps() -> Any:
    """Allow the command to be completed only on VPS machine.

    A bit niche, mainly used for developer commands to interact with VPS machine such as
    kill the bot process or reboot it.
    """

    def predicate(ctx: IreContext) -> bool:
        # Still allow Irene to use the command during the testing;
        if not ctx.bot.subset_mode or ctx.chatter.id == ctx.bot.owner_id:
            return True
        msg = f"Sorry, this command is currently disabled while Irene is testing some stuff {const.FFZ.peepoPolice}"
        raise errors.RespondWithError(msg)

    return commands.guard(predicate)


def is_online() -> Any:
    """Allow the command to be completed only when Irene's stream is online."""

    def predicate(ctx: IreContext) -> bool:
        if ctx.bot.is_online(ctx.broadcaster.id):
            return True
        msg = f"This commands is only allowed when stream is online {const.FFZ.peepoPolice}"
        raise errors.RespondWithError(msg)

    return commands.guard(predicate)


def is_owner_channel() -> Any:
    """Allow the command to be completed only in Irene's stream channel."""

    def predicate(ctx: IreContext) -> bool:
        if ctx.channel.id == ctx.bot.owner_id:
            return True
        # decorators order in twitchio performs
        # `.component_before_invoke` after local decorators
        # so this workaround fixes that order
        msg = f"Command is only allowed in Irene's channel {const.FFZ.peepoPolice}"
        raise errors.SilentError(msg)

    return commands.guard(predicate)


def is_broadcaster_or_dev() -> Any:
    """Allow the command to be completed only by broadcaster or Irene.

    Similar to `@commands.is_broadcaster` but includes Irene too.
    """

    def predicate(ctx: IreContext) -> bool:
        if ctx.chatter.id in {ctx.broadcaster.id, ctx.bot.owner_id}:
            return True
        msg = f"Sorry, this command can only be used by the streamer {const.FFZ.peepoPolice}"
        raise errors.RespondWithError(msg)

    return commands.guard(predicate)


def is_dev() -> Any:
    """Allow the command to be completed only by Irene.

    Similar to `@commands.is_owner`.
    """

    def predicate(ctx: IreContext) -> bool:
        if ctx.chatter.id == ctx.bot.owner_id:
            return True
        msg = f"Sorry, this command can only be used by the developers {const.FFZ.peepoPolice}"
        raise errors.RespondWithError(msg)

    return commands.guard(predicate)
