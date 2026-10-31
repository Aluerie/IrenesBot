# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Tags."""

from __future__ import annotations

from itertools import islice
from typing import TYPE_CHECKING, TypedDict

import asyncpg
from twitchio.ext import commands

from core import PersonalComponent
from shared import errors
from utils import const

if TYPE_CHECKING:
    from collections.abc import Iterator

    from core import Bot, Context

    class TagQueryRow(TypedDict):
        tag_name: str
        tag_content: str


__all__ = ("Tags",)

EMOTE = const.Stv.uuhAcktshucally

# Twitch chat messages can't be longer than 500 characters.
MAX_MESSAGE_LENGTH = 500
# Do not flood the chat with too many messages when listing tags.
MAX_LIST_MESSAGES = 3

# Names of subcommands and their aliases: a tag with such a name could never be fetched by `!tag <name>`.
RESERVED_TAG_NAMES = frozenset({
    "add",
    "a",
    "create",
    "delete",
    "del",
    "remove",
    "d",
    "edit",
    "e",
    "rename",
    "r",
    "names",
    "n",
    "list",
    "l",
    "all",
})


def no_tag_error(tag_name: str) -> errors.RespondWithError:
    """Create an error for a tag that doesn't exist.

    Parameters
    ----------
    tag_name
        Name of the tag that wasn't found.
    """
    return errors.RespondWithError(f"There is no tag with name '{tag_name}' {EMOTE}")


def ensure_tag_name_is_free(tag_name: str) -> None:
    """Make sure the tag name doesn't clash with a subcommand name.

    Parameters
    ----------
    tag_name
        Name to check.

    Raises
    ------
    errors.RespondWithError
        If the name is reserved by one of the subcommands.
    """
    if tag_name in RESERVED_TAG_NAMES:
        msg = f"This tag_name is reserved {EMOTE}"
        raise errors.RespondWithError(msg)


def chunk_parts(parts: list[str], *, separator: str, limit: int) -> Iterator[str]:
    """Join parts with a separator into chunks that fit into a message length limit.

    Parameters
    ----------
    parts
        Pieces of text to join.
    separator
        Text to put between the parts.
    limit
        Maximum length of a single chunk.
    """
    current = ""
    for part in parts:
        part = part[:limit]  # ruff: ignore[redefined-loop-name]
        candidate = f"{current}{separator}{part}" if current else part
        if current and len(candidate) > limit:
            yield current
            current = part
        else:
            current = candidate
    if current:
        yield current


class Tags(PersonalComponent):
    """Commands to fetch something by a tag name."""

    async def send_chunked(self, ctx: Context, parts: list[str], *, separator: str) -> None:
        """Send parts as a few chat messages that respect Twitch limits.

        Parameters
        ----------
        ctx
            Command context.
        parts
            Pieces of text to send.
        separator
            Text to put between the parts in a single message.
        """
        prefix = f"{EMOTE} "
        chunks = chunk_parts(parts, separator=separator, limit=MAX_MESSAGE_LENGTH - len(prefix))
        for chunk in islice(chunks, MAX_LIST_MESSAGES):
            await ctx.send(f"{prefix}{chunk}")

    @commands.group(invoke_fallback=True, name="tag", aliases=["tags", "t"])
    async def tag_group(self, ctx: Context, tag_name: str) -> None:
        """Group command for `!tag`.

        Without a subcommand this fetches a tag.

        Parameters
        ----------
        tag_name
            Name of the tag to fetch.
        """
        tag_name = tag_name.lower()
        query = """
            SELECT tag_content FROM tags
            WHERE tag_name = $1;
        """
        tag_content: str | None = await self.bot.pool.fetchval(query, tag_name)
        if tag_content is None:
            raise no_tag_error(tag_name)
        await ctx.send(tag_content)

    @commands.is_moderator()
    @tag_group.command(name="add", aliases=["a", "create"])
    async def tag_add(self, ctx: Context, tag_name: str, *, tag_content: str) -> None:
        """Add a new tag.

        Parameters
        ----------
        tag_name
            Name for the new tag, should be one word (no spaces).
        tag_content
            Content for the new tag.

        Examples
        --------
        * ``!tag add info Some cool info`` - will add a tag under ``<tag_name>`` "info" with
          ``<tag_content>`` being "Some cool info".
        """
        tag_name = tag_name.lower()
        ensure_tag_name_is_free(tag_name)

        query = """
            INSERT INTO tags
            (tag_name, tag_content)
            VALUES ($1, $2);
        """
        try:
            await self.bot.pool.execute(query, tag_name, tag_content)
        except asyncpg.UniqueViolationError:
            msg = f"There already exists a tag with name '{tag_name}' {EMOTE}"
            raise errors.RespondWithError(msg) from None
        else:
            await ctx.send(f"Created tag '{tag_name}' {EMOTE}")

    @commands.is_moderator()
    @tag_group.command(name="delete", aliases=["del", "remove", "d"])
    async def tag_delete(self, ctx: Context, tag_name: str) -> None:
        """Delete tag by name.

        Parameters
        ----------
        tag_name
            Name of the tag to delete.
        """
        tag_name = tag_name.lower()
        query = """
            DELETE FROM tags
            WHERE tag_name = $1
            RETURNING tag_name;
        """
        val: str | None = await self.bot.pool.fetchval(query, tag_name)
        if val is None:
            raise no_tag_error(tag_name)
        await ctx.send(f"Deleted tag '{tag_name}' {EMOTE}")

    @commands.is_moderator()
    @tag_group.command(name="edit", aliases=["e"])
    async def tag_edit(self, ctx: Context, tag_name: str, *, tag_content: str) -> None:
        """Edit tag content.

        Parameters
        ----------
        tag_name
            Name of the tag to edit.
        tag_content
            New content for the tag.
        """
        tag_name = tag_name.lower()
        query = """
            UPDATE tags
            SET tag_content = $2
            WHERE tag_name = $1
            RETURNING tag_name;
        """
        val: str | None = await self.bot.pool.fetchval(query, tag_name, tag_content)
        if val is None:
            raise no_tag_error(tag_name)
        await ctx.send(f"Edited tag '{tag_name}' {EMOTE}")

    @commands.is_moderator()
    @tag_group.command(name="rename", aliases=["r"])
    async def tag_rename(self, ctx: Context, tag_name: str, new_tag_name: str) -> None:
        """Rename tag.

        Parameters
        ----------
        tag_name
            Current name of the tag.
        new_tag_name
            New name for the tag, should be one word (no spaces).
        """
        tag_name = tag_name.lower()
        new_tag_name = new_tag_name.lower()
        ensure_tag_name_is_free(new_tag_name)

        query = """
            UPDATE tags
            SET tag_name = $2
            WHERE tag_name = $1
            RETURNING tag_name;
        """
        try:
            val: str | None = await self.bot.pool.fetchval(query, tag_name, new_tag_name)
        except asyncpg.UniqueViolationError:
            msg = f"There already exists a tag with name '{new_tag_name}' {EMOTE}"
            raise errors.RespondWithError(msg) from None

        if val is None:
            raise no_tag_error(tag_name)
        await ctx.send(f"Renamed tag '{tag_name}' into '{new_tag_name}' {EMOTE}")

    @tag_group.command(name="names", aliases=["n"])
    async def tag_names(self, ctx: Context) -> None:
        """Tag names list."""
        query = """
            SELECT tag_name FROM tags
            ORDER BY tag_name;
        """
        rows: list[TagQueryRow] = await self.bot.pool.fetch(query)
        if not rows:
            await ctx.send(f"No tags were created yet {EMOTE}")
            return
        await self.send_chunked(ctx, [row["tag_name"] for row in rows], separator=", ")

    @tag_group.command(name="list", aliases=["l", "all"])
    async def tag_list(self, ctx: Context) -> None:
        """Tag list with contents."""
        query = """
            SELECT tag_name, tag_content FROM tags
            ORDER BY tag_name;
        """
        rows: list[TagQueryRow] = await self.bot.pool.fetch(query)
        if not rows:
            await ctx.send(f"No tags were created yet {EMOTE}")
            return
        await self.send_chunked(ctx, [f"{row['tag_name']}: {row['tag_content']}" for row in rows], separator=" | ")


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(Tags(bot))
