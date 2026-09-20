import pytest
from src.shared.dota2.tools import extract_hero_index
from steam.ext import dota2

# pyright bug: if I do `from steam.ext.dota2 import Hero` it will fail to find stubs:
# Stub file not found for "steam.ext.dota2" (reportMissingTypeStubs)
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
]


@pytest.mark.parametrize(
    ("argument", "expected_hero", "heroes_in_match"),
    [
        ("pa", Hero.PhantomAssassin, ALL_HEROES),
        ("kEZ", Hero.Kez, ALL_HEROES),
        ("cm", Hero.CrystalMaiden, ALL_HEROES),
        ("naga", Hero.NagaSiren, MATCH_1_HEROES),
    ],
)
def test_fuzzy_extract_hero_index(argument: str, expected_hero: Hero, heroes_in_match: list[Hero]) -> None:
    """Test whether `extract_hero_index` function returns expected values."""
    assert extract_hero_index(argument, heroes_in_match)[0] == expected_hero
