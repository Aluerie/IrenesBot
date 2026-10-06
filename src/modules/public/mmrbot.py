"""MMR Bot.

The name is a homage to old-school famous @9kmmrbot which was a twitch bot for Dota 2 streamers
with various chat commands such as `!np`.

Nowadays, @dotabod is quite popular and feature rich, but I always liked simplicity of @9kmmrbot.
Its author (@Hambergo) is a cool guy too.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import datetime as dt
import logging
import operator
import pprint
import re
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import TYPE_CHECKING, Any, Literal, TypedDict, override
from urllib import parse as url_parse

import steam
from steam.ext.dota2 import GameMode, Hero, LobbyType, MatchOutcome
from twitchio.ext import commands

from config import env
from core import IreContext, IrePublicComponent
from shared import clock, errors, fmt, fuzzy
from shared.dota_apis.steam_web_api import SteamWebAPIClient
from utils import const, guards

if TYPE_CHECKING:
    import aiohttp

    from core import IreBot
    from shared.types_ import steam_web_api as steam_web_api_schemas

    #########################################################################################################################
    # DATABASE QUERIES
    #########################################################################################################################

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

    #########################################################################################################################
    # LOCAL API
    #########################################################################################################################

    type Streamers = dict[str, Streamer]

    class Streamer(TypedDict):
        id: int
        name: str
        is_playing_dota: str
        status: str
        rich_presence: str
        raw_rich_presence: dict[str, str]
        activity: str
        live_match: LiveMatch | None

    class LiveMatch(TypedDict):
        tag: Literal["playing", "spectating", "unsupported"]
        message: str
        ready: bool
        match_id: int
        lobby_type: int | None
        lobby_type_name: str
        game_mode: int | None
        game_mode_name: str
        server_steam_id: int
        players: list[Player]
        started_at: dt.datetime
        average_mmr: str | None
        unavailable: bool

    class Player(TypedDict):
        id: int
        player_slot: int
        color: str
        lifetime_games: int
        medal: str
        hero_id: int
        hero_name: str

    class MinimalMatch(TypedDict):
        id: int
        players: list[MinimalMatchPlayer]
        outcome: int
        lobby_type: int
        game_mode: int
        duration: int
        start_time: str

    class MinimalMatchPlayer(TypedDict):
        id: int
        hero_id: int
        hero_name: str
        kills: int
        deaths: int
        assists: int

    class ProfileCard(TypedDict):
        medal: str

    class User(TypedDict):
        name: str

#########################################################################################################################
# FROM DOTA2BOT
#########################################################################################################################


class PlayingMatchState(IntEnum):
    """Indicates current state for matches."""

    Starting = 1
    Live = 2
    Pending = 3
    Completed = 4


__all__ = ("MMRBot",)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class LocalAPI:
    """Local API provided by my Dota2Bot."""

    BASE_URL = "http://127.0.0.1:8000"

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def _invoke(self, endpoint: str) -> Any:
        async with self.session.get(f"{self.BASE_URL}{endpoint}") as resp:
            return await resp.json()

    async def get_streamers(self) -> Streamers:
        return await self._invoke("/streamers")

    async def get_minimal_match(self, match_id: int) -> MinimalMatch:
        """Get minimal match."""
        return await self._invoke(f"/minimal/{match_id}")

    async def get_user(self, user_id: int) -> User:
        return await self._invoke(f"/user/{user_id}")

    async def get_profile_card(self, friend_id: int) -> ProfileCard:
        """Get profile_card."""
        return await self._invoke(f"/profile_card/{friend_id}")


# /* cSpell:disable */
HERO_ALIASES = {
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


COLOR_ALIASES = {
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
    """Convert command argument provided by user (twitch chatter) into a player_slot in the match.

    Uses fuzzy match to extract the likely match.

    It supports
    * player slot as digits;
    * player colors;
    * hero aliases (which include hero localized names, abbreviations and some common nicknames);

    Returns
    -------
    tuple[Hero, int]
        Matched hero as well as its index in the provided `heroes` list.
        This is because usually when this function is called, the `player slot` is also of a big interest.
    """
    if argument.isnumeric():
        # then the user typed only a number and our life is easy because it is a player slot
        # let's consider users normal: they start enumerating slots from 1 instead of 0.
        index = int(argument) - 1
        if index < 0:
            msg = f'Detected numeric input "{argument}" but player slot cannot be a negative number.'
            raise errors.RespondWithError(msg)

        try:
            hero_names[index]
        except IndexError:
            msg = (
                f"Detected numeric input for player slot #{argument} "
                f"but there are only {len(hero_names)} players in this match."
            )
            raise errors.RespondWithError(msg) from None
        else:
            return index
    # Otherwise - we have to use the fuzzy search
    result: tuple[int | None, str, int] = (None, "", 0)

    # Step 1. Color aliases;
    for player_slot, color_aliases in COLOR_ALIASES.items():
        find = fuzzy.extract_one(argument, color_aliases, scorer=fuzzy.quick_token_sort_ratio, score_cutoff=49)
        if find and find[1] > result[2]:
            try:
                result = (player_slot, color_aliases[0], find[1])
            except ValueError:
                continue

    # Step 2. Hero aliases
    # Sort the hero list so heroes in the match come first (i.e. so "es" alias triggers on a hero in the match first)
    for hero, hero_aliases in sorted(HERO_ALIASES.items(), key=lambda x: x[0] in hero_names, reverse=True):
        find = fuzzy.extract_one(argument, hero_aliases, scorer=fuzzy.quick_token_sort_ratio, score_cutoff=49)
        if find and find[1] > result[2]:
            result = (-1, hero, find[1])

    if result[0] is None:
        msg = 'Sorry, didn\'t understand your query. Try something like "PA / 7 / Phantom Assassin / Blue".'
        raise errors.RespondWithError(msg)
    if result[0] == -1:
        try:
            index = hero_names.index(result[1])
        except ValueError:
            msg = f"Hero {result[1]} is not present in the match."
            raise errors.RespondWithError(msg) from None
        else:
            return index

    return result[0]


class ScoreCategory(Enum):
    """Match categories for !score (!wl !winloss) command.

    The bot will group matches into !wl command by this parameter, i.e. !wl -> "Ranked 3 W - 1 L, Turbo 2 W - 0 L."
    """

    Ranked = 1
    Unranked = 2
    Turbo = 3
    Other = 4

    @classmethod
    def create(cls, lobby_type: int, game_mode: int) -> ScoreCategory:
        """Create !wl command category from `lobby_type` and `game_mode`.

        Dota Matches naturally in API data are described by those attributes.
        This allows categorizing dota matches for !wl command.
        """
        match lobby_type:
            case LobbyType.Ranked:
                return ScoreCategory.Ranked
            case LobbyType.Unranked:
                return ScoreCategory.Turbo if game_mode == GameMode.Turbo else ScoreCategory.Unranked
            case _:
                return ScoreCategory.Other


@dataclass
class Score:
    wins: int
    losses: int
    abandons: int
    pending: int


def is_allowed_to_add_notable() -> Any:
    """Allow !npm add/remove/rename to only be invoked by certain people."""

    def predicate(ctx: IreContext) -> bool:
        # Maybe we will edit this to be some proper dynamic database thing;
        allowed_ids = (const.UserID.Irene, const.UserID.Xas)
        if ctx.chatter.id in allowed_ids:
            return True
        msg = f"You are not allowed to add notable players into the bot's database {const.FFZ.peepoPolice}"
        raise errors.NotAllowedError(msg)

    return commands.guard(predicate)


class MMRBot(IrePublicComponent):
    """MMR Bot."""

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.steam_web_api = SteamWebAPIClient(api_key=env.STEAM_API_KEY, session=bot.session)
        self.local_api = LocalAPI(bot.session)

    #########################################################################################################################
    # COMMON
    #########################################################################################################################

    async def get_streamer(self, broadcaster_id: str, *, is_green_online_required: bool = True) -> Streamer:
        """Find broadcaster's steam friend_id.

        Note that we only return their last-seen account.
        We assume the last-seen account is the one they want to use commands against.
        """
        query = """
            SELECT twitch_id, friend_id
            FROM ttv_dota_accounts
            WHERE twitch_id = $1
            ORDER BY last_seen DESC
            LIMIT 1;
        """
        row = await self.bot.pool.fetchrow(query, broadcaster_id)
        if row is None:
            msg = "There is no steam accounts associated with your twitch channel"
            raise errors.RespondWithError(msg)

        data: Streamers = await self.local_api.get_streamers()
        if not data:
            msg = "Dota2Bot is restarting, please, wait a bit"
            raise errors.RespondWithError(msg)

        streamer = data.get(str(row["friend_id"]))

        if streamer is not None:
            if is_green_online_required and not streamer["is_playing_dota"]:
                msg = "Inactive command \N{BULLET} it requires streamer to be green-online \N{LARGE GREEN CIRCLE} in Dota 2"
                raise errors.RespondWithError(msg)
            return streamer

        msg = "Couldn't find streamer's steam account in my friends uuh"
        raise errors.RespondWithError(msg)

    #########################################################################################################################
    # LIVE GAME
    #########################################################################################################################

    async def get_live_match(self, broadcaster_id: str) -> LiveMatch:
        """Find broadcaster's active match."""
        streamer = await self.get_streamer(broadcaster_id)
        live_match = streamer["live_match"]
        if live_match is None:
            msg = f"No Active Game Found \N{BULLET} Streamer's status: {streamer['status']}"
            raise errors.RespondWithError(msg)
        if live_match["tag"] == "unsupported":
            msg = live_match["message"]
            raise errors.RespondWithError(msg)
        if live_match["unavailable"]:
            msg = "I'm not able to fetch data for this match, sorry."
            raise errors.RespondWithError(msg)
        return live_match

    async def send_with_tag(self, ctx: IreContext, match: LiveMatch, content: str) -> None:
        """Send with tag."""
        prefix = "[Spectating] " if match["tag"] == "spectating" else ""
        await ctx.send(f"{prefix}{content}")

    @commands.command()
    async def server_steam_id(self, ctx: IreContext) -> None:
        """Show server steam id for the match.

        Useful if I want to manually request `GetRealTimeStats`.
        """
        match = await self.get_live_match(ctx.broadcaster.id)
        await ctx.send(content=str(match["server_steam_id"]))

    @commands.command(aliases=["matchid"])
    async def match_id(self, ctx: IreContext) -> None:
        """Show match ID for the current match."""
        match = await self.get_live_match(ctx.broadcaster.id)
        content = str(match["match_id"])
        await self.send_with_tag(ctx, match, content)

    @commands.command(aliases=["gm"])
    async def game_medals(self, ctx: IreContext) -> None:
        """Fetch each player rank medals in the current game."""
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match["players"]:
            content = "No player data yet"
        else:
            response_parts = [
                f"{player['hero_name'] or player['color']} {player['medal'] or '?'}" for player in match["players"]
            ]
            prefix = f"[{avg_mmr}] " if (avg_mmr := match["average_mmr"]) else ""
            content = prefix + " \N{BULLET} ".join(response_parts)
        await self.send_with_tag(ctx, match, content)

    @commands.command()
    async def ranked(self, ctx: IreContext) -> None:
        """Show whether the current game is ranked or not."""
        match = await self.get_live_match(ctx.broadcaster.id)
        if match["lobby_type"] is None or match["game_mode"] is None:
            content = "No lobby data yet."
        else:
            yes_no = "Yes" if match["lobby_type"] == LobbyType.Ranked else "No"
            content = f"{yes_no}, it's {match['lobby_type_name']} ({match['game_mode_name']})"
        await self.send_with_tag(ctx, match, content)

    @commands.command(aliases=["lifetime"])
    async def smurfs(self, ctx: IreContext) -> None:
        """Show amount of total games each player has on their accounts.

        Not really a "smurf detector", but it's quite good initial metric.
        """
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match["players"]:
            content = "No players data yet."
        else:
            response_parts = [
                f"{player['hero_name'] or player['color']} {player['lifetime_games']}"
                for player in sorted(match["players"], key=operator.itemgetter("lifetime_games"))
            ]
            content = "Lifetime Games: " + " \N{BULLET} ".join(response_parts)
        await self.send_with_tag(ctx, match, content)

    @commands.command(name="notable", aliases=["np"])
    async def notable_players(self, ctx: IreContext) -> None:
        """List notable players for the current match."""
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match["players"]:
            content = "No player data yet."
        else:
            query = "SELECT friend_id, nickname FROM ttv_dota_notable_players WHERE friend_id = ANY($1);"
            rows: list[NotablePlayersQueryRow] = await self.bot.pool.fetch(query, [p["id"] for p in match["players"]])
            if not rows:
                content = "No notable players found"
            else:
                nickname_mapping = {row["friend_id"]: row["nickname"] for row in rows}
                response_parts = [
                    f"{nick} as {player['hero_name'] or player['color']}"
                    for player in match["players"]
                    if (nick := nickname_mapping.get(player["id"]))
                ]
                content = " \N{BULLET} ".join(response_parts)
        await self.send_with_tag(ctx, match, content)

    @commands.command(aliases=["player"])
    async def profile(self, ctx: IreContext, *, player_slot_color_or_hero_name: str) -> None:
        """Get a link to player stats profile.

        `argument` can be a hero name, hero alias, player slot or colour.
        """
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match["players"]:
            content = "No player data yet."
        else:
            hero_names = [player["hero_name"] for player in match["players"]]
            player_slot = extract_player_slot(player_slot_color_or_hero_name, hero_names)
            player = match["players"][player_slot]
            content = f"{player['hero_name'] or player['color']} stratz.com/players/{player['id']}"
        await self.send_with_tag(ctx, match, content)

    #########################################################################################################################
    # LIVE GAME THAT REQUIRE REAL TIME STATS
    #########################################################################################################################

    async def get_real_time_stats(self, match: LiveMatch) -> steam_web_api_schemas.RealTimeStats:
        """Get Real time stats."""
        if not match["server_steam_id"]:
            msg = "This match doesn't support real time stats"
            raise errors.RespondWithError(msg)
        if match["lobby_type"] == LobbyType.NewPlayerMode:
            msg = "New Player Mode matches do not support real time stats."
            raise errors.RespondWithError(msg)
        return await self.steam_web_api.get_real_time_stats(match["server_steam_id"])

    @commands.command(aliases=["items", "kda"])
    async def stats(self, ctx: IreContext, *, player_slot_color_or_hero_name: str) -> None:
        """Fetch items and some profile data about a certain player in the game.

        `argument` can be a hero name, hero alias, player slot or colour.
        """
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match["players"]:
            await ctx.send("No player data yet.")
            return

        hero_names = [player["hero_name"] for player in match["players"]]
        player_slot = extract_player_slot(player_slot_color_or_hero_name, hero_names)
        player = match["players"][player_slot]
        stats = await self.get_real_time_stats(match)

        api_player = next(
            iter(p for team in stats["teams"] for p in team["players"] if p["heroid"] == player["hero_id"]), None
        )
        if api_player is None:
            msg = f"Somehow couldn't find the player {player_slot=} with {player['hero_name']} in the game."
            raise errors.SomethingWentWrongError(msg)

        try:
            api_player["items"]
        except KeyError:
            items = "No item data yet"
        else:
            # https://stackoverflow.com/a/35456954/19217368
            query = """
                SELECT item_id, display_name
                FROM dota_constants_items
                JOIN unnest($1::int[]) WITH ORDINALITY t(item_id, ord) USING (item_id)
                ORDER BY t.ord;
            """
            player_items_dict: dict[int, str] = {
                r["item_id"]: r["display_name"] for r in await self.bot.pool.fetch(query, api_player["items"])
            }
            items: str = ", ".join([
                player_items_dict.get(item, "Unknown Item") for item in api_player["items"] if item != -1
            ])
        response_parts = (
            (  # Prefix
                f"{'[2m delay] ' if match['tag'] == 'playing' else ''}"
                f"{api_player['name']} {player['hero_name']} lvl {api_player['level']}"
            ),
            f"NW: {api_player['net_worth']}",  # Net worth
            f"{api_player['kill_count']}/{api_player['death_count']}/{api_player['assists_count']}",  # KDA
            f"CS: {api_player['lh_count']}",  # Last Hits
            items,  # Items
        )
        content = " \N{BULLET} ".join(response_parts)
        await self.send_with_tag(ctx, match, content)

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
    async def lead(self, ctx: IreContext) -> None:
        """Show which team has a gold lead and by how much."""
        match = await self.get_live_match(ctx.broadcaster.id)
        stats = await self.get_real_time_stats(match)
        radiant = stats["teams"][0]
        dire = stats["teams"][1]
        lead = radiant["net_worth"] - dire["net_worth"]
        word = "Radiant" if lead > 0 else "Dire"
        content = (
            f"{'[2m delay] ' if match['tag'] == 'playing' else ''}"
            f"Radiant {radiant['score']} - Dire {dire['score']}: "
            f"{word} is leading by {abs(lead) / 1000:.1f}k"
        )
        await self.send_with_tag(ctx, match, content)

    #########################################################################################################################
    # LAST GAME
    #########################################################################################################################

    async def get_last_game(self, broadcaster_id: str) -> tuple[int, int, MinimalMatch]:
        """Get broadcaster's last played game from the database.

        Returns
        -------
        tuple[int, int, MinimalMatch]
            This tuple consists of `friend_id`, `hero_id` and `last_game` of `MinimalMatch` type because
            both `friend_id` and `hero_id` are useful at identifying the correct player later on.
            If a player has their data private then MinimalMatch will have zero for that player slot `friend_id`
        """
        query = """
            SELECT p.match_id, p.friend_id, p.hero_id
            FROM ttv_dota_matches m
            JOIN ttv_dota_match_players p ON m.match_id = p.match_id
            JOIN ttv_dota_accounts a ON a.friend_id = p.friend_id
            WHERE a.twitch_id = $1
            ORDER BY m.start_time DESC
            LIMIT 1;
        """
        row = await self.bot.pool.fetchrow(query, broadcaster_id)
        if not row:
            msg = "No last game found: streamer hasn't played Dota 2 in the last 2 days"
            raise errors.RespondWithError(msg)
        last_game = await self.local_api.get_minimal_match(row["match_id"])
        return row["friend_id"], row["hero_id"], last_game

    @commands.command(name="played", aliases=["last_game", "lg", "lm"])
    async def played_with(self, ctx: IreContext) -> None:
        """List recurring players from the last game present in the current match."""
        match = await self.get_live_match(ctx.broadcaster.id)
        if not match["players"]:
            await ctx.send("No player data yet.")
            return

        if match["tag"] == "playing":
            friend_id, _, last_game = await self.get_last_game(ctx.broadcaster.id)

            last_game_hero_player_index: dict[int, str] = {p["id"]: p["hero_name"] for p in last_game["players"]}
            last_game_hero_player_index.pop(friend_id, None)  # remove the streamer themselves

            response_parts = [
                f"{player['hero_name'] or player['color']} played as {last_game_played_as}"
                for player in match["players"]
                if (last_game_played_as := last_game_hero_player_index.get(player["id"]))
            ]
            content = (
                " \N{BULLET} ".join(response_parts)
                if response_parts
                else "No players from the last game present in the match"
            )
        else:
            content = 'Only matches streamer is playing in support "!last_game" command usage'
        await ctx.send(content)

    @commands.command(aliases=["pm"])
    async def previous_match(self, ctx: IreContext) -> None:
        """Show summary stats for the previous match."""
        _, hero_id, match = await self.get_last_game(ctx.broadcaster.id)

        slot, player = next(iter((s, p) for s, p in enumerate(match["players"]) if p["hero_id"] == hero_id), (None, None))
        if slot is None or player is None:
            msg = "Somehow can't find streamer's account in their previous match uuh weird"
            raise errors.SomethingWentWrongError(msg)

        is_radiant = slot < 5
        score_category = ScoreCategory.create(match["lobby_type"], match["game_mode"])
        if match["outcome"] >= MatchOutcome.NotScoredPoorNetworkConditions:
            outcome = "Not Scored"
        elif match["outcome"] == MatchOutcome.RadiantVictory:
            outcome = "Win" if is_radiant else "Loss"
        elif match["outcome"] == MatchOutcome.DireVictory:
            outcome = "Loss" if is_radiant else "Win"
        else:
            outcome = "Unknown outcome"

        delta = clock.utcnow() - (dt.datetime.fromisoformat(match["start_time"]) + dt.timedelta(seconds=match["duration"]))

        response = (
            f"Last Game - {score_category.name}: {outcome} as "
            f"{player['hero_name']} {player['kills']}/{player['deaths']}/{player['assists']} "
            f"\N{BULLET} ended {clock.human_timedelta(delta, mode='short')} ago "
            f"\N{BULLET} stratz.com/matches/{match['id']}"
        )
        await ctx.send(response)

    #########################################################################################################################
    # NOTABLE PEOPLE MANAGEMENT
    #########################################################################################################################

    async def get_id_convert(self, argument: str) -> int:
        """Get minimal match."""
        async with self.bot.session.get(f"http://127.0.0.1:8000/convert/{argument}") as resp:
            try:
                data = (await resp.json())["id"]
            except KeyError:
                msg = "Unsupported input - please use friend id / steam64 id format"
                raise errors.RespondWithError(msg) from None
            else:
                if data is None:
                    msg = "Could not parse steam id from the input"
                    raise errors.RespondWithError(msg)
                return data

    @is_allowed_to_add_notable()
    @guards.is_vps()
    @commands.group(name="npm", aliases=["np-dev"], invoke_fallback=True)
    async def npm_dev(self, ctx: IreContext) -> None:
        """Group command for the bot developer to manage list of notable players in the database."""
        message = (
            '"!npm" is a group command: use it together with its subcommands (add, help, remove, find), "'
            '"i.e. "!npm add 123 Arteezy"'
        )
        await ctx.send(message)

    @npm_dev.command(name="add", aliases=["edit", "rename"])
    async def npm_dev_add(self, ctx: IreContext, argument: str, *, name: str) -> None:
        """Add a notable player to the database.

        This command is only available for certain group of people.
        Since if the player already exists - it will just replace the entry - this command
        also works as `!npm rename` just fine (we don't need to raise anything)
        """
        steam_id = await self.get_id_convert(argument)
        query = """
            INSERT INTO ttv_dota_notable_players
            (friend_id, nickname)
            VALUES ($1, $2)
            ON CONFLICT (friend_id) DO
                UPDATE SET nickname = $2;
        """
        await self.bot.pool.execute(query, steam_id, name)
        await ctx.send(f"Added/edited a notable player <friend_id={steam_id}, name={name}>")

    @npm_dev.command(name="help")
    async def npm_dev_help(self, ctx: IreContext) -> None:
        """Show small help for !np-dev commands."""
        response = (
            "!npm add 123 Arteezy \N{BULLET} "
            "!npm remove 123 \N{BULLET} "
            "!npm rename 123 \N{BULLET} "
            "where 123 is their friend_id; "
            "!npm find Arteezy - to get their friend_id."
        )
        await ctx.send(response)

    @npm_dev.command(name="remove")
    async def npm_dev_remove(self, ctx: IreContext, friend_id: int) -> None:
        """Add a notable player to the database.

        This command is only available for certain group of people.
        """
        query = """
            DELETE FROM ttv_dota_notable_players
            WHERE friend_id = $1
            RETURNING nickname;
        """
        name: str = await self.bot.pool.fetchval(query, friend_id)
        await ctx.send(f"Removed player <friend_id={friend_id}, name={name}> from notable players.")

    @npm_dev.command(name="find")
    async def npm_dev_find(self, ctx: IreContext, *, name: str) -> None:
        """Find a notable player from the database.

        This command is only available for certain group of people.
        """
        query = """
            SELECT friend_id, nickname
            FROM ttv_dota_notable_players
            ORDER BY similarity(nickname, $1) DESC
            LIMIT 3;
        """
        rows = await self.bot.pool.fetch(query, name)
        response = f'3 most similar entries "{name}": ' + " \N{BULLET} ".join(
            f"{row['nickname']} id={row['friend_id']}" for row in rows
        )
        await ctx.send(response)

    #########################################################################################################################
    # MMR
    #########################################################################################################################

    @commands.group(invoke_fallback=True)
    async def mmr(self, ctx: IreContext) -> None:
        """Show streamer's mmr on the current account."""
        streamer: Streamer = await self.get_streamer(ctx.broadcaster.id, is_green_online_required=False)
        query = "SELECT estimated_mmr FROM ttv_dota_accounts WHERE friend_id = $1;"
        mmr: int = await self.bot.pool.fetchval(query, streamer["id"])

        profile_card = await self.local_api.get_profile_card(streamer["id"])
        response = f"Medal: {profile_card['medal']} \N{BULLET} Database tracked MMR: {mmr}"
        await ctx.send(response)

    @commands.is_broadcaster()
    @mmr.command(name="set")
    async def mmr_set(self, ctx: IreContext, new_mmr: int) -> None:
        """Set streamer's mmr in the database."""
        streamer = await self.get_streamer(ctx.broadcaster.id, is_green_online_required=False)
        query = "UPDATE ttv_dota_accounts SET estimated_mmr = $1 WHERE friend_id = $2;"
        await self.bot.pool.fetchval(query, new_mmr, streamer["id"])
        response = f'Successfully set MMR to {new_mmr} for the account "{streamer["name"]}"'
        await ctx.send(response)

    #########################################################################################################################
    # PROFILE
    #########################################################################################################################

    @commands.command(aliases=["stratz", "opendota"])
    async def dotabuff(self, ctx: IreContext) -> None:
        """Show stats service profile link for the streamer, i.e. dotabuff / stratz / opendota."""
        streamer = await self.get_streamer(ctx.broadcaster.id, is_green_online_required=False)
        if not (invoked := ctx.invoked_with):
            invoked = "stratz"
        await ctx.send(content=f"{invoked}.com/players/{streamer['id']}")

    @commands.command(aliases=["lastseen"])
    async def status(self, ctx: IreContext) -> None:
        """Show the steam account the bot has seen you last online on.

        This account is considered to be queried against for the bot's commands.
        """
        streamer = await self.get_streamer(ctx.broadcaster.id, is_green_online_required=False)
        query = "SELECT last_seen FROM ttv_dota_accounts WHERE friend_id = $1"
        last_seen: dt.datetime = await self.bot.pool.fetchval(query, streamer["id"])
        delta = clock.utcnow() - last_seen
        response = (
            f"{streamer['name']} id={streamer['id']} status={streamer['status']} - "
            f"changed to it {clock.human_timedelta(delta, mode='short')} ago "
            "(while being green-online in Dota 2)"
        )
        await ctx.send(response)

    @commands.command()
    async def party(self, ctx: IreContext) -> None:
        """Show notable players in the current party."""
        streamer = await self.get_streamer(ctx.broadcaster.id)
        party = streamer["raw_rich_presence"].get("party")
        if party is None:
            msg = "Streamer is not in a party."
            raise errors.RespondWithError(msg)
        if party2 := streamer["raw_rich_presence"].get("party2"):
            # Apparently if a party is too big, valve just slice the string into party2
            party += party2

        # Mapping steam32_id -> [steam64_id, their supposed account name]
        # v[0]: int - steam64
        # v[1]: str - notable name
        party_member_pattern = re.compile(r"members\s{\ssteam_id:\s([0-9]+)")
        members: dict[int, list[Any]] = {m.id: [m.id64, ""] for m in map(steam.ID, party_member_pattern.findall(party))}
        if not members:
            msg = "Streamer is not in a party."
            raise errors.RespondWithError(msg)

        query = "SELECT nickname, friend_id FROM ttv_dota_notable_players WHERE friend_id = ANY($1);"
        rows = await self.bot.pool.fetch(query, members.keys())
        for row in rows:
            members[row["friend_id"]][1] = row["nickname"]

        response = ""
        if rows:
            known_party_members = " \N{BULLET} ".join(v[1] for v in members.values() if v[1])
            response += known_party_members

        unknown_party_members = " \N{BULLET} ".join([
            f"{(await self.local_api.get_user(v[0]))['name']} ({k})" for k, v in members.items() if not v[1]
        ])
        if unknown_party_members:
            response += f". And not notable to the bot: {unknown_party_members}"
        # else:
        #     # zero known members
        #     response = f"Party members IDs: {unknown_party_members}"
        await ctx.send(response)

    async def score_response_helper(self, broadcaster_id: str, stream_started_at: dt.datetime | None = None) -> str:
        """Get !wl commands response."""
        clause = "AND m.start_time > $3" if stream_started_at else ""
        query = f"""
            SELECT d.friend_id, m.start_time, m.lobby_type, m.game_mode, m.outcome, p.player_slot, p.abandon
            FROM ttv_dota_matches m
            JOIN ttv_dota_match_players p ON m.match_id = p.match_id
            JOIN ttv_dota_accounts d ON d.friend_id = p.friend_id
            WHERE d.twitch_id = $1 AND m.live > $2 {clause}
            ORDER BY m.start_time DESC;
        """  # ruff: ignore[hardcoded-sql-expression]
        rows: list[ScoreQueryRow] = (
            await self.bot.pool.fetch(query, broadcaster_id, PlayingMatchState.Live, stream_started_at)
            if stream_started_at
            else await self.bot.pool.fetch(query, broadcaster_id, PlayingMatchState.Live)
        )

        if not rows:
            return "0 W - 0 L" if stream_started_at else "0 W - 0 L (No games played in the last 2 days)"

        index: dict[int, dict[ScoreCategory, Score]] = {}

        cutoff_dt = rows[0]["start_time"]
        for row in rows:
            # Let's assume gaming sessions to be separated by 6 hours from each other;
            if row["start_time"] < cutoff_dt - dt.timedelta(hours=6):
                gaming_session_dt = cutoff_dt
                break
            cutoff_dt = row["start_time"]

            score_category = ScoreCategory.create(row["lobby_type"], row["game_mode"])
            score = index.setdefault(row["friend_id"], {}).setdefault(score_category, Score(0, 0, 0, 0))

            if row["abandon"]:
                score.abandons += 1
            elif row["outcome"] is None:
                score.pending += 1
            elif row["outcome"] == MatchOutcome.RadiantVictory:
                if row["player_slot"] < 5:
                    score.wins += 1
                else:
                    score.losses += 1
            elif row["outcome"] == MatchOutcome.DireVictory:
                if row["player_slot"] > 4:
                    score.wins += 1
                else:
                    score.losses += 1
        else:
            gaming_session_dt = rows[-1]["start_time"]

        def format_results(score: Score) -> str:
            wl = f"{score.wins} W - {score.losses} L"
            if a := score.abandons:
                wl += f", Abandons: {a}"
            if p := score.pending:
                wl += f", Pending: {p}"
            return wl

        response_parts = {
            friend_id: " \N{BULLET} ".join(
                f"{category.name} {format_results(results)}" for category, results in scores.items()
            )
            for friend_id, scores in index.items()
        }

        response = " \N{LARGE PURPLE CIRCLE} ".join(
            # Let's make extra query to know name accounts
            [f"{(await self.local_api.get_user(friend_id))['name']}: {part}" for friend_id, part in response_parts.items()]
        )
        if not stream_started_at:
            timedelta = clock.utcnow() - gaming_session_dt
            response = (
                "[Offline WL for the last gaming session that started "
                f"{clock.human_timedelta(timedelta, mode='short')} ago] {response}"
            )
        return response

    @commands.group(aliases=["wl", "winloss"], invoke_fallback=True)
    async def score(self, ctx: IreContext) -> None:
        """Show streamer's Win - Loss score ratio during the stream."""
        streamer = self.bot.streamers[ctx.broadcaster.id]
        if not streamer.online:
            response = await self.score_response_helper(ctx.broadcaster.id)
        else:
            response = await self.score_response_helper(ctx.broadcaster.id, streamer.started_dt)
        await ctx.send(content=response)

    @score.command()
    async def offline(self, ctx: IreContext) -> None:
        """Show streamer's Win - Loss score ratio during their last gaming session.

        Unlike !wl without any argument - this command counts games that were played off stream.
        Note that for both commands a "gaming session" is considered to be broken if there was a 6 hours break between
        their Dota 2 matches.
        """
        response = await self.score_response_helper(ctx.broadcaster.id)
        await ctx.send(content=response)

    @commands.command(name="d2pt")
    async def dota2protracker_hero_page(self, ctx: IreContext) -> None:
        """Show Dota 2 Pro Tracker page for the currently played hero."""
        streamer = await self.get_streamer(ctx.broadcaster.id)
        npc_hero_name = streamer["raw_rich_presence"].get("param2")
        if npc_hero_name:
            hero = Hero.create_from_npc_dota_hero_name(npc_hero_name.removeprefix("#"))
            response = url_parse.quote(f"dota2protracker.com/hero/{hero.display_name}")
        else:
            response = "The streamer has not picked a hero yet."
        await ctx.send(response)

    @commands.is_owner()
    @commands.command(name="raw_rp")
    async def send_raw_rich_presence(self, ctx: IreContext) -> None:
        """Send current rich presence state to @irene for debugging reasons."""
        friend = await self.get_streamer(ctx.broadcaster.id)
        to_send = fmt.codeblock(pprint.pformat(friend["raw_rich_presence"]), "json")
        await self.bot.error_webhook.send(content=to_send)
        await ctx.send(content="Done")

    #########################################################################################################################
    # LAST TOUCH
    #########################################################################################################################

    @override
    async def component_command_error(self, payload: commands.CommandErrorPayload) -> bool | None:
        """Event called when an error occurs in a command in this Component."""
        if isinstance(payload.exception, errors.ApiError):
            msg = "I'm not able to fetch data for this match, sorry!"
            await payload.context.send(msg)
            return False
        return None


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(MMRBot(bot))
