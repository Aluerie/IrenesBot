from __future__ import annotations

from typing import TYPE_CHECKING

from twitchio.ext import commands

from shared import errors

if TYPE_CHECKING:
    import twitchio

    from core import IreBot


class IreContext(commands.Context["IreBot"]):
    """My custom context."""

    if TYPE_CHECKING:
        # I will only use IreContext with message commands
        # (twitchio also provides Channel Points commands).
        # therefore some type-hints can be reduced for convenience.
        chatter: twitchio.Chatter  # pyright: ignore[reportIncompatibleMethodOverride]
        message: twitchio.ChatMessage  # pyright: ignore[reportIncompatibleMethodOverride]

    async def group_default_response(self) -> None:
        """Default group response.

        Answers with a list of subcommands.
        """
        if not isinstance(self.command, commands.Group):
            msg = "`group_default_response` was called from a non-group command"
            raise errors.SomethingWentWrongError(msg)
        if self.invoked_with is None:
            msg = "`self.invoked_with` is None for some reason."
            raise errors.SomethingWentWrongError(msg)

        invoked_strip = self.invoked_with.strip()
        await self.send(
            content=(
                f'"{invoked_strip}" is a group command, use it together with one of '
                f"the children: {', '.join(self.command.commands)}, "
                f'e.g. "{invoked_strip} {next(iter(self.command.commands))}".'
            )
        )
