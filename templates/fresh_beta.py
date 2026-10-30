# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Template for `ext.beta` module.

Just copy-paste it there without this docstring.
Then you can beta-test some random code snippets with ease.
"""

from __future__ import annotations

from base_beta import *


class BetaTest(BetaCog):
    async def beta_test_task_count_1(self) -> None:  # ty: ignore[missing-override-decorator]
        pass

    @commands.command(name="test", aliases=["beta"])
    async def test(self, ctx: Context) -> None:
        await ctx.send("test")

    @commands.Component.listener(name="custom_redemption_add")
    async def test_custom_redemption_add(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        pass


async def setup(bot: Bot) -> None:
    await bot.add_component(BetaTest(bot))
