from __future__ import annotations

from beta_base import *


class BetaTest(BetaCog):
    async def beta_test_task_count_1(self) -> None:  # ty: ignore[missing-override-decorator]
        # query = "SELECT blacklisted_at FROM ttv_stv_blacklist_emotes LIMIT 1"
        # dt = await self.bot.pool.fetchval(query)
        # print(clock.utcnow() - dt)
        pass

    @commands.command(name="test", aliases=["beta"])
    async def test(self, ctx: IreContext, *, flags: str) -> None:
        pass

    @commands.Component.listener(name="custom_redemption_add")
    async def test_custom_redemption_add(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        print(redemption.reward.id)


async def setup(bot: IreBot) -> None:
    await bot.add_component(BetaTest(bot))
