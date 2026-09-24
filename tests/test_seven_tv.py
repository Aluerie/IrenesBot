import pytest
from src.config import env
from src.shared import seven_tv_gql
from src.shared.helpers import MISSING
from src.utils import const

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
async def stv() -> seven_tv_gql.GraphQL7TVClient:
    """7TV client fixture."""
    return seven_tv_gql.GraphQL7TVClient(
        env.SEVEN_TV_BEARER,
        bot_7tv_user_id=const.SevenTV.IRENESBOT_USER_ID,
        pool=MISSING,
    )


@pytest.mark.asyncio
async def test_active_emote_set_by_broadcaster(stv: seven_tv_gql.GraphQL7TVClient) -> None:
    """Whether the client can properly fetch Irene's active emote set."""
    partial_emote_set = await stv.create_partial_user(const.UserID.Irene).fetch_active_emote_set()
    assert partial_emote_set.id == const.SevenTV.IRENE_EMOTE_SET_ID
