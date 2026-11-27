# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Test the chat overlay's message rendering and emote bookkeeping."""

from typing import Any

import aiohttp
import pytest
import seven_tv_events

from ext.personal.chat_overlay.emotes import StvEmotes, parse_bttv, parse_ffz, stv_emote
from ext.personal.chat_overlay.render import (
    Fragment,
    OverlayEmote,
    default_colour,
    is_emote_only,
    readable_colour,
    render_parts,
    twitch_emote_url,
)

EMOTES = {
    "Okayge": OverlayEmote("Okayge", "/okayge.webp"),
    "RainTime": OverlayEmote("RainTime", "/raintime.webp", zero_width=True),
    "PETPET": OverlayEmote("PETPET", "/petpet.webp", zero_width=True),
}


def text(value: str) -> Fragment:
    return Fragment("text", value)


def test_plain_text_stays_one_part() -> None:
    parts, action = render_parts([text("hello there  friend")], EMOTES)
    assert parts == [{"type": "text", "text": "hello there  friend"}]
    assert not action


def test_third_party_emotes_are_found_between_words() -> None:
    parts, _ = render_parts([text("hi Okayge bye")], EMOTES)
    assert parts == [
        {"type": "text", "text": "hi "},
        {"type": "emote", "name": "Okayge", "url": "/okayge.webp", "overlays": []},
        {"type": "text", "text": " bye"},
    ]


def test_emote_names_are_case_sensitive_and_whole_words() -> None:
    parts, _ = render_parts([text("okayge Okayge, xOkayge")], EMOTES)
    assert parts == [{"type": "text", "text": "okayge Okayge, xOkayge"}]


def test_zero_width_emotes_stack_on_the_emote_before_them() -> None:
    parts, _ = render_parts([text("Okayge RainTime PETPET !")], EMOTES)
    assert parts == [
        {
            "type": "emote",
            "name": "Okayge",
            "url": "/okayge.webp",
            "overlays": [{"name": "RainTime", "url": "/raintime.webp"}, {"name": "PETPET", "url": "/petpet.webp"}],
        },
        {"type": "text", "text": " !"},
    ]


def test_zero_width_emote_on_a_twitch_emote() -> None:
    parts, _ = render_parts([Fragment("emote", "Kappa", "25"), text(" RainTime")], EMOTES)
    assert parts == [
        {
            "type": "emote",
            "name": "Kappa",
            "url": twitch_emote_url("25"),
            "overlays": [{"name": "RainTime", "url": "/raintime.webp"}],
        },
    ]


def test_zero_width_emote_without_an_emote_before_it_is_drawn_alone() -> None:
    parts, _ = render_parts([text("look RainTime")], EMOTES)
    assert parts == [
        {"type": "text", "text": "look "},
        {"type": "emote", "name": "RainTime", "url": "/raintime.webp", "overlays": []},
    ]


def test_mentions_and_cheermotes() -> None:
    parts, _ = render_parts([Fragment("mention", "@Irene"), text(" hi "), Fragment("cheermote", "Cheer100")], EMOTES)
    assert parts == [{"type": "mention", "text": "@Irene"}, {"type": "text", "text": " hi Cheer100"}]


def test_action_messages_lose_their_ctcp_wrapping() -> None:
    parts, action = render_parts([text("\x01ACTION waves Okayge\x01")], EMOTES)
    assert action
    assert parts == [
        {"type": "text", "text": "waves "},
        {"type": "emote", "name": "Okayge", "url": "/okayge.webp", "overlays": []},
    ]


def test_emote_only() -> None:
    assert is_emote_only(render_parts([text("Okayge  Okayge RainTime ")], EMOTES)[0])
    assert not is_emote_only(render_parts([text("Okayge hi")], EMOTES)[0])
    assert not is_emote_only(render_parts([text("   ")], EMOTES)[0])
    assert not is_emote_only(render_parts([Fragment("mention", "@a"), text(" Okayge")], EMOTES)[0])


@pytest.mark.parametrize("colour", ["#FFFFFF", "#FF69B4", "#00FF7F", "#DAA520"])
def test_readable_colour_keeps_light_colours(colour: str) -> None:
    assert readable_colour(colour) == colour


@pytest.mark.parametrize("colour", ["#0000FF", "#000000", "#8A2BE2", "#B22222"])
def test_readable_colour_lightens_dark_colours(colour: str) -> None:
    lighter = readable_colour(colour)
    assert lighter != colour
    assert sum(int(lighter[i : i + 2], 16) for i in (1, 3, 5)) > sum(int(colour[i : i + 2], 16) for i in (1, 3, 5))


def test_default_colour_is_stable() -> None:
    assert default_colour("irene_adler__") == default_colour("irene_adler__")
    assert default_colour("irene_adler__").startswith("#")


def test_bttv_parsing() -> None:
    emotes = parse_bttv([{"id": "abc", "code": "DankG"}, {"id": "def", "code": "SoSnowy"}])
    assert emotes["DankG"] == OverlayEmote("DankG", "https://cdn.betterttv.net/emote/abc/2x.webp")
    assert emotes["SoSnowy"].zero_width


def test_ffz_parsing_prefers_animated_and_bigger_images() -> None:
    sets = {
        "3": {
            "emoticons": [
                {"name": "Weirdge", "urls": {"1": "https://ffz/1", "2": "https://ffz/2"}},
                {"name": "Small", "urls": {"1": "https://ffz/small"}},
                {
                    "name": "Moving",
                    "urls": {"1": "https://ffz/m1"},
                    "animated": {"1": "https://ffz/a1", "2": "https://ffz/a2"},
                },
            ]
        },
        "4": {"emoticons": [{"name": "Unused", "urls": {"1": "https://ffz/u"}}]},
    }
    emotes = parse_ffz(sets, [3])
    assert {name: e.url for name, e in emotes.items()} == {
        "Weirdge": "https://ffz/2",
        "Small": "https://ffz/small",
        "Moving": "https://ffz/a2",
    }


def stv_emote_json(emote_id: str, name: str, *, flags: int = 0) -> dict[str, Any]:
    return {
        "id": emote_id,
        "name": name,
        "flags": flags,
        "data": {"id": emote_id, "name": name, "host": {"url": f"//cdn.7tv.app/emote/{emote_id}"}},
    }


def emote_set_update(emote_set_id: str, **changes: list[dict[str, Any]]) -> seven_tv_events.Dispatch:
    return seven_tv_events.Dispatch.from_json({
        "type": "emote_set.update",
        "body": {"id": emote_set_id, "kind": 3, **changes},
    })


async def test_stv_emote_set_updates() -> None:
    async with aiohttp.ClientSession() as session:
        stv = StvEmotes(session, "180499648")
        stv.emote_set_id = "01FAQVCS500002EV4FV330P46A"
        old = stv_emote_json("01AAAAAAAAAAAAAAAAAAAAAAAA", "Okayge")
        stv.channel_emotes = {old["id"]: seven_tv_events.Emote.from_json(old)}
        changes: list[None] = []
        stv.on_change.append(lambda: changes.append(None))

        added = stv_emote_json("01BBBBBBBBBBBBBBBBBBBBBBBB", "RainTime", flags=1)
        renamed = {**old, "name": "Okay"}
        await stv._on_emote_set_update(
            emote_set_update(
                stv.emote_set_id,
                pushed=[{"key": "emotes", "index": 1, "value": added}],
                updated=[{"key": "emotes", "index": 0, "old_value": old, "value": renamed}],
            )
        )
        assert set(stv.emotes()) == {"Okay", "RainTime"}
        assert stv.emotes()["RainTime"] == OverlayEmote(
            "RainTime", "/overlay/7tv/01BBBBBBBBBBBBBBBBBBBBBBBB/2x.webp", zero_width=True
        )
        assert added["id"] in stv.known_ids

        await stv._on_emote_set_update(
            emote_set_update(stv.emote_set_id, pulled=[{"key": "emotes", "index": 1, "old_value": added}])
        )
        assert set(stv.emotes()) == {"Okay"}

        # an event of some other set (e.g. the previous active one) changes nothing
        await stv._on_emote_set_update(
            emote_set_update("01CCCCCCCCCCCCCCCCCCCCCCCC", pushed=[{"key": "emotes", "index": 1, "value": added}])
        )
        assert set(stv.emotes()) == {"Okay"}
        assert len(changes) == 3


async def test_stv_events_during_a_load_are_applied_after_it() -> None:
    async with aiohttp.ClientSession() as session:
        stv = StvEmotes(session, "180499648")
        stv.emote_set_id = "01FAQVCS500002EV4FV330P46A"
        stv._buffer = []  # what load() does while its requests are in flight
        added = stv_emote_json("01BBBBBBBBBBBBBBBBBBBBBBBB", "Okayge")
        await stv._on_emote_set_update(
            emote_set_update(stv.emote_set_id, pushed=[{"key": "emotes", "index": 0, "value": added}])
        )
        assert stv.emotes() == {}
        assert len(stv._buffer) == 1


def test_global_and_channel_7tv_emotes() -> None:
    emote = seven_tv_events.Emote.from_json(stv_emote_json("01AAAAAAAAAAAAAAAAAAAAAAAA", "PETPET", flags=1))
    assert stv_emote(emote) == OverlayEmote(
        "PETPET", "/overlay/7tv/01AAAAAAAAAAAAAAAAAAAAAAAA/2x.webp", zero_width=True
    )
