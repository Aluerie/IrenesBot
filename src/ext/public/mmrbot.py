# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""MMR Bot.

The name is a homage to old-school famous @9kmmrbot which was a twitch bot for Dota 2 streamers
with various chat commands such as `!np`.

Nowadays, @dotabod is quite popular and feature rich, but I always liked simplicity of @9kmmrbot.
Its author (@Hambergo) is a cool guy too.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import operator
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypedDict, override
from urllib import parse as url_parse

from steam.ext.dota2 import Hero, LobbyType, MatchOutcome
from twitchio.ext import commands

from config import env
from core import Component, Context
from shared import clock, errors, fmt, fuzzy
from shared.apis import local, steam_web
from utils import const, guards

if TYPE_CHECKING:
    from core import Bot

    # DATABASE QUERIES

    class NotablePlayersQueryRow(TypedDict):
        friend_id: int
        nickname: str

    class ScoreQueryRow(TypedDict):
        friend_id: int
        start_time: dt.datetime
        lobby_type: int
        game_mode: int
        outcome: int | None
        player_slot: int
        abandon: bool


__all__ = ("MMRBot",)

# Dota 2 matches of a gaming session are at most this far from each other.
GAMING_SESSION_GAP = dt.timedelta(hours=6)

# /* cSpell:disable */
HERO_ALIASES: dict[str, list[str]] = {
    # HERO ALIASES.
    #
    # The list mainly for !profile/!items command so people can just write "!items CM"
    # and the bot will send Crystal Maiden's items.
    #
    # The list includes mostly
    # * abbreviations, i.e. "cm";
    # * persona names i.e. "wei";
    # * dota 1 names , i.e. "traxex"
    # * official names, i.e. "beastmaster";
    # * short forms of any from above, i.e. "cent";
    # * just nicknames, aliases or common names that people sometimes *actually* use for Dota 2 heroes ;
    #
    # It doesn't include aliases that people don't use
    # i.e. nobody calls techies as "Squee, Spleen & Spoon"
    #
    "Abaddon": ["abaddon", "aba"],
    "Alchemist": ["alch", "alchemist"],
    "AncientApparition": ["aa", "apparition", "ancient apparition"],
    "AntiMage": ["am", "wei", "magina", "anti-mage", "antimage"],
    "ArcWarden": ["aw", "arc", "zett", "arc warden"],
    "Axe": ["axe"],
    "Bane": ["bane"],
    "Batrider": ["bat", "batrider"],
    "Beastmaster": ["bm", "beastmaster"],
    "Bloodseeker": ["bs", "strygwyr", "seeker", "blood", "bloodseeker"],
    "BountyHunter": ["bh", "gondar", "bounty hunter"],
    "Brewmaster": ["brew", "brewmaster"],
    "Bristleback": ["bb", "bristle", "bristleback"],
    "Broodmother": ["brood", "spider", "broodmother"],
    "CentaurWarrunner": ["centaur", "cent", "centaur warrunner"],
    "ChaosKnight": ["ck", "chaos", "chaos knight"],
    "Chen": ["chen"],
    "Clinkz": ["clinkz"],
    "Clockwerk": ["clock", "clockwerk"],
    "CrystalMaiden": ["cm", "rylai", "crystal maiden"],
    "DarkSeer": ["ds", "dark seer"],
    "DarkWillow": ["dw", "mireska", "oversight", "dark willow"],
    "Dawnbreaker": ["dawnbreaker", "valora", "dawn"],
    "Dazzle": ["dazzle"],
    "DeathProphet": ["dp", "krobelus", "death prophet"],
    "Disruptor": ["dis", "disruptor"],
    "Doom": ["doom"],
    "DragonKnight": ["dk", "davion", "dragon knight"],
    "DrowRanger": ["traxex", "drow", "drow ranger"],
    "EarthSpirit": ["es", "kaolin", "earth", "earth spirit"],
    "Earthshaker": ["es", "earthshaker"],
    "ElderTitan": ["et", "elder titan"],
    "EmberSpirit": ["xin", "ember", "es", "ember spirit"],
    "Enchantress": ["ench", "enchantress"],
    "Enigma": ["nigma", "enigma"],
    "FacelessVoid": ["fv", "faceless void"],
    "Grimstroke": ["grim", "grimstroke"],
    "Gyrocopter": ["gyro", "gyrocopter"],
    "Hoodwink": ["hood", "hw", "hoodwink"],
    "Huskar": ["huskar"],
    "Invoker": ["invo", "invoker"],
    "Io": ["wisp", "io"],
    "Jakiro": ["thd", "twin headed dragon", "jakiro"],
    "Juggernaut": ["yurnero", "jugg", "juggernaut"],
    "KeeperOfTheLight": ["keeper", "ezalor", "kotl", "keeper of the light"],
    "Kez": ["kez"],
    "Kunkka": ["admiral", "kunkka"],
    "Largo": ["largo"],
    "LegionCommander": ["tresdin", "legion", "lc", "legion commander"],
    "Leshrac": ["lesh", "leshrac"],
    "Lich": ["lich"],
    "Lifestealer": ["ls", "naix", "lifestealer"],
    "Lina": ["slayer", "lina"],
    "Lion": ["demon witch", "lion"],
    "LoneDruid": ["ld", "lone druid"],
    "Luna": ["moon rider", "luna"],
    "Lycan": ["lycan"],
    "Magnus": ["mag", "magnus"],
    "Marci": ["marci"],
    "Mars": ["mars"],
    "Medusa": ["medusa"],
    "Meepo": ["meepo"],
    "Mirana": ["potm", "mirana"],
    "MonkeyKing": ["mk", "wukong", "monkey king"],
    "Morphling": ["morph", "morphling"],
    "Muerta": ["muerta"],
    "NagaSiren": ["naga", "naga siren"],
    "NaturesProphet": ["np", "furion", "nature's prophet"],
    "Necrophos": ["necro", "necrophos"],
    "NightStalker": ["ns", "balanar", "night stalker"],
    "NyxAssassin": ["nyx", "nyx assassin"],
    "OgreMagi": ["ogre", "ogre magi"],
    "Omniknight": ["omniknight"],
    "Oracle": ["oracle"],
    "OutworldDestroyer": ["od", "outworld destroyer"],
    "Pangolier": ["ar", "pango", "pangolier"],
    "PhantomAssassin": ["pa", "mortred", "phantom assassin"],
    "PhantomLancer": ["pl", "phantom lancer"],
    "Phoenix": ["phoenix"],
    "PrimalBeast": ["pb", "primal beast"],
    "Puck": ["puck"],
    "Pudge": ["butcher", "pudge"],
    "Pugna": ["pugna"],
    "QueenOfPain": ["qop", "akasha", "queen of pain", "queen"],
    "Razor": ["razor"],
    "Riki": ["riki"],
    "Ringmaster": ["ringmaster"],
    "Rubick": ["rubick"],
    "SandKing": ["sk", "sand king"],
    "ShadowDemon": ["sd", "shadow demon"],
    "ShadowFiend": ["sf", "nevermore", "shadow fiend"],
    "ShadowShaman": ["ss", "rhasta", "shaman", "shadow shaman"],
    "Silencer": ["silencer"],
    "SkywrathMage": ["sky", "skywrath mage"],
    "Slardar": ["slardar"],
    "Slark": ["slark"],
    "Snapfire": ["snap", "snapfire"],
    "Sniper": ["sniper"],
    "Spectre": ["spectre"],
    "SpiritBreaker": ["sb", "bara", "spirit breaker"],
    "StormSpirit": ["ss", "storm", "storm spirit"],
    "Sven": ["sven"],
    "Techies": ["techies"],
    "TemplarAssassin": ["ta", "lanaya", "templar assassin"],
    "Terrorblade": ["tb", "terrorblade"],
    "Tidehunter": ["th", "tidehunter"],
    "Timbersaw": ["timber", "timbersaw"],
    "Tinker": ["tinker"],
    "Tiny": ["tiny"],
    "TreantProtector": ["tree", "treant", "treant protector"],
    "TrollWarlord": ["troll", "troll warlord"],
    "Tusk": ["tusk"],
    "Underlord": ["pitlord", "underlord"],
    "Undying": ["dirge", "undying"],
    "Ursa": ["ursa"],
    "VengefulSpirit": ["vs", "venge", "vengeful spirit"],
    "Venomancer": ["veno", "venomancer"],
    "Viper": ["viper"],
    "Visage": ["visage"],
    "VoidSpirit": ["void", "vs", "void spirit"],
    "Warlock": ["warlock"],
    "Weaver": ["weaver"],
    "Windranger": ["wr", "lyralei", "windranger"],
    "WinterWyvern": ["ww", "winter wyvern"],
    "WitchDoctor": ["wd", "witch doctor"],
    "WraithKing": ["wk", "wraith king"],
    "Zeus": ["zuus", "zeus"],
}
# /* cSpell:enable */


COLOR_ALIASES: dict[int, list[str]] = {
    0: ["blue"],
    1: ["teal"],
    2: ["purple"],
    3: ["yellow"],
    4: ["orange"],
    5: ["pink"],
    6: ["olive", "grey"],  # it was originally grey in WC3, but idk, it's easy to confuse with lightblue I feel like.
    7: ["lightblue", "white"],
    8: ["darkgreen", "green"],
    9: ["brown"],
}


def extract_player_slot(argument: str, hero_names: list[str]) -> int:
    """Convert command argument provided by user (twitch chatter) into a player index in the match.

    Uses fuzzy match to extract the likely match.

    It supports
    * player slot as digits;
    * player colors;
    * hero aliases (which include hero localized names, abbreviations and some common nicknames);

    Parameters
    ----------
    argument
        What the chatter has typed.
    hero_names
        Names of the heroes in the match, in the order of the player slots.

    Returns
    -------
    int
        Index of the matched player in `hero_names`.
    """
    if argument.isdecimal():
        # then the user typed only a number and our life is easy because it is a player slot
        # let's consider users normal: they start enumerating slots from 1 instead of 0.
        number = int(argument)
        if not 1 <= number <= len(hero_names):
            msg = f"Player slot should be a number from 1 to {len(hero_names)}: that many players are in the match."
            raise errors.RespondWithError(msg)
        return number - 1

    # Otherwise - we have to use the fuzzy search: the alias with the best score wins, colors win ties.
    best_score = 0
    best_match: int | str | None = None  # either a slot (for colors) or a hero name (for hero aliases)

    for player_slot, color_aliases in COLOR_ALIASES.items():
        find = fuzzy.extract_one(argument, color_aliases, scorer=fuzzy.quick_token_sort_ratio, score_cutoff=49)
        if find and find[1] > best_score:
            best_score, best_match = find[1], player_slot

    # Heroes in the match go first (i.e. so "es" alias triggers on a hero in the match first)
    heroes_in_match = set(hero_names)
    for hero, hero_aliases in sorted(HERO_ALIASES.items(), key=lambda item: item[0] in heroes_in_match, reverse=True):
        find = fuzzy.extract_one(argument, hero_aliases, scorer=fuzzy.quick_token_sort_ratio, score_cutoff=49)
        if find and find[1] > best_score:
            best_score, best_match = find[1], hero

    if best_match is None:
        msg = 'Sorry, didn\'t understand your query. Try something like "PA / 7 / Phantom Assassin / Blue".'
        raise errors.RespondWithError(msg)

    if isinstance(best_match, int):
        if best_match >= len(hero_names):
            msg = f"There is no {COLOR_ALIASES[best_match][0]} player in this match."
            raise errors.RespondWithError(msg)
        return best_match

    try:
        return hero_names.index(best_match)
    except ValueError:
        msg = f"Hero {best_match} is not present in the match."
        raise errors.RespondWithError(msg) from None


def pick_player(match: local.FriendLiveMatch, argument: str) -> tuple[int, local.FriendLiveMatchPlayer]:
    """Find the match player the chatter is talking about.

    Returns
    -------
    tuple[int, FriendLiveMatchPlayer]
        Index of the player in the match and the player themselves.
    """
    player_slot = extract_player_slot(argument, [player.hero.name for player in match.players])
    return player_slot, match.players[player_slot]


@dataclass
class Score:
    """Win-loss record for one category of matches."""

    wins: int = 0
    losses: int = 0
    abandons: int = 0
    pending: int = 0

    @override
    def __str__(self) -> str:
        wl = f"{self.wins} W - {self.losses} L"
        if self.abandons:
            wl += f", Abandons: {self.abandons}"
        if self.pending:
            wl += f", Pending: {self.pending}"
        return wl

    def record(self, outcome: int | None, *, player_slot: int, abandon: bool | None) -> None:
        """Add a single match to the score.

        Parameters
        ----------
        outcome
            Match outcome, ``None`` if it is not known yet.
        player_slot
            The player's slot, where slots below 5 belong to Radiant.
        abandon
            Whether the player abandoned the match.
        """
        if bool(abandon):
            self.abandons += 1
        elif outcome is None:
            self.pending += 1
        elif outcome in {MatchOutcome.RadiantVictory, MatchOutcome.DireVictory}:
            is_radiant = player_slot < 5
            if (outcome == MatchOutcome.RadiantVictory) == is_radiant:
                self.wins += 1
            else:
                self.losses += 1


def is_allowed_to_add_notable() -> Any:
    """Allow !npm add/remove/rename to only be invoked by certain people."""

    def predicate(ctx: Context) -> bool:
        # Maybe we will edit this to be some proper dynamic database thing;
        allowed_ids = (const.UserID.Irene, const.UserID.Xas)
        if ctx.chatter.id in allowed_ids:
            return True
        msg = f"You are not allowed to add notable players into the bot's database {const.Ffz.peepoPolice}"
        raise errors.NotAllowedError(msg)

    return commands.guard(predicate)


SEPARATOR = " \N{BULLET} "

PLAYED_WITH_QUERY = """
WITH me AS (
    SELECT p.friend_id
    FROM shared.dota_match_players AS p
    JOIN shared.dota_accounts AS a USING (friend_id)
    WHERE p.match_id = $1
      AND a.twitch_id = $2
    LIMIT 1
),
live AS (
    SELECT start_time
    FROM shared.dota_matches
    WHERE match_id = $1
),
history AS (
    SELECT
        m.match_id,
        m.start_time,
        LEAD(m.start_time) OVER (ORDER BY m.start_time) - m.start_time AS gap_to_next
    FROM shared.dota_matches AS m
    JOIN shared.dota_match_players AS p USING (match_id)
    WHERE p.friend_id = (SELECT friend_id FROM me)
      AND (m.failed = 0 OR m.match_id = $1)
      AND m.start_time <= (SELECT start_time FROM live)
),
session_matches AS (
    SELECT
        h.match_id,
        ROW_NUMBER() OVER (ORDER BY h.start_time DESC) - 1 AS matches_ago
    FROM history AS h
    WHERE h.start_time > COALESCE(
        (SELECT MAX(start_time) FROM history WHERE gap_to_next > INTERVAL '6 hours'),
        '-infinity'::timestamptz
    )
)
SELECT DISTINCT ON (sp.friend_id)
    sp.friend_id,
    sp.hero_id,
    sm.matches_ago
FROM shared.dota_match_players AS lp
JOIN shared.dota_match_players AS sp ON sp.friend_id = lp.friend_id
JOIN session_matches AS sm ON sm.match_id = sp.match_id
WHERE lp.match_id = $1
  AND lp.friend_id <> (SELECT friend_id FROM me)
  AND sm.matches_ago > 0
ORDER BY sp.friend_id, sm.matches_ago;
"""


def _ago(n: int) -> str:
    """Format a number of matches back as text.

    Parameters
    ----------
    n
        How many matches ago, where ``1`` is the previous game.
    """
    return "last game" if n == 1 else f"{n} matches ago"


SCORE_QUERY = """
    WITH matches AS (
        SELECT
            d.friend_id,
            m.start_time,
            m.lobby_type,
            m.game_mode,
            m.outcome,
            p.player_slot,
            p.abandon,
            LAG(m.start_time) OVER (ORDER BY m.start_time DESC) - m.start_time AS gap_to_newer
        FROM dota_matches AS m
        JOIN dota_match_players AS p ON p.match_id = m.match_id
        JOIN dota_accounts AS d ON d.friend_id = p.friend_id
        WHERE d.twitch_id = $1
          AND m.live > $2
          AND ($3::timestamptz IS NULL OR m.start_time > $3)
    )
    SELECT friend_id, start_time, lobby_type, game_mode, outcome, player_slot, abandon
    FROM matches
    WHERE start_time > COALESCE(
        (SELECT MAX(start_time) FROM matches WHERE gap_to_newer > $4),
        '-infinity'::timestamptz
    )
    ORDER BY start_time DESC;
"""


class MMRBot(Component):
    """MMR Bot."""

    def __init__(self, bot: Bot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.steam_web = steam_web.SteamWebAPIClient(session=bot.session, api_key=env.STEAM_API_KEY)
        self.local_api = local.LocalAPI(bot.session)

    # --- COMMON -------------------------------------------------------------------------------------------------------

    async def get_friend_id(self, broadcaster_id: str) -> int:
        """Get the friend id of the steam account the broadcaster has been seen last online on."""
        query = """
            SELECT friend_id
            FROM dota_accounts
            WHERE twitch_id = $1
            ORDER BY last_seen DESC
            LIMIT 1;
        """
        row = await self.bot.pool.fetchrow(query, broadcaster_id)
        if row is None:
            msg = "There is no steam accounts associated with this twitch channel"
            raise errors.RespondWithError(msg)

        return row["friend_id"]

    async def get_friend(self, broadcaster_id: str, *, is_green_online_required: bool = True) -> local.Friend:
        """Find broadcaster's steam friend.

        Note that we only return their last-seen account.
        We assume the last-seen account is the one they want to use commands against.
        """
        friend_id = await self.get_friend_id(broadcaster_id)
        friend = await self.local_api.get_friend(friend_id)
        if is_green_online_required and not friend.is_playing_dota:
            msg = "Inactive command \N{BULLET} it requires streamer to be green-online \N{LARGE GREEN CIRCLE} in Dota 2"
            raise errors.RespondWithError(msg)
        return friend

    # --- LIVE GAME ----------------------------------------------------------------------------------------------------

    async def get_live_match(self, broadcaster_id: str) -> local.FriendLiveMatch:
        """Find broadcaster's active match."""
        streamer = await self.get_friend(broadcaster_id)
        live_match = streamer.live_match
        if live_match is None:
            msg = f"No Active Game Found \N{BULLET} Streamer's status: {streamer.status}"
            raise errors.RespondWithError(msg)
        if live_match.tag == "unsupported":
            raise errors.RespondWithError(live_match.message)
        if live_match.state == local.MatchState.GaveUp:
            msg = "I'm not able to fetch data for this match, sorry."
            raise errors.RespondWithError(msg)
        return live_match

    async def send_with_tag(
        self, ctx: Context, match: local.FriendLiveMatch, content: str, *, delayed: bool = False
    ) -> None:
        """Send the response with a prefix describing where the data comes from, if it's not a regular case.

        Parameters
        ----------
        ctx
            Command context.
        match
            The live match the response is about.
        content
            The response itself.
        delayed
            Whether the data lags behind the game. This applies to matches the streamer is playing.
        """
        if match.tag == "spectating":
            prefix = "[Spectating] "
        elif delayed:
            prefix = "[2m delay] "
        else:
            prefix = ""
        await ctx.send(f"{prefix}{content}")

    @commands.command()
    async def server_steam_id(self, ctx: Context) -> None:
        """Show server steam id for the match.

        Useful if I want to manually request `GetRealTimeStats`.
        """
        match = await self.get_live_match(ctx.broadcaster.id)
        content = "No server data yet." if match.server_steam_id is None else str(match.server_steam_id)
        await self.send_with_tag(ctx, match, content)

    @commands.command(aliases=["matchid"])
    async def match_id(self, ctx: Context) -> None:
        """Show match ID for the current match."""
        match = await self.get_live_match(ctx.broadcaster.id)
        content = "No match data yet." if match.id is None else str(match.id)
        await self.send_with_tag(ctx, match, content)

    @commands.command(aliases=["gm"])
    async def game_medals(self, ctx: Context) -> None:
        """Fetch each player rank medals in the current game."""
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match.players:
            content = "No player data yet"
        else:
            response_parts = [f"{player.identifier} {player.rank_display_name}" for player in match.players]
            prefix = f"[{avg_mmr} avg mmr] " if bool(avg_mmr := match.average_mmr) else ""
            content = prefix + " \N{BULLET} ".join(response_parts)
        await self.send_with_tag(ctx, match, content)

    @commands.command()
    async def ranked(self, ctx: Context) -> None:
        """Show whether the current game is ranked or not."""
        match = await self.get_live_match(ctx.broadcaster.id)
        if match.lobby_type is None or match.game_mode is None:
            content = "No lobby data yet."
        else:
            yes_no = "Yes" if match.lobby_type == LobbyType.Ranked else "No"
            content = f"{yes_no}, it's {match.lobby_type.display_name} ({match.game_mode.display_name})"
        await self.send_with_tag(ctx, match, content)

    @commands.command(aliases=["lifetime"])
    async def smurfs(self, ctx: Context) -> None:
        """Show amount of total games each player has on their accounts.

        Not really a "smurf detector", but it's quite good initial metric.
        """
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match.players:
            content = "No players data yet."
        else:
            response_parts = [
                f"{player.identifier} {player.lifetime_games}"
                for player in sorted(match.players, key=operator.attrgetter("lifetime_games"))
            ]
            content = "Lifetime Games: " + " \N{BULLET} ".join(response_parts)
        await self.send_with_tag(ctx, match, content)

    @commands.command(name="notable", aliases=["np"])
    async def notable_players(self, ctx: Context) -> None:
        """List notable players for the current match."""
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match.players:
            content = "No player data yet."
        else:
            query = "SELECT friend_id, nickname FROM dota_notable_players WHERE friend_id = ANY($1);"
            rows: list[NotablePlayersQueryRow] = await self.bot.pool.fetch(query, [p.id for p in match.players])
            if not rows:
                content = "No notable players found"
            else:
                nickname_mapping = {row["friend_id"]: row["nickname"] for row in rows}
                response_parts = [
                    f"{nick} as {player.identifier}"
                    for player in match.players
                    if (nick := nickname_mapping.get(player.id)) is not None
                ]
                content = " \N{BULLET} ".join(response_parts)
        await self.send_with_tag(ctx, match, content)

    @commands.command(aliases=["player"])
    async def profile(self, ctx: Context, *, player_slot_color_or_hero_name: str) -> None:
        """Get a link to player stats profile.

        Parameters
        ----------
        player_slot_color_or_hero_name
            A hero name, hero alias, player slot or colour.
        """
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match.players:
            content = "No player data yet."
        else:
            _, player = pick_player(match, player_slot_color_or_hero_name)
            content = f"{player.identifier} stratz.com/players/{player.id}"
        await self.send_with_tag(ctx, match, content)

    # --- LIVE GAME THAT REQUIRE REAL TIME STATS -----------------------------------------------------------------------

    async def get_real_time_stats(self, match: local.FriendLiveMatch) -> steam_web.RealTimeStats:
        """Get real time stats of the match from Steam Web API."""
        if match.lobby_type == LobbyType.NewPlayerMode:
            msg = "New Player Mode matches do not support real time stats."
            raise errors.RespondWithError(msg)
        if match.server_steam_id is None:
            msg = "No match data yet."
            raise errors.RespondWithError(msg)
        return await self.steam_web.get_real_time_stats(match.server_steam_id)

    @commands.command(aliases=["items", "kda"])
    async def stats(self, ctx: Context, *, player_slot_color_or_hero_name: str) -> None:
        """Fetch items and some profile data about a certain player in the game.

        Parameters
        ----------
        player_slot_color_or_hero_name
            A hero name, hero alias, player slot or colour.
        """
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match.players:
            await ctx.send("No player data yet.")
            return

        player_slot, player = pick_player(match, player_slot_color_or_hero_name)
        stats = await self.get_real_time_stats(match)

        api_player = next((p for p in stats.players if p.hero.id == player.hero.id), None)
        if api_player is None:
            msg = f"Somehow couldn't find the player {player_slot=} with {player.hero.name} in the game."
            raise errors.SomethingWentWrongError(msg)

        item_ids = [item for item in api_player.items if item != -1]
        if not item_ids:
            items = "No items yet"
        else:
            query = "SELECT item_id, display_name FROM dota_constants_items WHERE item_id = ANY($1::int[]);"
            item_names: dict[int, str] = {
                row["item_id"]: row["display_name"] for row in await self.bot.pool.fetch(query, item_ids)
            }
            items = ", ".join(item_names.get(item, "Unknown Item") for item in item_ids)

        content = " \N{BULLET} ".join((
            api_player.name,
            f"{player.identifier} lvl {api_player.level}",
            f"NW {api_player.networth / 1000:.1f}k (gold {api_player.gold / 1000:.1f}k)",
            f"KDA {api_player.kills}/{api_player.deaths}/{api_player.assists}",
            f"CS {api_player.creep_score}/{api_player.denies}",
            items,
        ))
        await self.send_with_tag(ctx, match, content, delayed=True)

    @stats.error
    @profile.error
    async def stats_error(self, payload: commands.CommandErrorPayload) -> None:
        """Error for !stats argument."""
        if isinstance(payload.exception, commands.MissingRequiredArgument):
            await payload.context.send(
                "You need to provide a hero name (i.e. VengefulSpirit , PA, Mireska, etc) or "
                "player slot (i.e. 9, DarkGreen )"
            )
        else:
            raise payload.exception

    @commands.command()
    async def lead(self, ctx: Context) -> None:
        """Show which team has a gold lead and by how much."""
        match = await self.get_live_match(ctx.broadcaster.id)
        stats = await self.get_real_time_stats(match)
        lead = stats.radiant_nw - stats.dire_nw
        if lead == 0:
            summary = "Net worth is even"  # is it even possible in Dota :D
        else:
            summary = f"{'Radiant' if lead > 0 else 'Dire'} is leading by {abs(lead) / 1000:.1f}k"
        content = f"Radiant {stats.radiant_score} - Dire {stats.dire_score}: {summary}"
        await self.send_with_tag(ctx, match, content, delayed=True)

    # --- LAST GAME(-S) ------------------------------------------------------------------------------------------------

    async def get_last_game(self, broadcaster_id: str) -> tuple[int, local.MinimalMatch]:
        """Get broadcaster's last finished game from the database.

        Returns
        -------
        tuple[int, MinimalMatch]
            Friend id of the streamer's account that has played the game, and the game itself.
            The friend id is useful at identifying the streamer among the match players.
            If a player has their data private then MinimalMatch will have zero for that player's id.
        """
        query = """
            SELECT p.match_id, p.friend_id
            FROM dota_matches m
                    JOIN dota_match_players p ON m.match_id = p.match_id
                    JOIN dota_accounts a ON a.friend_id = p.friend_id
            WHERE a.twitch_id = $1 AND m.live > $2
            ORDER BY m.start_time DESC
            LIMIT 1;
        """
        row = await self.bot.pool.fetchrow(query, broadcaster_id, local.MatchState.Live)
        if not row:
            msg = "No last game found: the bot hasn't recorded any streamer's games"
            raise errors.RespondWithError(msg)
        last_game = await self.local_api.get_minimal_match(row["match_id"])
        return row["friend_id"], last_game

    @commands.command(name="played", aliases=["last_game", "lg", "lm", "lgs"])
    async def played_with(self, ctx: Context) -> None:
        """List recurring players from the last gaming session present in the current match."""
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match.players:
            await ctx.send("No player data yet.")
            return

        if match.tag != "playing":
            await ctx.send("This command only works for the matches the streamer is playing in, not spectating.")
            return

        rows = await self.bot.pool.fetch(PLAYED_WITH_QUERY, match.id, ctx.broadcaster.id)
        previous = {row["friend_id"]: row for row in rows}

        response_parts = [
            f"{player.identifier} played as {Hero(prev['hero_id']).display_name} {_ago(prev['matches_ago'])}"
            for player in match.players
            if (prev := previous.get(player.id))
        ]
        content = (
            SEPARATOR.join(response_parts)
            if response_parts
            else "No players from the last game(-s) present in the match"
        )
        await ctx.chunk_send(content)

    @commands.command(aliases=["pm"])
    async def previous_match(self, ctx: Context, index: int = 0) -> None:
        """Show summary stats for the previous match.

        Parameters
        ----------
        index
            How far to look back: 0 is the latest match, 1 is the one before it, and so on.
        """
        if not 0 <= index < 20:
            msg = "'index' argument should be an integer and 0 <= index < 20"
            raise errors.RespondWithError(msg)

        friend_id = await self.get_friend_id(ctx.broadcaster.id)
        match = await self.local_api.get_previous_match(friend_id, index=index)

        minimal = await self.local_api.get_minimal_match(match.id)
        player = next((p for p in minimal.players if p.hero.id == match.hero.id), None)
        if player is None:
            msg = "Somehow can't find streamer's account in their previous match uuh weird"
            raise errors.SomethingWentWrongError(msg)

        response = (
            f"Previous Match - {match.category.name}: {'Win' if match.win else 'Loss'} as "
            f"{player.hero.name} {player.kills}/{player.deaths}/{player.assists} "
            f"\N{BULLET} ended {clock.human_datetime_diff(match.end_dt, mode='short')} ago "
            f"\N{BULLET} stratz.com/matches/{match.id}"
        )
        await ctx.send(response)

    # --- NOTABLE PEOPLE MANAGEMENT ------------------------------------------------------------------------------------

    @guards.is_production()
    @commands.group(name="npm", aliases=["np-dev"], invoke_fallback=True)
    async def npm_dev(self, ctx: Context) -> None:
        """Group command for the bot developer to manage list of notable players in the database."""
        message = (
            '"!npm" is a group command: use it together with its subcommands (add, help, remove, find), '
            'i.e. "!npm add 123 Arteezy"'
        )
        await ctx.send(message)

    @is_allowed_to_add_notable()
    @npm_dev.command(name="add", aliases=["edit", "rename"])
    async def npm_dev_add(self, ctx: Context, friend_id: int, *, name: str) -> None:
        """Add a notable player to the database.

        This command is only available for certain group of people.
        Since if the player already exists - it will just replace the entry - this command
        also works as `!npm rename` just fine (we don't need to raise anything)
        """
        steam_user = await self.local_api.get_steam_user(friend_id)
        query = """
            INSERT INTO dota_notable_players
            (friend_id, nickname)
            VALUES ($1, $2)
            ON CONFLICT (friend_id) DO
                UPDATE SET nickname = $2;
        """
        await self.bot.pool.execute(query, steam_user.id, name)
        await ctx.send(f"Added/edited a notable player <friend_id={steam_user.id}, name={name}>")

    @is_allowed_to_add_notable()
    @npm_dev.command(name="help")
    async def npm_dev_help(self, ctx: Context) -> None:
        """Show small help for !np-dev commands."""
        response = (
            "!npm add 123 Arteezy \N{BULLET} "
            "!npm remove 123 \N{BULLET} "
            "!npm rename 123 SADBOY \N{BULLET} "
            "where 123 is their friend_id; "
            "!npm find Arteezy - to get their friend_id."
        )
        await ctx.send(response)

    @is_allowed_to_add_notable()
    @npm_dev.command(name="remove")
    async def npm_dev_remove(self, ctx: Context, friend_id: int) -> None:
        """Remove a notable player from the database."""
        query = """
            DELETE FROM dota_notable_players
            WHERE friend_id = $1
            RETURNING nickname;
        """
        name: str | None = await self.bot.pool.fetchval(query, friend_id)
        if name is None:
            await ctx.send("This is not a notable player.")
            return
        await ctx.send(f"Removed player <friend_id={friend_id}, name={name}> from notable players.")

    @is_allowed_to_add_notable()
    @npm_dev.command(name="find")
    async def npm_dev_find(self, ctx: Context, *, name: str) -> None:
        """Find a notable player from the database."""
        query = """
            SELECT friend_id, nickname
            FROM dota_notable_players
            ORDER BY similarity(nickname, $1) DESC
            LIMIT 3;
        """
        rows = await self.bot.pool.fetch(query, name)
        if not rows:
            await ctx.send("There are no notable players in the database yet.")
            return
        response = f'3 most similar entries "{name}": ' + " \N{BULLET} ".join(
            f"{row['nickname']} id={row['friend_id']}" for row in rows
        )
        await ctx.send(response)

    # --- PROFILE ------------------------------------------------------------------------------------------------------

    @commands.command(aliases=["rank", "medal"])
    async def mmr(self, ctx: Context) -> None:
        """Show streamer's mmr on the current account."""
        friend_id = await self.get_friend_id(ctx.broadcaster.id)
        profile_card = await self.local_api.get_profile_card(friend_id)
        await ctx.send(profile_card.rank_display_name)

    @commands.command(aliases=["stratz", "opendota"])
    async def dotabuff(self, ctx: Context) -> None:
        """Show stats service profile link for the streamer, i.e. dotabuff / stratz / opendota."""
        friend_id = await self.get_friend_id(ctx.broadcaster.id)
        invoked = (ctx.invoked_with or "stratz").lower()
        await ctx.send(content=f"{invoked}.com/players/{friend_id}")

    @commands.command(aliases=["lastseen"])
    async def status(self, ctx: Context) -> None:
        """Show the steam account the bot has seen you last online on.

        This account is considered to be queried against for the bot's commands.
        """
        streamer = await self.get_friend(ctx.broadcaster.id, is_green_online_required=False)
        query = "SELECT last_seen FROM dota_accounts WHERE friend_id = $1"
        last_seen: dt.datetime = await self.bot.pool.fetchval(query, streamer.id)
        delta = clock.utcnow() - last_seen
        response = (
            f"{streamer.name} id={streamer.id} status={streamer.status} - "
            f"changed to it {clock.human_timedelta(delta, mode='short')} ago "
            "(while being green-online in Dota 2)"
        )
        await ctx.send(response)

    @commands.command()
    async def party(self, ctx: Context) -> None:
        """Show who is in the streamer's party. Notable players get their nicknames."""
        friend = await self.get_friend(ctx.broadcaster.id)

        # the party includes the streamer themselves
        member_ids = [member_id for member_id in friend.party if member_id != friend.id]
        if not member_ids:
            msg = "Streamer is not in a party."
            raise errors.RespondWithError(msg)

        query = "SELECT nickname, friend_id FROM dota_notable_players WHERE friend_id = ANY($1);"
        rows: list[NotablePlayersQueryRow] = await self.bot.pool.fetch(query, member_ids)
        notables = {row["friend_id"]: row["nickname"] for row in rows}

        # `gather` instead of `TaskGroup`, so `RespondWithError` is raised as is, not wrapped into an ExceptionGroup
        users = await asyncio.gather(*(self.local_api.get_steam_user(member_id) for member_id in member_ids))
        party_members = [
            f"{user.name} ({notables[member_id]})" if member_id in notables else user.name
            for member_id, user in zip(member_ids, users, strict=True)
        ]
        await ctx.send(" \N{BULLET} ".join(party_members))

    # --- WIN / LOSS ---------------------------------------------------------------------------------------------------

    async def score_response_helper(self, broadcaster_id: str, stream_started_at: dt.datetime | None = None) -> str:
        """Get !wl commands response."""
        rows: list[ScoreQueryRow] = await self.bot.pool.fetch(
            SCORE_QUERY,
            broadcaster_id,
            local.MatchState.Live,
            stream_started_at,
            GAMING_SESSION_GAP,
        )
        if not rows:
            return "0 W - 0 L"

        # friend_id -> category -> score
        scores: defaultdict[int, defaultdict[local.Category, Score]] = defaultdict(lambda: defaultdict(Score))
        for row in rows:
            category = local.Category.create(row["lobby_type"], row["game_mode"])
            scores[row["friend_id"]][category].record(
                outcome=row["outcome"],
                player_slot=row["player_slot"],
                abandon=row["abandon"],
            )

        summaries = {
            friend_id: SEPARATOR.join(f"{category.name} {score}" for category, score in by_category.items())
            for friend_id, by_category in scores.items()
        }
        if len(summaries) == 1:
            response = next(iter(summaries.values()))
        else:
            # Multiple accounts: make extra queries to know the names of the accounts
            users = await asyncio.gather(*(self.local_api.get_steam_user(friend_id) for friend_id in summaries))
            response = " \N{LARGE PURPLE CIRCLE} ".join(
                f"{user.name}: {summary}" for user, summary in zip(users, summaries.values(), strict=True)
            )

        if stream_started_at is None:
            # rows are ordered newest first, so rows[-1] is the first match of the session
            ago = clock.human_timedelta(clock.utcnow() - rows[-1]["start_time"], mode="short")
            response = f"[Offline, {ago} ago] {response}"
        return response

    @commands.group(aliases=["wl", "winloss"], invoke_fallback=True)
    async def score(self, ctx: Context) -> None:
        """Show streamer's Win - Loss score ratio during the stream."""
        streamer = self.bot.get_streamer(ctx.broadcaster.id)
        response = await self.score_response_helper(
            ctx.broadcaster.id, streamer.started_dt if streamer.online else None
        )
        await ctx.send(content=response)

    @score.command()
    async def offline(self, ctx: Context) -> None:
        """Show streamer's Win - Loss score ratio during their last gaming session.

        Unlike !wl without any argument - this command counts games that were played off stream.
        Note that for both commands a "gaming session" is considered to be broken if there was a 6 hours break between
        their Dota 2 matches.
        """
        response = await self.score_response_helper(ctx.broadcaster.id)
        await ctx.send(content=response)

    # --- MISC ---------------------------------------------------------------------------------------------------------

    @commands.command(name="d2pt")
    async def dota2protracker_hero_page(self, ctx: Context) -> None:
        """Show Dota 2 Pro Tracker page for the currently played hero."""
        friend = await self.get_friend(ctx.broadcaster.id)
        npc_hero_name = friend.raw_rich_presence.get("param2")
        if npc_hero_name is not None:
            hero = Hero.create_from_npc_dota_hero_name(npc_hero_name.removeprefix("#"))
            response = url_parse.quote(f"dota2protracker.com/hero/{hero.display_name}")
        else:
            response = "The streamer has not picked a hero yet."
        await ctx.send(response)

    @commands.is_owner()
    @commands.command(name="raw_rp")
    async def send_raw_rich_presence(self, ctx: Context) -> None:
        """Send current rich presence state to @irene for debugging reasons."""
        friend = await self.get_friend(ctx.broadcaster.id)
        to_send = fmt.codeblock(json.dumps(friend.raw_rich_presence, indent=2), "json")
        await self.bot.spam_webhook.send(content=to_send)
        await ctx.send(content="Done")

    @commands.is_broadcaster()
    @commands.command(name="steam-invite")
    async def steam_invite(self, ctx: Context, friend_id: int) -> None:
        """Accept steam invite.

        Parameters
        ----------
        friend_id
            Your steam account friend id.
            Please send it in steam_32ID format (e.g. for my bot it's 1807243552).
            steam_64ID format (e.g. 76561199767509280) should also work.
        """
        steam_user = await self.local_api.get_accept_invite(friend_id, ctx.broadcaster.id)
        bot_profile_link = f"steamcommunity.com/id/{'irenestest' if self.bot.test else 'irenesbot'}"
        await ctx.send(
            f"Waiting 10 minutes for a friend request from {steam_user.name} ({steam_user.id}) "
            f"Please, add me asap {bot_profile_link}"
        )


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(MMRBot(bot))
