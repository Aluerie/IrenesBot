# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Chat overlay: Irene's Twitch chat with badges and 7TV, BTTV and FFZ emotes, as an OBS browser source.

The bot serves the overlay page and pushes ready-to-draw messages to it over a WebSocket. It also proxies
7TV emote images, because 7TV is blocked or throttled on the streaming PC's network.

Routes (on the bot's web adapter, so only when it runs with the remote adapter):
* `/overlay/chat?key=<OVERLAY_KEY>&fade=15` - the page to add to OBS as a browser source;
* `/overlay/chat/ws?key=<OVERLAY_KEY>` - the page's WebSocket;
* `/overlay/7tv/<emote id>/<size>` - 7TV emote images, cached in memory.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

import aiohttp
import seven_tv_events
import twitchio
from loguru import logger
from starlette.responses import HTMLResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect
from twitchio.ext import commands
from twitchio.web import StarletteAdapter

from config import env
from core import PersonalComponent
from shared import clock
from utils import const

from .emotes import STV_IMAGE_PATH, STV_IMAGE_SIZES, ImageCache, StvEmotes, fetch_bttv_emotes, fetch_ffz_emotes
from .render import Fragment, OverlayEmote, default_colour, is_emote_only, readable_colour, render_parts

if TYPE_CHECKING:
    from starlette.requests import Request

    from core import Bot

PAGE_PATH = "/overlay/chat"
WEBSOCKET_PATH = "/overlay/chat/ws"
HISTORY_SIZE = 50
SEND_TIMEOUT = 5.0
BTTV_FFZ_REFRESH_INTERVAL = 30 * 60  # seconds; BTTV and FFZ have no live updates

_page_template = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")
PAGE_VERSION = hashlib.sha256(_page_template.encode()).hexdigest()[:12]
PAGE = _page_template.replace("__OVERLAY_VERSION__", PAGE_VERSION)


class ChatOverlay(PersonalComponent):
    """Stream chat overlay for Irene's channel."""

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.broadcaster_id: str = const.UserID.Irene
        self.stv: StvEmotes = StvEmotes(bot.session, self.broadcaster_id)
        self.stv.on_change.append(self.rebuild_emotes)
        self.images: ImageCache = ImageCache(bot.session)

        self.third_party: dict[str, OverlayEmote] = {}  # BTTV and FFZ
        self.emotes: dict[str, OverlayEmote] = {}
        self.badges: dict[tuple[str, str], dict[str, str]] = {}  # (set id, version id) -> badge
        self.clients: set[WebSocket] = set()
        self.history: deque[dict[str, Any]] = deque(maxlen=HISTORY_SIZE)

        self._routes: list[Route | WebSocketRoute] = []
        self._tasks: set[asyncio.Task[None]] = set()

    # LIFECYCLE

    @override
    async def component_load(self) -> None:
        """Add the web routes and start loading emotes and badges."""
        adapter = self.bot.adapter
        if not isinstance(adapter, StarletteAdapter):
            logger.warning("Chat overlay: the bot runs without the remote (Starlette) adapter, so no overlay routes")
            return
        self._routes = [
            Route(PAGE_PATH, self.page, methods=["GET"]),
            WebSocketRoute(WEBSOCKET_PATH, self.websocket),
            Route(STV_IMAGE_PATH.format(emote_id="{emote_id}", size="{size}"), self.stv_image, methods=["GET"]),
        ]
        adapter.router.routes.extend(self._routes)
        self._spawn(self.run_stv())
        self._spawn(self.refresh_bttv_ffz())
        self._spawn(self.load_badges())

    @override
    async def component_teardown(self) -> None:
        """Remove the routes, disconnect the pages and stop the background tasks."""
        adapter = self.bot.adapter
        if isinstance(adapter, StarletteAdapter):
            for route in self._routes:
                with contextlib.suppress(ValueError):
                    adapter.router.routes.remove(route)
        await self.stv.close()
        for task in self._tasks:
            task.cancel()
        for ws in list(self.clients):
            with contextlib.suppress(Exception):
                await ws.close(code=1012)  # service restart: the pages reconnect
        self.clients.clear()

    def _spawn(self, coro: Any) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    # EMOTES AND BADGES

    def rebuild_emotes(self) -> None:
        """Merge all emote sources; 7TV wins name clashes, as it does in most chat clients."""
        self.emotes = self.third_party | self.stv.emotes()

    async def run_stv(self) -> None:
        """Keep the 7TV emotes up to date for as long as the component is loaded."""
        try:
            await self.stv.run()
        except seven_tv_events.ClosedError:
            logger.exception("Chat overlay: the 7TV EventAPI closed the connection for good")
            await self.bot.notify_developers("Chat overlay: 7TV EventAPI closed for good; 7TV emotes stopped updating.")

    async def refresh_bttv_ffz(self) -> None:
        """Load BTTV and FFZ emotes, and reload them every now and then since they have no live updates."""
        while True:
            emotes: dict[str, OverlayEmote] = {}
            for fetch in (fetch_ffz_emotes, fetch_bttv_emotes):  # BTTV wins name clashes with FFZ
                try:
                    emotes |= await fetch(self.bot.session, self.broadcaster_id)
                except aiohttp.ClientError, TimeoutError, ValueError:
                    logger.exception("Chat overlay: failed to load emotes with {}", fetch.__name__)
            if emotes:
                self.third_party = emotes
                self.rebuild_emotes()
            await asyncio.sleep(BTTV_FFZ_REFRESH_INTERVAL)

    async def load_badges(self) -> None:
        """Load the global and the channel's Twitch chat badges (the channel's override the global ones)."""
        try:
            global_badges = await self.bot.fetch_badges()
            channel_badges = await self.bot.create_partialuser(self.broadcaster_id).fetch_badges()
        except twitchio.HTTPException:
            logger.exception("Chat overlay: failed to load chat badges; messages show without them")
            return
        for badge in (*global_badges, *channel_badges):
            for version in badge.versions:
                self.badges[badge.set_id, version.id] = {"name": version.title, "url": version.image_url_2x}

    # WEB ROUTES

    @staticmethod
    def key_matches(key: str | None) -> bool:
        """Whether the key from a request is `OVERLAY_KEY`; always false while it is not set."""
        return bool(env.OVERLAY_KEY) and hmac.compare_digest((key or "").encode(), env.OVERLAY_KEY.encode())

    async def page(self, request: Request) -> Response:
        """Serve the overlay page."""
        if not self.key_matches(request.query_params.get("key")):
            return Response("Wrong or missing key.", status_code=403)
        return HTMLResponse(PAGE, headers={"Cache-Control": "no-store"})

    async def websocket(self, ws: WebSocket) -> None:
        """Send the recent messages to a newly connected page, then push new ones until it disconnects."""
        if not self.key_matches(ws.query_params.get("key")):
            await ws.close(code=1008)
            return
        await ws.accept()
        await ws.send_json({"type": "hello", "version": PAGE_VERSION, "history": list(self.history)})
        self.clients.add(ws)
        try:
            while True:
                await ws.receive_text()  # the page never sends anything; this just waits for it to go away
        except WebSocketDisconnect:
            pass
        finally:
            self.clients.discard(ws)

    async def stv_image(self, request: Request) -> Response:
        """Serve a 7TV emote image, downloaded by the bot, since the streaming PC can't reach 7TV itself."""
        emote_id, size = request.path_params["emote_id"], request.path_params["size"]
        if size not in STV_IMAGE_SIZES or emote_id not in self.stv.known_ids:
            return Response(status_code=404)
        try:
            image = await self.images.get(emote_id, size)
        except (aiohttp.ClientError, TimeoutError) as exc:
            logger.warning("Chat overlay: failed to get 7TV image {}/{}: {!r}", emote_id, size, exc)
            return Response(status_code=502)
        return Response(image, media_type="image/webp", headers={"Cache-Control": "public, max-age=604800"})

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send an event to every connected page, dropping the ones that don't take it."""

        async def send(ws: WebSocket) -> None:
            try:
                await asyncio.wait_for(ws.send_json(data), SEND_TIMEOUT)
            except Exception:  # ruff: ignore[blind-except] # a page that went away in any way
                self.clients.discard(ws)

        await asyncio.gather(*(send(ws) for ws in list(self.clients)))

    # TWITCH EVENTS

    def build_message(self, message: twitchio.ChatMessage) -> dict[str, Any]:
        """Turn a chat message into what the overlay page draws."""
        fragments = [Fragment(f.type, f.text, f.emote.id if f.emote else None) for f in message.fragments]
        parts, action = render_parts(fragments, self.emotes)
        chatter = message.chatter
        colour = message.colour.html if message.colour else default_colour(chatter.name or "")
        return {
            "id": message.id,
            "user_id": chatter.id,
            "name": chatter.display_name,
            "colour": readable_colour(colour),
            "badges": [b for badge in message.badges if (b := self.badges.get((badge.set_id, badge.id))) is not None],
            "parts": parts,
            "action": action,
            "big": is_emote_only(parts),
            "ts": int((message.timestamp or clock.utcnow()).timestamp() * 1000),
        }

    @commands.Component.listener(name="message")
    async def overlay_message(self, message: twitchio.ChatMessage) -> None:
        """Show a chat message on the overlay."""
        if message.broadcaster.id != self.broadcaster_id or message.source_broadcaster is not None:
            return  # other channels, and messages shared from other channels' chats in a shared chat session
        data = self.build_message(message)
        self.history.append(data)
        await self.broadcast({"type": "message", "message": data})

    @commands.Component.listener(name="message_delete")
    async def overlay_message_delete(self, payload: twitchio.ChatMessageDelete) -> None:
        """Remove a message a moderator deleted."""
        if payload.broadcaster.id != self.broadcaster_id:
            return
        self._forget(lambda m: m["id"] == payload.message_id)
        await self.broadcast({"type": "delete", "id": payload.message_id})

    @commands.Component.listener(name="chat_clear_user")
    async def overlay_chat_clear_user(self, payload: twitchio.ChannelChatClearUserMessages) -> None:
        """Remove the messages of a banned or timed-out chatter."""
        if payload.broadcaster.id != self.broadcaster_id:
            return
        self._forget(lambda m: m["user_id"] == payload.user.id)
        await self.broadcast({"type": "clear_user", "user_id": payload.user.id})

    @commands.Component.listener(name="chat_clear")
    async def overlay_chat_clear(self, payload: twitchio.ChannelChatClear) -> None:
        """Remove every message after a `/clear`."""
        if payload.broadcaster.id != self.broadcaster_id:
            return
        self.history.clear()
        await self.broadcast({"type": "clear"})

    def _forget(self, predicate: Any) -> None:
        self.history = deque((m for m in self.history if not predicate(m)), maxlen=HISTORY_SIZE)


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(ChatOverlay(bot))
