"""Test Dota 2 features.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import pytest
from src.modules.public.mmrbot import extract_player_slot
from steam.ext import dota2

Hero = dota2.Hero

ALL_HEROES = list(Hero)
MATCH_1_HEROES = [
    Hero.Clockwerk,
    Hero.Grimstroke,
    Hero.NagaSiren,
    Hero.Tinker,
    Hero.PrimalBeast,
    Hero.QueenOfPain,
    Hero.TemplarAssassin,
    Hero.VengefulSpirit,
    Hero.Windranger,
    Hero.Magnus,
    Hero.PhantomAssassin,
    Hero.Kez,
    Hero.CrystalMaiden,
]


@pytest.mark.parametrize(
    ("argument", "expected_index"),
    [
        ("pa", 10),
        ("kEZ", 11),
        ("cm", 12),
        ("naga", 2),
    ],
)
def test_fuzzy_extract_hero_index(argument: str, expected_index: int) -> None:
    """Test whether `extract_hero_index` function returns expected values."""
    assert extract_player_slot(argument, [h.name for h in MATCH_1_HEROES]) == expected_index
