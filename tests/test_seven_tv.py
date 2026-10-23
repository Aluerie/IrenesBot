"""Test 7TV features.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import pytest
from src.shared.apis import stv
from src.utils import const

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
async def stv_client() -> stv.StvClient:  # ruff: ignore[unused-async]
    """7TV client fixture."""
    return stv.StvClient(bot_7tv_user_id=const.StvID.BOT)


@pytest.mark.asyncio
async def test_active_emote_set_by_broadcaster(stv_client: stv.StvClient) -> None:
    """Whether the client can properly fetch Irene's active emote set."""
    partial_emote_set = await stv_client.create_partial_user(const.UserID.Irene).fetch_active_emote_set()
    assert partial_emote_set.id == const.StvID.IRENE_EMOTE_SET
