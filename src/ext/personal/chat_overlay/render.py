# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Turn Twitch chat messages into the JSON pieces the chat overlay page draws.

All the work happens here, on the bot's side, so the page itself stays dumb: it gets text, emote image URLs,
badge URLs and a readable name colour, and never needs to know about 7TV, BTTV, FFZ or Twitch.
"""

from __future__ import annotations

import colorsys
import re
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

__all__ = (
    "Fragment",
    "OverlayEmote",
    "default_colour",
    "readable_colour",
    "render_parts",
    "twitch_emote_url",
)

type Part = dict[str, Any]

WHITESPACE = re.compile(r"(\s+)")
ACTION_PREFIX = "\x01ACTION "

# The colours Twitch gives chatters who never picked one.
TWITCH_DEFAULT_COLOURS = (
    "#FF0000",
    "#0000FF",
    "#008000",
    "#B22222",
    "#FF7F50",
    "#9ACD32",
    "#FF4500",
    "#2E8B57",
    "#DAA520",
    "#D2691E",
    "#5F9EA0",
    "#1E90FF",
    "#FF69B4",
    "#8A2BE2",
    "#00FF7F",
)

# The overlay sits on top of a game, so names need to stand out from a dark background.
MIN_LUMINANCE = 0.25


@dataclass(frozen=True, slots=True)
class OverlayEmote:
    """A third-party (7TV, BTTV or FFZ) emote, as the overlay draws it."""

    name: str
    url: str
    zero_width: bool = False
    """Drawn on top of the emote before it instead of next to it."""


@dataclass(frozen=True, slots=True)
class Fragment:
    """The part of a Twitch chat message fragment that matters for drawing it."""

    type: Literal["text", "cheermote", "emote", "mention", "gif"]
    text: str
    emote_id: str | None = None
    """The Twitch emote ID, for `emote` fragments."""


def twitch_emote_url(emote_id: str) -> str:
    """Return the image URL of a Twitch emote (animated when the emote is)."""
    return f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/dark/2.0"


def default_colour(login: str) -> str:
    """Return the colour Twitch would show for a chatter who never picked one, stable per login."""
    return TWITCH_DEFAULT_COLOURS[zlib.crc32(login.encode()) % len(TWITCH_DEFAULT_COLOURS)]


def _luminance(r: float, g: float, b: float) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def readable_colour(hex_colour: str) -> str:
    """Lighten a `#RRGGBB` colour until it is readable on a dark background; keep it if it already is."""
    r, g, b = (int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    while _luminance(r, g, b) < MIN_LUMINANCE and lightness < 1:
        lightness = min(1.0, lightness + 0.05)
        r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return "#{:02X}{:02X}{:02X}".format(*(round(c * 255) for c in (r, g, b)))


def _emote_part(name: str, url: str) -> Part:
    return {"type": "emote", "name": name, "url": url, "overlays": []}


def _add_text(parts: list[Part], text: str, kind: str = "text") -> None:
    if not text:
        return
    if parts and parts[-1]["type"] == kind == "text":
        parts[-1]["text"] += text
    else:
        parts.append({"type": kind, "text": text})


def _add_zero_width(parts: list[Part], emote: OverlayEmote) -> None:
    """Stack a zero-width emote on the emote before it, skipping whitespace between them."""
    index = len(parts) - 1
    while index >= 0 and parts[index]["type"] == "text" and not parts[index]["text"].strip():
        index -= 1
    if index >= 0 and parts[index]["type"] == "emote":
        del parts[index + 1 :]  # the whitespace between them
        parts[index]["overlays"].append({"name": emote.name, "url": emote.url})
    else:
        parts.append(_emote_part(emote.name, emote.url))


def render_parts(fragments: Iterable[Fragment], emotes: Mapping[str, OverlayEmote]) -> tuple[list[Part], bool]:
    """Split a chat message into text, mention and emote parts.

    Words of text fragments that are 7TV/BTTV/FFZ emote names (in `emotes`) become emotes, and zero-width ones
    are stacked on the emote before them. Returns the parts and whether the message is a `/me` action.
    """
    fragments = list(fragments)
    action = bool(fragments) and fragments[0].type == "text" and fragments[0].text.startswith(ACTION_PREFIX)
    if action:
        first = fragments[0]
        fragments[0] = Fragment(first.type, first.text.removeprefix(ACTION_PREFIX), first.emote_id)
        last = fragments[-1]
        fragments[-1] = Fragment(last.type, last.text.removesuffix("\x01"), last.emote_id)

    parts: list[Part] = []
    for fragment in fragments:
        match fragment.type:
            case "emote" if fragment.emote_id is not None:
                parts.append(_emote_part(fragment.text, twitch_emote_url(fragment.emote_id)))
            case "mention":
                _add_text(parts, fragment.text, "mention")
            case "text":
                for word in WHITESPACE.split(fragment.text):
                    emote = emotes.get(word)
                    if emote is None:
                        _add_text(parts, word)
                    elif emote.zero_width:
                        _add_zero_width(parts, emote)
                    else:
                        parts.append(_emote_part(emote.name, emote.url))
            case _:
                _add_text(parts, fragment.text)
    return parts, action


def is_emote_only(parts: Iterable[Part]) -> bool:
    """Whether a message is nothing but emotes (and whitespace), so the overlay can draw it bigger."""
    has_emote = False
    for part in parts:
        if part["type"] == "emote":
            has_emote = True
        elif part["type"] != "text" or part["text"].strip():
            return False
    return has_emote
