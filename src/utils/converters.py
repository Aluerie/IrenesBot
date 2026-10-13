"""Converters.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple, override

from twitchio.ext import commands

from shared import errors

if TYPE_CHECKING:
    from core import IreContext


def flag_parser(
    user_input: str,
    flags: list[str],
    *,
    positional: bool = True,
    prefix: str = "",
    delimiter: str = ":",
) -> dict[str, str | None]:
    result: dict[str, str | None] = dict.fromkeys(flags)
    joined = "|".join(flags)
    pattern = re.compile(f"(({re.escape(prefix)})(?P<flag>{joined}){re.escape(delimiter)})", re.IGNORECASE)
    last_position: int = 0
    last_flag: str | None = None

    if positional:
        match = pattern.search(user_input)
        if match is not None:
            begin, end = match.span(0)
            value = user_input[:begin].strip()
        else:
            value = user_input.strip()
            last_position = len(user_input)

        if value:
            result["_positional"] = value

    for match in pattern.finditer(user_input):
        begin, end = match.span(0)
        flag = match.group("flag").lower()

        if last_position and last_flag is not None:
            value = user_input[last_position : begin - 1].lstrip()
            if not value:
                msg = f"This command requires flag `{last_flag}:`"
                raise errors.RespondWithError(msg)  # raise MissingFlagArgument(last_flag)

            name = last_flag

            result[name] = value

        last_position = end
        last_flag = flag

    # Get the remaining string, if applicable
    value = user_input[last_position:].strip()
    # Add the remaining string to the last available flag
    if last_flag is not None:
        if not value:
            msg = f"This command requires flag `{last_flag}:`"
            raise errors.RespondWithError(msg)  # raise MissingFlagArgument(last_flag)

        name = last_flag

        result[name] = value
    elif value:
        # If we're here then we passed extra arguments that aren't flags
        msg = "Too many flag arguments passed to this command"
        raise errors.RespondWithError(msg)
        # raise TooManyArguments(f"Too many arguments passed to {cls.__name__}")

    # Verification of values will come at a later stage
    return result


class TranslateArgs(NamedTuple):
    text: str
    to: str = "en"
    from_: str = "auto"


class TranslateConverter(commands.Converter[TranslateArgs]):
    """Translate Converter."""

    @override
    async def convert(self, ctx: IreContext, user_input: str) -> TranslateArgs:  # ty: ignore[invalid-method-override]
        """Convert `user_input` to 7TV emote_id."""
        flags = flag_parser(user_input, flags=["to", "from"])
        if "_positional" not in flags or flags["_positional"] is None:
            msg = "This command requires positional text, e.g. !translate You are an idiot to: fr from: en"
            raise errors.RespondWithError(msg)

        return TranslateArgs(
            text=flags["_positional"],
            to=flags["to"] or "en",
            from_=flags["from"] or "auto",
        )
