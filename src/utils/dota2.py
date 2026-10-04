from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, NamedTuple, override

from config import env
from core import ireloop
from shared.dota2 import Dota2Client

if TYPE_CHECKING:
    from steam.ext import dota2

    from core import IreBot


log = logging.getLogger(__name__)

__all__ = ("IreDota2Client", "SteamUserUpdate")


class SteamUserUpdate(NamedTuple):
    """Payload for my custom `steam_user_update` event to mirror `Dota2Client.on_user_update`."""

    before: dota2.User
    after: dota2.User


class IreDota2Client(Dota2Client):
    """Subclass for SteamIO's Client.

    Used to communicate with Dota 2 Game Coordinator in order to track information about my profile real-time.
    """

    def __init__(self, bot: IreBot) -> None:
        super().__init__(
            session=bot.session,
            pool=bot.pool,
            steam_username=env.STEAM_IRENESTEST_USERNAME if bot.subset_mode else env.STEAM_IRENESBOT_USERNAME,
            steam_password=env.STEAM_IRENESTEST_PASSWORD if bot.subset_mode else env.STEAM_IRENESBOT_PASSWORD,
            steam_web_api=env.STEAM_API_KEY,
            stratz_bearer=env.STRATZ_BEARER,
        )
        self.bot: IreBot = bot

    @override
    async def before_login(self) -> None:
        """Start helping services for steam."""
        self.refresh_database_dota_constants.start()

    @override
    async def close(self) -> None:
        self.refresh_database_dota_constants.stop()

    @override
    async def on_user_update(self, before: dota2.User, after: dota2.User) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Called when a steam user is updated, due to one or more of their attributes changing.

        The information from this event is redirected to `self.bot` events
        so we can process it in the bot components' listeners.
        """
        payload = SteamUserUpdate(before=before, after=after)
        self.bot.dispatch("steam_user_update", payload)
