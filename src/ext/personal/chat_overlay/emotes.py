# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Emote sources of the chat overlay: 7TV (kept live by its EventAPI), BTTV and FFZ, plus a 7TV image cache.

7TV images are served through the bot (`STV_IMAGE_PATH`) instead of straight from `cdn.7tv.app`,
because 7TV is blocked or throttled on the streaming PC's network while the VPS reaches it fine.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

import aiohttp
import seven_tv_events
from loguru import logger

from .render import OverlayEmote

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = (
    "STV_IMAGE_PATH",
    "STV_IMAGE_SIZES",
    "ImageCache",
    "StvEmotes",
    "fetch_bttv_emotes",
    "fetch_ffz_emotes",
)

STV_IMAGE_PATH = "/overlay/7tv/{emote_id}/{size}"
STV_IMAGE_SIZES = frozenset({"1x.webp", "2x.webp", "3x.webp", "4x.webp"})
STV_CDN = "https://cdn.7tv.app/emote/{emote_id}/{size}"

TIMEOUT = aiohttp.ClientTimeout(total=20)

# Global BTTV emotes that are drawn over the emote before them; BTTV's API doesn't mark them.
BTTV_ZERO_WIDTH = frozenset({"SoSnowy", "IceCold", "SantaHat", "TopHat", "ReinDeer", "CandyCane", "cvMask", "cvHazmat"})


def stv_emote(emote: seven_tv_events.Emote) -> OverlayEmote:
    """Return the overlay version of a 7TV emote, with its image served by the bot."""
    return OverlayEmote(
        name=emote.name,
        url=STV_IMAGE_PATH.format(emote_id=emote.id, size="2x.webp"),
        zero_width=bool(emote.flags & 1),
    )


async def _get_json(session: aiohttp.ClientSession, url: str) -> Any:
    """GET a JSON document; `None` for a 404 (e.g. a channel without BTTV or FFZ emotes)."""
    async with session.get(url, timeout=TIMEOUT) as resp:
        if resp.status == 404:
            return None
        resp.raise_for_status()
        return await resp.json()


def parse_bttv(emotes: Iterable[dict[str, Any]]) -> dict[str, OverlayEmote]:
    return {
        e["code"]: OverlayEmote(
            name=e["code"],
            url=f"https://cdn.betterttv.net/emote/{e['id']}/2x.webp",
            zero_width=e["code"] in BTTV_ZERO_WIDTH,
        )
        for e in emotes
    }


async def fetch_bttv_emotes(session: aiohttp.ClientSession, twitch_id: str) -> dict[str, OverlayEmote]:
    """Fetch the global BTTV emotes and the channel's own (channel ones win on a name clash)."""
    global_emotes = await _get_json(session, "https://api.betterttv.net/3/cached/emotes/global") or []
    channel = await _get_json(session, f"https://api.betterttv.net/3/cached/users/twitch/{twitch_id}") or {}
    return parse_bttv(global_emotes) | parse_bttv([*channel.get("channelEmotes", ()), *channel.get("sharedEmotes", ())])


def parse_ffz(sets: dict[str, Any], set_ids: Iterable[int | str]) -> dict[str, OverlayEmote]:
    emotes: dict[str, OverlayEmote] = {}
    for set_id in set_ids:
        for e in (sets.get(str(set_id)) or {}).get("emoticons", ()):
            urls = e.get("animated") or e.get("urls") or {}
            if url := urls.get("2") or urls.get("1"):
                emotes[e["name"]] = OverlayEmote(name=e["name"], url=url)
    return emotes


async def fetch_ffz_emotes(session: aiohttp.ClientSession, twitch_id: str) -> dict[str, OverlayEmote]:
    """Fetch the global FFZ emotes and the channel's own (channel ones win on a name clash)."""
    global_data = await _get_json(session, "https://api.frankerfacez.com/v1/set/global") or {}
    room = await _get_json(session, f"https://api.frankerfacez.com/v1/room/id/{twitch_id}") or {}
    global_emotes = parse_ffz(global_data.get("sets", {}), global_data.get("default_sets", ()))
    channel_emotes = parse_ffz(room.get("sets", {}), room.get("sets", {}).keys())
    return global_emotes | channel_emotes


class StvEmotes:
    """The 7TV global emotes and a channel's active emote set, kept up to date by the 7TV EventAPI.

    `load()` fetches everything over the REST API; it runs on every (re)connect, since events may have been
    missed while the connection was down. Events that arrive during a load are applied on top of it afterwards.
    A change of the channel's active emote set (a `user.update` event) moves the subscription to the new set.
    """

    def __init__(self, session: aiohttp.ClientSession, twitch_id: str) -> None:
        self.session: aiohttp.ClientSession = session
        self.twitch_id: str = twitch_id
        self.client: seven_tv_events.Client = seven_tv_events.Client(session=session)

        self.global_emotes: dict[str, OverlayEmote] = {}
        self.channel_emotes: dict[str, seven_tv_events.Emote] = {}  # by emote ID
        self.emote_set_id: str | None = None
        self.user_id: str | None = None
        self.known_ids: set[str] = set()
        """Every 7TV emote ID seen since the bot started: the only images the bot proxies."""

        self._buffer: list[seven_tv_events.Dispatch] | None = None
        self._load_lock: asyncio.Lock = asyncio.Lock()
        self.on_change: list[Any] = []  # callbacks without arguments, called after every change

        self.client.add_event_handler("ready", self._on_connect)
        self.client.add_event_handler("resumed", self._on_connect)
        self.client.add_dispatch_handler(seven_tv_events.SubscriptionType.EMOTE_SET_UPDATE, self._on_emote_set_update)
        self.client.add_dispatch_handler(seven_tv_events.SubscriptionType.USER_UPDATE, self._on_user_update)

    def emotes(self) -> dict[str, OverlayEmote]:
        """Return the emotes by name: the channel's set over the global one."""
        return self.global_emotes | {e.name: stv_emote(e) for e in self.channel_emotes.values()}

    async def run(self) -> None:
        """Load the emotes and keep them updated until `close()`.

        Raises `seven_tv_events.ClosedError` if the EventAPI closes the connection for good.
        """
        await self.client.start(wait=False)
        await self.reload()
        await self.client.wait_closed()

    async def reload(self) -> None:
        """Run `load()` until it succeeds, waiting longer after each failure."""
        delay = 5.0
        while True:
            try:
                await self.load()
            except aiohttp.ClientError, TimeoutError, seven_tv_events.RESTError, seven_tv_events.EventAPIError:
                logger.exception("Chat overlay: failed to load 7TV emotes, retrying in {:.0f} s", delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 300)
            else:
                return

    async def close(self) -> None:
        """Stop listening to 7TV."""
        await self.client.close()

    async def load(self) -> None:
        """(Re)load the global emotes and the channel's active set, and subscribe to their changes."""
        async with self._load_lock:
            self._buffer = []
            try:
                connection = await seven_tv_events.rest.fetch_user_connection(
                    "twitch", self.twitch_id, session=self.session
                )
                global_set = await seven_tv_events.rest.fetch_emote_set("global", session=self.session)
                await self._follow(connection)
                self.global_emotes = {e.name: stv_emote(e) for e in global_set.emotes}
                self.known_ids.update(e.id for e in global_set.emotes)
                emote_set = connection.emote_set
                self.channel_emotes = {e.id: e for e in emote_set.emotes} if emote_set else {}
                self.known_ids.update(self.channel_emotes)
            finally:
                buffered, self._buffer = self._buffer, None
        logger.info("Chat overlay: loaded {} 7TV channel emotes", len(self.channel_emotes))
        for event in buffered:
            self._apply(event)
        self._changed()

    async def _follow(self, connection: seven_tv_events.UserConnection) -> None:
        """Subscribe to the user's and their active emote set's changes, dropping a previous set."""
        if connection.user and connection.user.id != self.user_id:
            if self.user_id is not None:
                await self.client.unsubscribe(seven_tv_events.SubscriptionType.USER_UPDATE, object_id=self.user_id)
            self.user_id = connection.user.id
            await self.client.subscribe(seven_tv_events.SubscriptionType.USER_UPDATE, object_id=self.user_id)
        if connection.emote_set_id != self.emote_set_id:
            if self.emote_set_id is not None:
                logger.info("Chat overlay: active 7TV emote set changed to {}", connection.emote_set_id)
                await self.client.unsubscribe(
                    seven_tv_events.SubscriptionType.EMOTE_SET_UPDATE, object_id=self.emote_set_id
                )
            self.emote_set_id = connection.emote_set_id
            if self.emote_set_id is not None:
                await self.client.subscribe(
                    seven_tv_events.SubscriptionType.EMOTE_SET_UPDATE, object_id=self.emote_set_id
                )

    async def _on_connect(self, _: seven_tv_events.Hello) -> None:
        await self.reload()

    async def _on_user_update(self, _: seven_tv_events.Dispatch) -> None:
        # The interesting change, the channel switching its active emote set, is deep inside the user's
        # connections; reloading is simpler than picking it out, and user updates are rare.
        await self.reload()

    async def _on_emote_set_update(self, event: seven_tv_events.Dispatch) -> None:
        if self._buffer is not None:
            self._buffer.append(event)
            return
        self._apply(event)
        self._changed()

    def _apply(self, event: seven_tv_events.Dispatch) -> None:
        to_ulid = seven_tv_events.legacy_id_to_ulid
        if to_ulid(event.body.id) != to_ulid(self.emote_set_id or ""):
            return  # a late event of the previous set
        for change_type, change in event.body.changes():
            if change.key != "emotes":
                continue
            if change_type in {"pulled", "updated"} and change.old_value:
                self.channel_emotes.pop(change.old_value["id"], None)
            if change_type in {"pushed", "updated"} and change.value:
                emote = seven_tv_events.Emote.from_json(change.value)
                self.channel_emotes[emote.id] = emote
                self.known_ids.add(emote.id)
            logger.info(
                "Chat overlay: 7TV emote {} {}",
                change_type,
                (change.value or change.old_value or {}).get("name"),
            )

    def _changed(self) -> None:
        for callback in self.on_change:
            callback()


class ImageCache:
    """A size-capped in-memory LRU cache of 7TV emote images, filled from the 7TV CDN on demand.

    Concurrent requests for the same image share one download.
    """

    def __init__(self, session: aiohttp.ClientSession, max_bytes: int = 64 * 1024 * 1024) -> None:
        self.session: aiohttp.ClientSession = session
        self.max_bytes: int = max_bytes
        self.size: int = 0
        self._images: OrderedDict[tuple[str, str], bytes] = OrderedDict()
        self._pending: dict[tuple[str, str], asyncio.Task[bytes]] = {}

    async def get(self, emote_id: str, size: str) -> bytes:
        """Return the image, downloading it if it isn't cached. Raises `aiohttp.ClientError` if that fails."""
        key = (emote_id, size)
        if (image := self._images.get(key)) is not None:
            self._images.move_to_end(key)
            return image
        task = self._pending.get(key)
        if task is None:
            task = self._pending[key] = asyncio.create_task(self._download(key))
            task.add_done_callback(lambda _: self._pending.pop(key, None))
        return await asyncio.shield(task)

    async def _download(self, key: tuple[str, str]) -> bytes:
        emote_id, size = key
        async with self.session.get(STV_CDN.format(emote_id=emote_id, size=size), timeout=TIMEOUT) as resp:
            resp.raise_for_status()
            image = await resp.read()
        self._images[key] = image
        self.size += len(image)
        while self.size > self.max_bytes and len(self._images) > 1:
            _, old = self._images.popitem(last=False)
            self.size -= len(old)
        return image
