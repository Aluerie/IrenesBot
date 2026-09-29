"""
Template for `modules.beta` module.

Just copy-paste it there without this docstring.
Then you cna beta-test some random code snippets with ease.

License
-------
* License: MPL-2.0, see LICENSE for more details.
* Copyright: (C) 2020-present @Aluerie.
"""

# ruff: noqa: D101, D102, D103, EM101, RUF100, T201

from __future__ import annotations

from beta_base import *


class BetaTest(BetaCog):
    @override
    async def beta_test_task_count_1(self) -> None:
        pass

    @commands.command(name="test", aliases=["beta"])
    async def test(self, ctx: IreContext) -> None:
        await ctx.send("test")

    @commands.Component.listener(name="custom_redemption_add")
    async def test_custom_redemption_add(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        pass


async def setup(bot: IreBot) -> None:
    await bot.add_component(BetaTest(bot))
