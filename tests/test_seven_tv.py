import pytest
from src.config import env
from src.shared import seven_tv_api
from src.utils import const

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
async def stv() -> seven_tv_api.SevenTVClient:
    """7TV client fixture."""
    return seven_tv_api.SevenTVClient(env.SEVEN_TV_BEARER)


@pytest.mark.asyncio
async def test_active_emote_set_by_broadcaster(stv: seven_tv_api.SevenTVClient) -> None:
    """Whether the client can properly fetch Irene's active emote set."""
    partial_emote_set = await stv.create_partial_user(const.UserID.Irene).fetch_active_emote_set()
    assert partial_emote_set.id == const.STV_IRENE_DEFAULT_EMOTE_SET_ID
