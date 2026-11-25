# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""7TV Bearer token storage, automatic renewal and the web page to replace it manually.

7TV sessions hard-expire 30 days after login and there is no refresh endpoint, so a new session has to be
created by logging in again. The bot can do that itself through the 7TV v3 login flow, as long as it has
the bot account's twitch.tv `persistent` session cookie: Twitch then approves 7TV's OAuth request without
any interaction. If that fails, a new token can be submitted manually via a small password-protected web page
served by the bot's Starlette adapter. Either way the token is stored in the database and used immediately,
without editing `.env` or restarting the bot.
"""

from __future__ import annotations

import asyncio
import hmac
import html
from http.cookies import Morsel
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

import aiohttp
from loguru import logger
from starlette.responses import HTMLResponse
from yarl import URL

from config import env
from shared import clock, globs
from shared.apis.stv import parse_token_claims

if TYPE_CHECKING:
    from starlette.requests import Request
    from twitchio.web import StarletteAdapter

    from .bot import Bot

__all__ = (
    "STV_TOKEN_PAGE_PATH",
    "StvLoginError",
    "load_stv_token",
    "login_via_twitch_cookie",
    "register_stv_token_page",
    "renew_stv_token",
    "save_stv_token",
)


STV_TOKEN_PAGE_PATH = "/stv-token"  # ruff: ignore[hardcoded-password-string], it is a URL path
MAX_FAILED_ATTEMPTS = 10

STV_V3_LOGIN_URL = "https://api.7tv.app/v3/auth?platform=twitch"
LOGIN_TIMEOUT = 30
MAX_LOGIN_REDIRECTS = 8


class StvLoginError(Exception):
    """Automatic 7TV login through Twitch failed."""


BOT_VARIABLES_KEY = "stv_token"


async def load_stv_token(bot: Bot) -> None:
    """Load the 7TV token from the database if it outlives the one from `.env`.

    `.env` only serves as the initial value, so a fresh token in `.env` still wins over a stale one in the database.
    """
    query = "SELECT value FROM bot_variables WHERE key = $1;"
    db_token: str | None = await bot.pool.fetchval(query, BOT_VARIABLES_KEY)
    if db_token is None:
        return

    try:
        db_expires_at = parse_token_claims(db_token).expires_at
    except ValueError:
        logger.warning("7TV token stored in the database is not a readable JWT; ignoring it.")
        return

    env_expires_at = bot.stv.token_expires_at
    if env_expires_at is None or db_expires_at > env_expires_at:
        bot.stv.set_bearer_token(db_token)
        logger.info("Loaded 7TV token from the database, it expires at {}.", db_expires_at)


async def save_stv_token(bot: Bot, token: str) -> str:
    """Validate a new 7TV token, store it in the database and start using it.

    Returns
    -------
    str
        Human-readable confirmation.

    Raises
    ------
    ValueError
        The token is malformed, belongs to another 7TV account or is already expired.
    """
    token = token.removeprefix("Bearer ").strip().strip('"')
    claims = parse_token_claims(token)
    if claims.user_id != bot.stv.user_id:
        msg = f"This token belongs to 7TV user {claims.user_id}, not to the bot ({bot.stv.user_id})."
        raise ValueError(msg)
    if claims.expires_at <= clock.utcnow():
        msg = f"This token has already expired at {claims.expires_at:%Y-%m-%d %H:%M} UTC."
        raise ValueError(msg)

    query = """
        INSERT INTO bot_variables (key, value, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at;
    """
    await bot.pool.execute(query, BOT_VARIABLES_KEY, token)
    bot.stv.set_bearer_token(token)

    result = f"New 7TV token saved, it expires at {claims.expires_at:%Y-%m-%d %H:%M} UTC."
    logger.info(result)
    return result


async def login_via_twitch_cookie(persistent_cookie: str) -> str:
    """Create a new 7TV session through the 7TV v3 login flow and return its token.

    The flow is: 7TV v3 login -> Twitch OAuth authorize -> 7TV v3 callback -> redirect with the token in the URL
    fragment. Twitch only approves the request without user interaction when it recognises a logged-in browser
    session, which is what the bot account's twitch.tv `persistent` cookie provides.

    Raises
    ------
    StvLoginError
        Twitch didn't accept the cookie (it sends us to its login page instead), the flow changed or timed out.
    """
    jar = aiohttp.CookieJar()
    morsel: Morsel[str] = Morsel()
    morsel.set("persistent", persistent_cookie, persistent_cookie)
    morsel["domain"] = ".twitch.tv"
    morsel["path"] = "/"
    jar.update_cookies({"persistent": morsel}, URL("https://www.twitch.tv/"))

    url = URL(STV_V3_LOGIN_URL)
    try:
        async with (
            asyncio.timeout(LOGIN_TIMEOUT),
            # A browser User-Agent, so Twitch treats the request like the logged-in browser the cookie came from.
            aiohttp.ClientSession(cookie_jar=jar, headers={"User-Agent": globs.BROWSER_USER_AGENT}) as session,
        ):
            for _ in range(MAX_LOGIN_REDIRECTS):
                async with session.get(url, allow_redirects=False) as response:
                    location = response.headers.get("Location")
                    if location is None:
                        msg = f"Login flow stopped at {url.host}{url.path} with status {response.status}."
                        raise StvLoginError(msg)
                url = url.join(URL(location))
                if url.host == "www.twitch.tv" and url.path.startswith("/login"):
                    msg = "Twitch didn't accept the `persistent` cookie (redirected to its login page)."
                    raise StvLoginError(msg)
                tokens = parse_qs(urlsplit(str(url)).fragment).get("token")
                if tokens is not None:
                    return tokens[0]
    except (TimeoutError, aiohttp.ClientError) as exc:
        msg = f"Network problem during the login flow: {exc!r}"
        raise StvLoginError(msg) from exc

    msg = "Too many redirects in the login flow."
    raise StvLoginError(msg)


async def renew_stv_token(bot: Bot) -> str:
    """Log into 7TV as the bot automatically, then store and start using the new token.

    Returns
    -------
    str
        Human-readable confirmation.

    Raises
    ------
    StvLoginError
        Automatic login is not configured or failed.
    """
    if not env.TWITCH_BOT_PERSISTENT_COOKIE:
        msg = "Automatic 7TV login is off: `TWITCH_BOT_PERSISTENT_COOKIE` is not set in `.env`."
        raise StvLoginError(msg)
    token = await login_via_twitch_cookie(env.TWITCH_BOT_PERSISTENT_COOKIE)
    return await save_stv_token(bot, token)


def _page(message: str = "", *, ok: bool = True) -> HTMLResponse:
    """Render the token submission form, optionally with a status message above it."""
    colour = "#2e7d32" if ok else "#c62828"
    notice = f'<p style="color:{colour}">{html.escape(message)}</p>' if message else ""
    body = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>7TV token</title></head>
<body style="font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem">
<h1>Update bot's 7TV token</h1>
{notice}
<ol>
  <li>Log into <a href="https://7tv.app" target="_blank" rel="noreferrer">7tv.app</a>
      with the bot's Twitch account.</li>
  <li>Open dev tools &rarr; Application &rarr; Local Storage &rarr; https://7tv.app and copy the token
      (or copy it from the <code>Authorization: Bearer ...</code> header of any request to <code>/v4/gql</code>).</li>
  <li>Paste it below. Don't log out of 7tv.app afterwards: logging out kills the session for the bot too.</li>
</ol>
<form method="post" autocomplete="off">
  <p><label>Page key<br><input type="password" name="key" required style="width:100%"></label></p>
  <p><label>7TV token<br><textarea name="token" rows="6" required style="width:100%"></textarea></label></p>
  <p><button type="submit">Save</button></p>
</form>
</body></html>"""
    return HTMLResponse(body, status_code=200 if ok else 400, headers={"Cache-Control": "no-store"})


def register_stv_token_page(adapter: StarletteAdapter[Bot], bot: Bot) -> None:
    """Add the 7TV token submission page to the bot's web adapter.

    The page is protected by `STV_TOKEN_PAGE_KEY` from `.env`;
    after too many wrong keys it locks itself until the bot restarts.
    """
    failed_attempts = 0

    async def stv_token_page(request: Request) -> HTMLResponse:
        nonlocal failed_attempts
        if failed_attempts >= MAX_FAILED_ATTEMPTS:
            return HTMLResponse("Locked after too many wrong keys. Restart the bot to unlock.", status_code=403)

        if request.method == "GET":
            return _page()

        form = parse_qs((await request.body()).decode(errors="replace"))
        key = form.get("key", [""])[0]
        token = form.get("token", [""])[0]

        if not hmac.compare_digest(key.encode(), env.STV_TOKEN_PAGE_KEY.encode()):
            failed_attempts += 1
            logger.warning("Wrong key on the 7TV token page ({}/{}).", failed_attempts, MAX_FAILED_ATTEMPTS)
            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                await bot.notify_developers("7TV token page got locked after too many wrong keys.")
            return _page("Wrong key.", ok=False)

        try:
            result = await save_stv_token(bot, token)
        except ValueError as exc:
            return _page(str(exc), ok=False)
        return _page(result)

    adapter.add_route(STV_TOKEN_PAGE_PATH, stv_token_page, methods=["GET", "POST"])
