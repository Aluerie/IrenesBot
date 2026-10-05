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
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, TypedDict, override

from steam.ext.dota2 import GameMode, LobbyType, MatchOutcome
from twitchio.ext import commands

from config import env
from core import IreContext, IrePublicComponent
from shared import clock, errors, fuzzy
from shared.dota_apis.steam_web_api import SteamWebAPIClient
from utils import const, guards

if TYPE_CHECKING:
    from core import IreBot

    type IndexResponse = dict[str, Streamer]

    class Streamer(TypedDict):
        is_playing_dota: str
        rich_presence: str
        activity: str
        live_match: LiveMatch | None

    class LiveMatch(TypedDict):
        tag: Literal["playing", "spectating"]
        ready: bool
        match_id: int
        lobby_type: int | None
        lobby_type_name: str
        game_mode: int | None
        game_mode_name: str
        server_steam_id: int
        players: list[Player]
        heroes: list[int]
        hero_names: list[str]
        started_at: dt.datetime
        average_mmr: str | None

    class Player(TypedDict):
        friend_id: int
        player_slot: int
        color: str
        lifetime_games: int
        medal: str

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


__all__ = ("MMRBot",)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


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

        async with self.bot.session.get("http://127.0.0.1:8000/streamers") as resp:
            data: IndexResponse = await resp.json()
            streamer = data.get(str(row["friend_id"]))

        if streamer:
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
            msg = f"No Active Game Found \N{BULLET} Streamer's status: {streamer['rich_presence']}"
            raise errors.RespondWithError(msg)
        return live_match

    async def send_with_tag(self, ctx: IreContext, match: LiveMatch, content: str) -> None:
        """Send with tag."""
        prefix = "[Spectating] " if match["tag"] == "spectating" else ""
        await ctx.send(f"{prefix}{content}")

    @commands.command(aliases=["gm"])
    async def game_medals(self, ctx: IreContext) -> None:
        """Fetch each player rank medals in the current game."""
        match = await self.get_live_match(ctx.broadcaster.id)
        response_parts = [
            f"{hero_name if hero_name != 'NONE' else player['color']} {player['medal'] or '?'}"
            for player, hero_name in zip(match["players"], match["hero_names"], strict=True)
        ]
        prefix = f"[{avg_mmr}] " if (avg_mmr := match["average_mmr"]) else ""
        content = prefix + " \N{BULLET} ".join(response_parts) if response_parts else "No player data yet"
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
                f"{hero_name or player['color']} {player['lifetime_games']}"
                for player, hero_name in sorted(
                    zip(match["players"], match["hero_names"], strict=True),
                    key=lambda x: x[0]["lifetime_games"],
                )
            ]
            content = "Lifetime Games: " + " \N{BULLET} ".join(response_parts)
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
            player_slot = extract_player_slot(player_slot_color_or_hero_name, match["hero_names"])
            player = match["players"][player_slot]
            hero_name = match["hero_names"][player_slot]
            content = f"{hero_name if hero_name != 'NONE' else player['color']} stratz.com/players/{player['friend_id']}"
        await ctx.send(content)

    @commands.command(aliases=["items", "kda"])
    async def stats(self, ctx: IreContext, *, player_slot_color_or_hero_name: str) -> None:
        """Fetch items and some profile data about a certain player in the game.

        `argument` can be a hero name, hero alias, player slot or colour.
        """
        match = await self.get_live_match(ctx.broadcaster.id)

        if not match["players"]:
            await ctx.send("No player data yet.")
            return
        if not match["server_steam_id"]:
            await ctx.send("This match doesn't support real time stats")
        if match["lobby_type"] == LobbyType.NewPlayerMode:
            await ctx.send("New Player Mode matches do not support real time stats.")
            return

        player_slot = extract_player_slot(player_slot_color_or_hero_name, match["hero_names"])
        # player = list(match["players"].values())[player_slot]
        hero_id = match["heroes"][player_slot]
        hero_name = match["heroes"][player_slot]

        stats = await self.steam_web_api.get_real_time_stats(match["server_steam_id"])

        # We have to loop through teams in order to support Custom and Event Games
        # Since the amount of players in the team can be variable.
        for team in stats["teams"]:
            for p in team["players"]:
                if p["heroid"] == hero_id:
                    api_player = p
                    break
            else:
                continue
            break
        else:
            msg = f"Somehow couldn't find the player {player_slot=} with {hero_name} in the game."
            raise errors.SomethingWentWrongError(msg)

        prefix = (
            f"{'[2m delay] ' if match['tag'] == 'playing' else ''}{api_player['name']} {hero_name} lvl {api_player['level']}"
        )
        net_worth = f"NW: {api_player['net_worth']}"
        kda = f"{api_player['kill_count']}/{api_player['death_count']}/{api_player['assists_count']}"
        cs = f"CS: {api_player['lh_count']}"

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
        response_parts = (prefix, net_worth, kda, cs, items)
        await ctx.send(" \N{BULLET} ".join(response_parts))

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
    async def server_steam_id(self, ctx: IreContext) -> None:
        """Show server steam id for the match.

        Useful if I want to manually request `GetRealTimeStats`.
        """
        match = await self.get_live_match(ctx.broadcaster.id)
        await ctx.send(content=str(match["server_steam_id"]))

    #########################################################################################################################
    # LAST GAME
    #########################################################################################################################

    async def get_minimal_match(self, match_id: int) -> MinimalMatch:
        """Get minimal match."""
        async with self.bot.session.get(f"http://127.0.0.1:8000/minimal/{match_id}") as resp:
            return await resp.json()

    async def get_last_game(self, broadcaster_id: str) -> tuple[int, int, MinimalMatch]:
        """Fet broadcaster's last played game from the database.

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
        last_game = await self.get_minimal_match(row["match_id"])
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
                f"{hero or player['color']} played as {last_game_played_as}"
                for player, hero in zip(match["players"], match["heroes"], strict=True)
                if (last_game_played_as := last_game_hero_player_index.get(player["friend_id"]))
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
        if not slot or not player:
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

    async def get_steam_id(self, argument: str) -> int | None:
        """Get minimal match."""
        async with self.bot.session.get(f"http://127.0.0.1:8000/minimal/{argument}") as resp:
            return (await resp.json())["id"]

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
        steam_id = await self.get_steam_id(argument)
        if steam_id is None:
            await ctx.send("Could not parse steam id from the input")
            return
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
        response = f'3 most similar entries "{name}": ' + " \N{BULLET}".join(
            f"{row['nickname']} id={row['friend_id']}" for row in rows
        )
        await ctx.send(response)

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
