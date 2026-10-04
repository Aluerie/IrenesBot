"""Tags.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

import asyncpg
from twitchio.ext import commands

from core import IrePersonalComponent
from shared import errors
from utils import const

if TYPE_CHECKING:
    from core import IreBot, IreContext

    class TagQueryRow(TypedDict):
        tag_name: str
        tag_content: str


__all__ = ("Tags",)

NO_TAG_MESSAGE_FMT = "There is no tag with name '{tag_name}' {emote}".format(
    # Trickery: https://stackoverflow.com/a/69462670/19217368
    tag_name="{tag_name}",
    emote=const.STV.uuhAcktshucally,
)


class Tags(IrePersonalComponent):
    """Commands to fetch something by a tag name."""

    @commands.group(invoke_fallback=True, name="tag", aliases=["tags", "t"])
    async def tag_group(self, ctx: IreContext, tag_name: str) -> None:
        """Group command for `!tag`.

        Without a subcommand this fetches a tag.
        """
        query = """
            SELECT tag_content FROM ttv_tags
            WHERE tag_name = $1;
        """
        tag_content: str | None = await self.bot.pool.fetchval(query, tag_name)
        await ctx.send(NO_TAG_MESSAGE_FMT.format(tag_name=tag_name) if tag_content is None else tag_content)

    @commands.is_moderator()
    @tag_group.command(name="add", aliases=["a", "create"])
    async def tag_add(self, ctx: IreContext, tag_name: str, *, tag_content: str) -> None:
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
        if tag_name in ("delete", "remove", "del", "add", "list", "edit", "a", "d", "r", "e", "l"):
            msg = f"This tag_name is reserved {const.STV.uuhAcktshucally}"
            raise errors.RespondWithError(msg)
        try:
            query = """
                INSERT INTO ttv_tags
                (tag_name, tag_content)
                VALUES ($1, $2);
            """
            await self.bot.pool.execute(query, tag_name, tag_content)
            await ctx.send(f"Created tag '{tag_name}' {const.STV.uuhAcktshucally}")
        except asyncpg.UniqueViolationError:
            msg = f"There already exists a tag with name '{tag_name}' {const.STV.uuhAcktshucally}"
            raise errors.RespondWithError(msg) from None

    @commands.is_moderator()
    @tag_group.command(name="delete", aliases=["del", "remove", "d"])
    async def tag_delete(self, ctx: IreContext, tag_name: str) -> None:
        """Delete tag by name."""
        query = """
            DELETE FROM ttv_tags
            WHERE tag_name=$1
            RETURNING tag_name;
        """
        val: str | None = await self.bot.pool.fetchval(query, tag_name)
        await ctx.send(
            NO_TAG_MESSAGE_FMT.format(tag_name=tag_name)
            if val is None
            else f"Deleted tag '{tag_name}' {const.STV.uuhAcktshucally}"
        )

    @commands.is_moderator()
    @tag_group.command(name="edit", aliases=["e"])
    async def tag_edit(self, ctx: IreContext, tag_name: str, *, tag_content: str) -> None:
        """Edit tag."""
        query = """
            UPDATE ttv_tags
            SET tag_content=$2
            WHERE tag_name=$1
            RETURNING tag_name;
        """
        val: str | None = await self.bot.pool.fetchval(query, tag_name, tag_content)
        await ctx.send(
            NO_TAG_MESSAGE_FMT.format(tag_name=tag_name)
            if val is None
            else f"Edited tag '{tag_name}' {const.STV.uuhAcktshucally}"
        )

    @commands.is_moderator()
    @tag_group.command(name="rename", aliases=["r"])
    async def tag_rename(self, ctx: IreContext, tag_name: str, new_tag_name: str) -> None:
        """Rename tag."""
        query = """
            UPDATE ttv_tags
            SET tag_name=$2
            WHERE tag_name=$1
            RETURNING tag_name;
        """
        val: str | None = await self.bot.pool.fetchval(query, tag_name, new_tag_name)
        await ctx.send(
            NO_TAG_MESSAGE_FMT.format(tag_name=tag_name)
            if val is None
            else f"Renamed tag '{tag_name}' into '{new_tag_name}' {const.STV.uuhAcktshucally}"
        )

    @tag_group.command(name="names", aliases=["n"])
    async def tag_names(self, ctx: IreContext) -> None:
        """Tag names list."""
        query = """
            SELECT tag_name FROM ttv_tags;
        """
        tag_names: list[str] = [r for (r,) in await self.bot.pool.fetch(query)]
        await ctx.send(
            f"{const.STV.uuhAcktshucally} {', '.join(tag_names)}"
            if tag_names
            else f"No tags were created yet {const.STV.uuhAcktshucally}"
        )

    @tag_group.command(name="list", aliases=["l", "all"])
    async def tag_list(self, ctx: IreContext) -> None:
        """Tag list."""
        query = """
            SELECT tag_name, tag_content FROM ttv_tags;
        """
        tag_rows: list[TagQueryRow] = await self.bot.pool.fetch(query)
        if not tag_rows:
            await ctx.send(f"No tags were created yet {const.STV.uuhAcktshucally}")
        for tag_row in tag_rows:
            await ctx.send(f"{const.STV.uuhAcktshucally} {tag_row['tag_name']}: {tag_row['tag_content']}")


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(Tags(bot))
