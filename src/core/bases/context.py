"""Context.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import twitchio
from twitchio.ext import commands

from shared import errors

if TYPE_CHECKING:
    from core import IreBot  # ruff: ignore[unused-import]


class IreContext(commands.Context["IreBot"]):
    """My custom context."""

    if TYPE_CHECKING:
        # I will only use IreContext with message commands
        # (twitchio also provides Channel Points commands).
        # therefore some type-hints can be reduced for convenience.
        chatter: twitchio.Chatter
        message: twitchio.ChatMessage

    async def group_default_response(self) -> None:
        """Get a default response for group commands.

        Answers with a list of subcommands.
        """
        if not isinstance(self.command, commands.Group):
            msg = "`group_default_response` was called from a non-group command"
            raise errors.SomethingWentWrongError(msg)
        if self.invoked_with is None:
            msg = "`self.invoked_with` is None for some reason."
            raise errors.SomethingWentWrongError(msg)

        relative_name = self.command.relative_name.strip()
        invoked_with = self.invoked_with.strip()

        prefix = (
            f'"{relative_name}" is a group command, '
            if invoked_with == relative_name
            else f"Wrong subcommand '{invoked_with.removeprefix(relative_name)}',"
        )
        await self.send(
            content=(
                f"{prefix}"
                f" available subcommands: {', '.join(self.command.commands)}, "
                f'e.g. "{relative_name} {next(iter(self.command.commands))}".'
            )
        )

    @override
    async def send(self, content: str, *, me: bool = False) -> twitchio.SentMessage:
        try:
            return await super().send(content, me=me)
        except twitchio.MessageRejectedError:
            # Bypass this error with a 7TV trick of adding an unknown character (32 is space though)
            return await super().send(content + chr(32) + chr(917504), me=me)
