"""Converters.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import re
from typing import TYPE_CHECKING, NamedTuple, override

from twitchio.ext import commands

from shared import errors

if TYPE_CHECKING:
    from core import IreContext

__all__ = (
    "TranslateArguments",
    "TranslateConverter",
)


def flag_parser(
    user_input: str,
    flags: list[str],
    *,
    positional: bool = True,
    prefix: str = "--",
    delimiter: str = " ",
) -> dict[str, str | None]:
    """Flag-parser: a converter that allows for a user-friendly flag syntax.

    TwitchIO doesn't have its own version of ``commands.FlagConverter`` like ``discord.py`` does so this is a temporary
    replacement until they implement it or I PR it.

    Source
    ------
    * Discord.py -> ``discord.ext.commands.flags.FlagConverter.parse_flags()`` (MIT License)

    Parameters
    ----------
    user_input
        User Input.
    flags
        The list of flags. User will be able to use them in their user input, e.g. "!translate Je t'aime to: en from: fr"
        has two flags: ``to`` and ``from``
    positional
        Whether the user input includes positional argument in the beginning of the string.
    prefix
        Flag prefix.
    delimiter
        Flag delimiter. Together with prefix it can customize the flag "look", e.g. ``delimiter=' ', prefix='--'``
        for POSIX-like flags: "--hello world".
    """
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
                msg = f"The flag `{last_flag}:` is missing its value"
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
            msg = f"The flag `{last_flag}:` is missing its value"
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


class TranslateArguments(NamedTuple):
    """The output of TranslateConverter."""

    text: str
    to: str = "en"
    from_: str = "auto"


class TranslateConverter(commands.Converter[TranslateArguments]):
    """Translate Converter."""

    @override
    async def convert(self, _: IreContext, user_input: str) -> TranslateArguments:  # ty: ignore[invalid-method-override]
        """Convert `user_input` to 7TV emote_id."""
        flags = flag_parser(user_input, flags=["to", "from"])
        if "_positional" not in flags or flags["_positional"] is None:
            msg = "This command requires positional text, e.g. !translate Je vous aime to: de from: fr"
            raise errors.RespondWithError(msg)

        return TranslateArguments(
            text=flags["_positional"],
            to=flags["to"] or "en",
            from_=flags["from"] or "auto",
        )
