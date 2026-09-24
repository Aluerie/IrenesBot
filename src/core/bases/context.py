from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, override

from twitchio.ext import commands

from modules import MODULES_EMOTE_MAPPING
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

    @override
    async def send(self, content: str, *, me: bool = False, use_suffix: bool = True) -> twitchio.SentMessage:
        if use_suffix:
            # https://stackoverflow.com/a/1095621/19217368
            parent_frame_info = inspect.stack()[1]
            mod = inspect.getmodule(parent_frame_info.frame)
            if mod:
                suffix = MODULES_EMOTE_MAPPING.get(mod.__name__)
                content = f"{content} {suffix}"
        return await super().send(content, me=me)
