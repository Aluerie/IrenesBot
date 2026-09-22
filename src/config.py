"""
_Insert Module Docstring Here_.

License
-------
* This Source Code Form is subject to the terms of the [Mozilla Public License v2.0](<http://mozilla.org/MPL/2.0/>).
* Copyright (C) 2020-present [@Aluerie](<https://github.com/Aluerie>).
"""

from __future__ import annotations

import re

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ("env", "replace_secrets")


class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )


class Env(EnvConfig):
    PROJECT_NAME: str
    TWITCH_CLIENT_ID: str
    TWITCH_CLIENT_SECRET: str
    TEST_TWITCH_CLIENT_ID: str
    TEST_TWITCH_CLIENT_SECRET: str
    POSTGRES_VPS: str
    POSTGRES_HOME: str
    STEAM_FRIEND_IRENE_ID64: int
    STEAM_FRIEND_IRENE_ID32: int
    STEAM_IRENESTEST_USERNAME: str
    STEAM_IRENESTEST_PASSWORD: str
    STEAM_IRENESBOT_USERNAME: str
    STEAM_IRENESBOT_PASSWORD: str
    STRATZ_BEARER: str
    STEAM_API_KEY: str
    SEVEN_TV_BEARER: str
    SPOTIFY_AIDENWALLIS: str
    EVENTSUB: str
    WEBHOOK_LOGGER: str
    WEBHOOK_ERROR: str
    WEBHOOK_STREAM_NOTIFS: str
    WEBHOOK_HEARTBEAT: str


env = Env()  # pyright: ignore[reportCallIssue]

secrets_list = list(map(str, env.model_dump().values()))
DO_NOT_SPOIL_PATTERN = re.compile("|".join(map(re.escape, secrets_list)))


def replace_secrets(text: str) -> str:
    """Hide my `.env` secrets from a string.

    A precaution measure.
    For example, it's possible for error handler to spoil my secrets when reporting some `HTTPException`.
    """
    return DO_NOT_SPOIL_PATTERN.sub("<SECRET>", text)
