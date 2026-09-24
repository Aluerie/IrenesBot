from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, TypedDict, override

from twitchio.ext import commands

from core import IreDevComponent, Streamer, ireloop

if TYPE_CHECKING:
    import twitchio

    from core import IreBot

    class StreamersUserQueryRow(TypedDict):
        user_id: str
        display_name: str


__all__ = ("StreamerIndexManagement",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class StreamerIndexManagement(IreDevComponent):
    """Component managing `self.bot.streamers` index.

    This index is used to cache some information about streamers
    that twitchio does not cache for me by itself, such as their `online` state
    (twitchio only allows fetching their state at the exact moment).

    This class is an attempt to reduce amount of `.fetch_streams` API calls across the bot.
    """

    def __init__(self, bot: IreBot) -> None:
        super().__init__(bot)

    @override
    async def component_load(self) -> None:
        self.fill_streamers_index.start()

    @override
    async def component_teardown(self) -> None:
        self.fill_streamers_index.cancel()

    @ireloop(count=1)
    async def fill_streamers_index(self) -> None:
        """Fill `bot.streamers` index on bot's startup."""
        log.debug("Filling `self.bot.streamers` index")
        query = "SELECT user_id FROM ttv_tokens WHERE user_type != 'bot';"
        user_ids = [r for (r,) in await self.bot.pool.fetch(query)]
        self.bot.streamers = {id_: Streamer(id_) for id_ in user_ids}

        if not user_ids:
            # `fetch_stream` in this case fetches top global streams which we don't want;
            # And nobody online, I guess;
            pass
        else:
            streams = await self.bot.fetch_streams(user_ids=user_ids)
            for stream in streams:
                streamer = self.bot.streamers[stream.user.id]
                streamer.online = True
                streamer.started_dt = stream.started_at

        log.debug("Finished initial filling of `self.bot.streamers` index")
        self.bot.streamers_index_ready.set()

    @commands.Component.listener(name="stream_online")
    async def add_stream_to_online_cache(self, online: twitchio.StreamOnline) -> None:
        """Set streamer's state to online in the index."""
        streamer = self.bot.streamers[online.broadcaster.id]
        streamer.online = True
        streamer.started_dt = online.started_at

    @commands.Component.listener(name="stream_offline")
    async def remove_stream_from_online_cache(self, offline: twitchio.StreamOffline) -> None:
        """Set streamer's state to offline in the index."""
        streamer = self.bot.streamers[offline.broadcaster.id]
        streamer.online = False
        streamer.started_dt = None

    @ireloop(time=datetime.time(hour=6, minute=34, second=10))
    async def check_twitch_accounts_renames(self) -> None:
        """Checks if people in FPC database renamed themselves on twitch.tv.

        I think we're using twitch ids everywhere so this timer is more for convenience matter
        when I'm browsing the database, but still.
        """
        if datetime.datetime.now(datetime.UTC).day != 31:
            return

        query = "SELECT user_id, display_name FROM ttv_tokens;"
        rows: list[StreamersUserQueryRow] = await self.bot.pool.fetch(query)
        database_streamers = {row["user_id"]: row["display_name"] for row in rows}

        twitch_users = await self.bot.fetch_users(ids=list(database_streamers.keys()))
        for user in twitch_users:
            if user.display_name.lower() != database_streamers[user.id]:
                query = "UPDATE ttv_tokens SET display_name = $1 WHERE user_id = $2"
                await self.bot.pool.execute(query, user.display_name, user.id)


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(StreamerIndexManagement(bot))
