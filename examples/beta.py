# ruff: noqa: D101, D102, D103

from __future__ import annotations

from src.beta_base import *


class BetaTest(BetaCog):
    @override
    async def beta_test_task_count_1(self) -> None:
        pass

    @commands.command(name="test", aliases=["beta"])
    async def test(self, ctx: IreContext) -> None:
        await ctx.send("test")


async def setup(bot: IreBot) -> None:
    await bot.add_component(BetaTest(bot))
