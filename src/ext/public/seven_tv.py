"""Seven TV Public Features.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal, TypedDict, override

import twitchio
from twitchio.ext import commands

from core import DevComponent, PublicComponent
from shared import clock, errors, globs, ut
from shared.apis.stv import EmoteNotFoundError, PartialEmote, PartialEmoteSet, StvGraphQLClient, UnsatisfyingResultError
from shared.concepts import PrefixLoggerAdapter, loop
from utils import const, guards

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from core import Bot, Context

    #########################################################################################################################
    # DATABASE QUERY ROW TYPE-HINTS
    #########################################################################################################################

    class ValidateIsEmoteBlacklistedQueryRow(TypedDict):
        emote_id: str
        blacklisted_at: dt.datetime
        duration: int
        remove_only: bool

    class CycleStatusQueryRow(TypedDict):
        reward_id: str
        emote_limit: int
        emote_count: int
        emote_set_id: str


__all__ = (
    "SevenTVDevOnly",
    "SevenTVPublic",
)

log = PrefixLoggerAdapter(logging.getLogger(__name__), "🤯")
log.setLevel(logging.DEBUG)


#############################################################################################################################
# CONSTANTS AND ENUMS
#############################################################################################################################


@dataclass
class Reward:
    code: Literal["blacklist", "permanent", "cycle"]
    name: str
    table: str
    processor: Callable[[twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption], Awaitable[Any]]
    cache: set[str] = field(default_factory=set)


class OwnershipEnum(StrEnum):
    """Emote ownership enum."""

    broadcaster_dev_or_editor = "broadcaster_dev_or_editor"
    chatter = "chatter"


# fmt: off
"""
Common Words
------------
* taken and edited from https://github.com/FrankerFaceZ/Add-Ons/blob/master/src/no-bad-emotes/common.json
* Removed: boat
* Added: color
* You can use ``pprint`` to print the list in a shortened way:

.. code-block:: alpha.py

    import pprint
    from ext.public.seven_tv import COMMON_WORDS
    pprint.pprint(tuple(COMMON_WORDS), width=120, compact=True)
"""
COMMON_WORDS = frozenset((
'weigh', 'instead', 'cover', 'five', 'politic', 'telephone', 'real', 'otherwise', 'pain', 'rather', 'waste', 'do',
 'once', 'near', 'die', 'ought', 'serious', 'percent', 'unless', 'wash', 'collect', 'rid', 'video', 'scared', 'car',
 'parent', 'believe', 'old', 'operate', 'pass', 'smoke', 'warm', 'want', 'first', 'east', 'test', 'lead', 'so', 'thing',
 'mother', 'village', 'home', 'suit', 'city', 'hand', 'score', 'see', 'employ', 'enjoy', 'achieve', 'hello', 'welcome',
 'each', 'over', 'yellow', 'clean', 'case', 'blue', 'already', 'idiot', 'leg', 'lord', 'ant', 'doubt', 'hour', 'enter',
 'every', 'present', 'beat', 'round', 'letter', 'sneak', 'run', 'result', 'than', 'contact', 'spell', 'start', 'bed',
 'horse', 'window', 'although', 'america', 'grant', 'long', 'say', 'set', 'quality', 'number', 'drop', 'chair', 'ten',
 'evening', 'orange', 'sign', 'wonder', 'authority', 'side', 'ground', 'thank', 'intro', 'bottom', 'maybe', 'receive',
 'motion', 'refer', 'why', 'bother', 'honest', 'price', 'community', 'mile', 'ring', 'sit', 'guess', 'money', 'note',
 'thirty', 'trouble', 'admit', 'match', 'affect', 'paper', 'safe', 'positive', 'report', 'into', 'new', 'drive',
 'fortune', 'hi', 'continue', 'if', 'street', 'friday', 'either', 'invest', 'eleven', 'lunch', 'big', 'recent', 'make',
 'involve', 'sale', 'usual', 'surprise', 'tonight', 'be', 'sex', 'end', 'therefore', 'commit', 'draw', 'because',
 'meow', 'put', 'simple', 'twelve', 'bank', 'dad', 'consult', 'throw', 'budget', 'one', 'then', 'choice', 'out', 'or',
 'fun', 'value', 'argue', 'attend', 'behind', 'child', 'definite', 'mention', 'sleep', 'question', 'improve', 'favour',
 'moderator', 'dog', 'wait', 'voices', 'sister', 'waiting', 'reduce', 'cheap', 'light', 'flat', 'game', 'decision',
 'laugh', 'agree', 'minister', 'matter', 'during', 'to', 'europe', 'exist', 'relation', 'cross', 'process', 'time',
 'heavy', 'radio', 'check', 'hell', 'mitosis', 'remember', 'visit', 'join', 'aware', 'yet', 'proper', 'role',
 'function', 'away', 'paint', 'quick', 'paragraph', 'sheet', 'sneaking', 'farm', 'far', 'whether', 'off', 'scotland',
 'trade', 'necessary', 'document', 'agent', 'quite', 'walking', 'find', 'appropriate', 'environment', 'lose', 'need',
 'bill', 'should', 'week', 'air', 'voice', 'shall', 'meaning', 'non', 'reacting', 'own', 'history', 'maw',
 'responsible', 'early', 'ago', 'limit', 'black', 'pretty', 'low', 'order', 'tea', 'beauty', 'business', 'grand',
 'none', 'staff', 'advertise', 'classic', 'form', 'wife', 'current', 'couple', 'pull', 'structure', 'morning', 'actual',
 'feed', 'comment', 'else', 'road', 'since', 'two', 'flash', 'vote', 'proceed', 'stay', 'extra', 'catch', 'union',
 'great', 'may', 'mark', 'hit', 'clear', 'sick', 'today', 'term', 'secretary', 'town', 'friend', 'evidence', 'bottle',
 'father', 'propose', 'poor', 'brother', 'deal', 'middle', 'call', 'stupid', 'protect', 'per', 'park', 'shoe',
 'suggest', 'company', 'pack', 'regard', 'seat', 'little', 'resource', 'think', 'must', 'hair', 'science', 'cake',
 'any', 'fall', 'doctor', 'space', 'flirt', 'sound', 'degree', 'left', 'alright', 'moment', 'with', 'plus', 'shop',
 'down', 'brief', 'card', 'general', 'buy', 'man', 'mind', 'save', 'supply', 'reason', 'project', 'full', 'count',
 'dress', 'wee', 'day', 'switch', 'word', 'gas', 'quid', 'level', 'person', 'look', 'inform', 'mod', 'glass', 'girl',
 'class', 'act', 'night', 'settle', 'conch', 'worse', 'equal', 'move', 'print', 'world', 'could', 'depend', 'large',
 'as', 'listening', 'load', 'tree', 'strong', 'listen', 'bad', 'ever', 'sense', 'heart', 'germany', 'television',
 'policy', 'change', 'wide', 'blood', 'angry', 'church', 'except', 'wall', 'ok', 'way', 'post', 'flashback', 'base',
 'university', 'very', 'wow', 'share', 'for', 'fight', 'learn', 'react', 'about', 'power', 'rate', 'effect', 'benefit',
 'news', 'send', 'type', 'allow', 'teach', 'bear', 'talk', 'tape', 'door', 'yes', 'life', 'separate', 'sing', 'water',
 'nation', 'come', 'include', 'princess', 'break', 'white', 'it', 'kid', 'study', 'subject', 'realize', 'part', 'small',
 'million', 'figure', 'key', 'original', 'jesus', 'even', 'team', 'without', 'picture', 'cut', 'still', 'up', 'common',
 'elect', 'mean', 'explain', 'prince', 'issue', 'situate', 'toward', 'high', 'sorry', 'difficult', 'minute', 'pence',
 'centre', 'happy', 'hard', 'color', 'tomorrow', 'lot', 'binoculars', 'second', 'available', 'transport', 'until',
 'bus', 'six', 'might', 'three', 'not', 'apply', 'meet', 'social', 'represent', 'income', 'easy', 'young', 'expect',
 'last', 'amount', 'local', 'fact', 'cat', 'oppose', 'district', 'due', 'hospital', 'absolute', 'ball', 'antenna',
 'hundred', 'idea', 'across', 'educate', 'forward', 'introduce', 'nice', 'too', 'against', 'department', 'face',
 'consider', 'board', 'region', 'insure', 'spend', 'step', 'can', 'increase', 'hear', 'hullo', 'marry', 'section',
 'special', 'try', 'machine', 'presume', 'add', 'table', 'exact', 'future', 'music', 'fish', 'okay', 'private', 'raise',
 'woman', 'year', 'right', 'walk', 'dinner', 'school', 'film', 'labour', 'just', 'fire', 'range', 'sun', 'really',
 'discuss', 'late', 'trust', 'four', 'half', 'other', 'lie', 'force', 'dear', 'best', 'month', 'unite', 'watching',
 'apart', 'associate', 'bar', 'boy', 'such', 'art', 'balance', 'begin', 'self', 'electric', 'nature', 'corner',
 'quarter', 'vibe', 'client', 'rail', 'short', 'together', 'important', 'baby', 'occasion', 'detail', 'free', 'south',
 'recording', 'follow', 'london', 'tax', 'luck', 'much', 'ask', 'eye', 'well', 'help', 'build', 'wood', 'choose',
 'modding', 'problem', 'thirteen', 'total', 'pardon', 'by', 'chap', 'english', 'fly', 'care', 'keep', 'back', 'product',
 'warning', 'answer', 'service', 'correct', 'character', 'place', 'charge', 'stuff', 'bet', 'jump', 'imagine', 'read',
 'grow', 'thou', 'upon', 'engine', 'suppose', 'a', 'tell', 'shut', 'show', 'scare', 'normal', 'express', 'govern',
 'fit', 'bag', 'fast', 'quiet', 'member', 'christ', 'fill', 'club', 'give', 'job', 'hack', 'rest', 'some', 'worry',
 'group', 'wage', 'press', 'court', 'support', 'concern', 'egg', 'divide', 'appear', 'people', 'god', 'identify',
 'here', 'compare', 'size', 'perfect', 'britain', 'opportunity', 'stairs', 'touch', 'few', 'arm', 'country', 'plan',
 'committee', 'on', 'watch', 'thursday', 'disbelief', 'account', 'industry', 'let', 'wish', 'blow', 'main', 'seem',
 'turn', 'unit', 'create', 'bloke', 'open', 'have', 'please', 'tie', 'practise', 'probable', 'work', 'summer',
 'research', 'same', 'along', 'sell', 'copy', 'terrible', 'west', 'lay', 'more', 'chicken', 'mrs', 'you', 'lady',
 'assume', 'major', 'finish', 'recognize', 'soon', 'various', 'cook', 'kind', 'practice', 'nine', 'stop', 'shoot',
 'warn', 'county', 'reckon', 'awful', 'knock', 'good', 'yesterday', 'before', 'red', 'chance', 'slow', 'tuesday', 'law',
 'past', 'sure', 'body', 'woof', 'hall', 'file', 'student', 'condition', 'and', 'complete', 'would', 'house', 'almost',
 'odd', 'treat', 'now', 'date', 'pick', 'minus', 'they', 'birth', 'another', 'list', 'whole', 'family', 'many',
 'record', 'will', 'love', 'sir', 'regret', 'age', 'exquisite', 'chairman', 'within', 'compute', 'able', 'food',
 'scheme', 'heat', 'photograph', 'clothe', 'garden', 'point', 'kitchen', 'speak', 'strike', 'at', 'eight', 'name',
 'next', 'danger', 'colour', 'final', 'often', 'what', 'get', 'most', 'arrange', 'all', 'feel', 'never', 'take',
 'under', 'he', 'drink', 'book', 'notes', 'previous', 'lad', 'tend', 'active', 'contract', 'travel', 'claim', 'expense',
 'sudden', 'vibing', 'goodbye', 'dry', 'sunday', 'leave', 'interest', 'hacking', 'ready', 'wear', 'system', 'line',
 'decide', 'society', 'design', 'happen', 'become', 'field', 'describe', 'how', 'dead', 'stage', 'pair', 'secure',
 'standard', 'state', 'fine', 'son', 'twenty', 'pay', 'converse', 'go', 'timeout', 'individual', 'period', 'hot',
 'wind', 'enough', 'indeed', 'straight', 'husband', 'develop', 'sort', 'clock', 'stand', 'christmas', 'offer', 'afford',
 'play', 'observing', 'prepare', 'item', 'measure', 'through', 'programme', 'war', 'respect', 'return', 'appoint',
 'always', 'double', 'cause', 'moderators', 'difference', 'closes', 'who', 'less', 'finance', 'there', 'only', 'of',
 'cent', 'purpose', 'realise', 'apparent', 'story', 'bit', 'busy', 'though', 'while', 'cost', 'however', 'slight',
 'speed', 'page', 'use', 'stick', 'push', 'win', 'around', 'confer', 'obvious', 'where', 'land', 'hang', 'view',
 'inside', 'miss', 'piece', 'kill', 'seven', 'train', 'which', 'mister', 'north', 'france', 'like', 'colleague',
 'holiday', 'top', 'accept', 'single', 'milk', 'council', 'particular', 'true', 'mods', 'cup', 'address', 'king',
 'likely', 'both', 'require', 'she', 'market', 'rule', 'wednesday', 'write', 'organize', 'area', 'experience',
 'succeed', 'understand', 'this', 'further', 'hope', 'encourage', 'economy', 'exercise', 'similar', 'fund', 'example',
 'gaze', 'health', 'guy', 'from', 'head', 'language', 'monday', 'saturday', 'also', 'basis', 'position', 'hate', 'roll',
 'site', 'cold', 'foot', 'bring', 'floor', 'possible', 'direct', 'pound', 'college', 'when', 'deep', 'manage', 'judge',
 'office', 'between', 'station', 'traffic', 'we', 'no', 'hold', 'forget', 'room', 'fair', 'lock', 'perhaps', 'link',
 'pressure', 'produce', 'course', 'serve', 'know', 'strategy', 'brilliant', 'provide', 'bye', 'after', 'the', 'panic',
 'approach', 'eat', 'close', 'control', 'notice', 'excuse', 'again', 'certain', 'live', 'party', 'thousand', 'wrong',
 'but', 'square', 'recommend', 'rise', 'specific', 'yo', 'police', 'public', 'sitting', 'front', 'in', 'especial',
 'box', 'coffee', 'carry', 'green', 'debate', 'worth', 'pension', 'observe', 'fishing', 'afternoon'))
# fmt: on


#############################################################################################################################
# USER INPUT PARSERS
#############################################################################################################################


def regex_to_emote(stv: StvGraphQLClient, emote_id_or_link: str) -> PartialEmote:
    """Convert a string containing 7TV emote id or link to `PartialEmote`.

    Does not do anything if the user input is already an emote_id.
    If no emote_id is provided then it errors out.

    Note
    ----
    The regex in this function is not restrictive for `emote_id_or_link`.
    It allows any strings that contain 7TV ids.

    This way all these are valid:
    * 01GEQCQVM0000B6WHR50T3PTZY
    * 7tv.app/emotes/01GEQCQVM0000B6WHR50T3PTZY
    * https://old.7tv.app/emotes/01GEQCQVM0000B6WHR50T3PTZY
    * https://www.7tv.app/emotes/01GEQCQVM0000B6WHR50T3PTZY
    * https://cdn.7tv.app/emote/01HNK8DGF0000FG935RNS75APG/4x.avif
    * https://7tv.app/emotes/669ea9ca106a10c8be7c621d

    Regex101 playground link: https://regex101.com/r/UYfHD6

    This ignores an extremely rare edge-case where emote's name can match emote_id's regex.

    Raises
    ------
    errors.BadUserInputError
        Could not parse emote id / emote link.
    """
    search = re.search(
        # Valid 7tv ids are
        # * new format - ULID format: [0-7][0-9A-HJKMNP-TV-Z]{25}
        # * old format - MongoDB ObjectID format: [0-9a-fA-F]{24}
        pattern=r"\b(?P<emote_id>[0-7][0-9A-HJKMNP-TV-Z]{25}|[0-9a-fA-F]{24})\b",
        string=emote_id_or_link,
    )
    if search is None:
        msg = "Bad <emote_id_or_link>, check the input"
        raise errors.BadUserInputError(msg)
    return stv.create_partial_emote(search["emote_id"])


async def parse_emote(
    stv: StvGraphQLClient, emote_id_link_or_name: str, broadcaster_id: str | None = None
) -> PartialEmote:
    """Parse or search."""
    try:
        # try parsing `emote_id`
        return regex_to_emote(stv, emote_id_link_or_name)
    except errors.BadUserInputError:
        # `emote_name` was provided to search
        if broadcaster_id is not None:
            # search within the broadcaster
            user = stv.create_partial_user(broadcaster_id)
            return await user.search_emote(emote_id_link_or_name)
        # search top globally
        return await stv.search_emote(emote_id_link_or_name)


async def parse_add_rename_reward_input(
    stv: StvGraphQLClient, user_input: str, broadcaster_id: str | None = None
) -> tuple[PartialEmote, str | None]:
    """Get emote_id from `user_input`.

    Parameters
    ----------
    stv
        SevenTV GraphQL client
    user_input
        User input
    broadcaster_id
        If provided then the 7tv client will search for the emote within the user emotes,
        if not - it will search globally.
    """
    split = user_input.split()
    if len(split) > 2:
        msg = "Bad Input; I require '<emote_link_or_id> <optional_emote_alias>' - no extra words"
        raise errors.BadUserInputError(msg)
    if not split:
        msg = "Bad Input; why would you type an empty text?"
        raise errors.BadUserInputError(msg)

    # Either
    # 2 words - 'emote_id_link_or_name + emote_alias' were provided
    # 1 word - just 'emote_id_link_or_name'
    try:
        emote_alias = split[1]
    except IndexError:
        emote_alias = None

    emote = await parse_emote(stv, split[0], broadcaster_id)
    return (emote, emote_alias)


async def parse_remove_reward_input(stv: StvGraphQLClient, user_input: str, broadcaster_id: str) -> PartialEmote:
    """Get emote_id from `user_input`."""
    split = user_input.split()
    if len(split) > 1:
        msg = "Bad Input; I require '<emote_link_or_id>' - no extra words"
        raise errors.BadUserInputError(msg)
    if len(split) <= 0:
        msg = "Bad Input; why would you type an empty text?"
        raise errors.BadUserInputError(msg)

    return await parse_emote(stv, split[0], broadcaster_id)


#############################################################################################################################
# ARGUMENT CONVERTERS
#############################################################################################################################


class SearchEmoteConverter(commands.Converter[PartialEmote]):
    """Seven TV Emote Converter.

    Converts user_input from `str` type into 7TV emote_id.

    Format: ``<global_emote_id_name_or_link> <alias>`` -> emote, alias
    """

    @override
    async def convert(self, ctx: Context, emote_id_link_or_name: str) -> PartialEmote:  # ty: ignore[invalid-method-override]
        """Convert `user_input` to 7TV emote_id."""
        return await parse_emote(ctx.bot.stv, emote_id_link_or_name)


class UserEmoteConverter(commands.Converter[PartialEmote]):
    """Seven TV Emote Converter.

    Converts user_input from `str` type into 7TV emote_id.

    Format: ``<user_emote_id_name_or_link>`` -> emote
    """

    @override
    async def convert(self, ctx: Context, emote_id_link_or_name: str) -> PartialEmote:  # ty: ignore[invalid-method-override]
        """Convert `user_input` to 7TV emote_id."""
        return await parse_emote(ctx.bot.stv, emote_id_link_or_name, ctx.broadcaster.id)


#############################################################################################################################
# GUARDS
#############################################################################################################################


async def _is_broadcaster_dev_or_editor_predicate(ctx: Context) -> Literal[True]:
    if ctx.chatter.id in {ctx.broadcaster.id, ctx.bot.owner_id}:
        return True

    query = "SELECT editor_id FROM ttv_stv_mods WHERE broadcaster_id = $1 AND editor_id = $2"
    editor_id: str | None = await ctx.bot.pool.fetchval(query, ctx.broadcaster.id, ctx.chatter.id)
    if editor_id is None:
        msg = "Only broadcaster and 7tv editors can use this command"
        raise errors.NotAllowedError(msg)
    return True


def is_broadcaster_dev_or_editor() -> Any:
    """Allow the command to be completed only by the following people.

    * broadcaster
    * developer
    * editor
    """
    return commands.guard(_is_broadcaster_dev_or_editor_predicate)


def is_broadcaster_dev_editor_or_adder() -> Any:
    """Allow the command to be completed only by emote owners.

    An emote is supposed to be managed by
    * broadcaster
    * developer
    * 7tv emote editor
    * a person who added it in the first place.

    PS. This is a fake guard as validation happens elsewhere because it needs command arguments
    (twitchio sets ``ctx.args`` after command invocation).

    This guard is needed solely for documentation quirks purposes.
    """

    def predicate(_: Context) -> Literal[True]:
        return True

    return commands.guard(predicate)


#############################################################################################################################
# COMPONENT
#############################################################################################################################


class SevenTVPublic(PublicComponent):
    """Cycling Emotes."""

    EMOTE = globs.TwitchEmote.FeelsDankMan

    def __init__(self, bot: Bot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)

        # Supported Rewards
        self.permanent = Reward(
            code="permanent",
            name="Add Permanent Emote",
            table="ttv_stv_permanent_rewards",
            processor=self.process_permanent_redemption,
        )
        self.cycle = Reward(
            code="cycle",
            name="Add Cycle Emote",
            table="ttv_stv_cycle_rewards",
            processor=self.process_cycle_redemption,
        )
        self.blacklist = Reward(
            code="blacklist",
            name="Blacklist/Remove Emote",
            table="ttv_stv_blacklist_rewards",
            processor=self.process_blacklist_redemption,
        )
        self.rewards = (self.permanent, self.cycle, self.blacklist)
        self.caches_ready: asyncio.Event = asyncio.Event()

    @override
    async def component_load(self) -> None:
        self.fill_all_caches.start()
        self.double_check_reward_redemptions_queues.start()
        self.double_check_cycle_emotes_existence.start()
        self.expire_blacklisted_emotes.start()
        await super().component_load()

    @override
    async def component_teardown(self) -> None:
        self.fill_all_caches.stop()
        self.double_check_reward_redemptions_queues.stop()
        self.double_check_cycle_emotes_existence.stop()
        self.expire_blacklisted_emotes.stop()
        await super().component_teardown()

    #########################################################################################################################
    # COMMON TASKS
    #########################################################################################################################

    async def fill_cache(self, reward: Reward) -> None:
        """Fill cache.

        Just a convenience so we don't query database each redemption.
        """
        query = f"SELECT reward_id FROM {reward.table}"  # ruff: ignore[hardcoded-sql-expression]
        reward.cache = {r for (r,) in await self.bot.pool.fetch(query)}

    @loop(seconds=10)
    async def fill_all_caches(self) -> None:
        """Task to fill caches on startup."""
        try:
            for literal in self.rewards:
                await self.fill_cache(literal)
        except Exception:  # ruff: ignore[blind-except]
            return
        else:
            self.caches_ready.set()
            self.fill_all_caches.stop()

    @loop(hours=8)
    async def double_check_reward_redemptions_queues(self) -> None:
        """Double-check the reward redemption queues.

        This double-checks the redemption queue for the following channel points rewards:
        * "Add cycle emote"
        * "Remove + blacklist emote"
        * "Add permanent emote"
        """
        for reward in self.rewards:
            query = f"SELECT reward_id, broadcaster_id FROM {reward.table}"  # ruff: ignore[hardcoded-sql-expression]
            for row in await self.bot.pool.fetch(query):
                custom_reward = ut.ni(
                    await self.bot.create_partialuser(row["broadcaster_id"]).fetch_custom_rewards(
                        ids=[row["reward_id"]], manageable=True
                    )
                )
                if custom_reward is None:
                    continue

                async for redemption in custom_reward.fetch_redemptions(status="UNFULFILLED", sort="OLDEST"):
                    try:
                        await reward.processor(redemption)
                    except Exception as error:
                        await self.redemption_refund(redemption)
                        if isinstance(
                            error,
                            (
                                UnsatisfyingResultError,
                                errors.BadUserInputError,
                                errors.NotAllowedError,
                                errors.RespondWithError,
                            ),
                        ):
                            pass
                        else:
                            raise

    #########################################################################################################################
    # COMMON QUERIES
    #########################################################################################################################

    async def select_allow_common_words(self, broadcaster_id: str) -> bool:
        """Select broadcaster's allow common words boolean."""
        query = "SELECT allow_common_words FROM ttv_stv_users WHERE broadcaster_id = $1;"
        return await self.bot.pool.fetchval(query, broadcaster_id)

    async def select_emote_set(self, broadcaster_id: str) -> PartialEmoteSet:
        """Select emote set id."""
        query = "SELECT emote_set_id FROM ttv_stv_users WHERE broadcaster_id = $1;"
        emote_set_id: str | None = await self.bot.pool.fetchval(query, broadcaster_id)
        if emote_set_id is None:
            msg = f"7tv features are not attached to any of the emote sets {self.EMOTE}"
            raise errors.RespondWithError(msg)
        return PartialEmoteSet(self.bot.stv, emote_set_id=emote_set_id)

    async def insert_into_stv_users(self, broadcaster_id: str, emote_set_id: str | None = None) -> str:
        """Add to `stv_users` table."""
        partial_user = self.bot.stv.create_partial_user(broadcaster_id)
        user_info = await partial_user.fetch_info()

        if emote_set_id is not None and emote_set_id != user_info.active_emote_set_id:
            # we need to validate ownership and get its name
            emote_set_info = await self.bot.stv.create_partial_emote_set(emote_set_id).fetch_info()
            if emote_set_info.owner_id != user_info.id:
                msg = "You are not allowed to attach to emote sets you don't own"
                raise errors.RespondWithError(msg)

            emote_set_name = emote_set_info.name
        else:
            emote_set_name = user_info.active_emote_set_name
            emote_set_id = user_info.active_emote_set_id

        query = """
            INSERT INTO ttv_stv_users
                (broadcaster_id, stv_user_id, emote_set_id)
            VALUES ($1, $2, $3)
            ON CONFLICT(broadcaster_id)
                DO UPDATE SET stv_user_id  = $2,
                            emote_set_id = $3;
        """
        await self.bot.pool.execute(query, broadcaster_id, user_info.id, emote_set_id)
        return f"linked bot's 7tv features to your '{emote_set_name}' emote set ({emote_set_id}) {self.EMOTE}"

    async def delete_from_cycle_emotes(self, emote_id: str, emote_set_id: str) -> None:
        """Delete an emote from ``ttv_stv_cycle_emotes``."""
        query = "DELETE FROM ttv_stv_cycle_emotes WHERE emote_id = $1 AND emote_set_id = $2"
        await self.bot.pool.execute(query, emote_id, emote_set_id)

    #########################################################################################################################
    # COMMON UTILS
    #########################################################################################################################

    async def fulfil_redemption(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
    ) -> None:
        """Fulfil redemption.

        TwitchIO quirk - the interface for ``ChannelPointsRedemptionAdd`` and ``CustomRewardRedemption`` is slightly
        different despite essentially representing the same thing, but we still need to account for the differences.
        """
        if redemption.status != "UNFULFILLED":
            # Already done
            return

        with contextlib.suppress(twitchio.HTTPException):
            if isinstance(redemption, twitchio.ChannelPointsRedemptionAdd):
                await redemption.fulfill(token_for=redemption.broadcaster.id)
            else:
                await redemption.fulfill()

    async def redemption_refund(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
    ) -> None:
        """Redemption refund.

        TwitchIO quirk - the interface for ``ChannelPointsRedemptionAdd`` and ``CustomRewardRedemption`` is slightly
        different despite essentially representing the same thing, but we still need to account for the differences.
        """
        if redemption.status != "UNFULFILLED":
            # Already done
            return

        with contextlib.suppress(twitchio.HTTPException):
            if isinstance(redemption, twitchio.ChannelPointsRedemptionAdd):
                await redemption.refund(token_for=redemption.broadcaster.id)
            else:
                # ``CustomRewardRedemption`` automatically puts proper token
                await redemption.refund()

    async def redemption_respond(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
        content: str,
    ) -> None:
        """Redemption respond.

        TwitchIO quirk - the interface for ``ChannelPointsRedemptionAdd`` and ``CustomRewardRedemption`` is slightly
        different despite essentially representing the same thing, but we still need to account for the differences.
        """
        if isinstance(redemption, twitchio.ChannelPointsRedemptionAdd):
            await redemption.respond(content)
        else:
            await redemption.broadcaster.send_message(content, sender=self.bot.bot_id)

    #########################################################################################################################
    # VALIDATIONS
    #########################################################################################################################

    NO_REWARD_ERROR_MSG = "This broadcaster does not have {0!r} channel points reward set up " + EMOTE

    async def validate_reward_exists(self, reward: Reward, broadcaster_id: str) -> None:
        """Validate whether the broadcaster has reward within the database."""
        query = f"SELECT COUNT(1) FROM {reward.table} WHERE broadcaster_id = $1"  # ruff: ignore[hardcoded-sql-expression]
        count: int = await self.bot.pool.fetchval(query, broadcaster_id)
        if count == 0:
            msg = self.NO_REWARD_ERROR_MSG.format(reward.name)
            raise errors.RespondWithError(msg)

    async def validate_editor_status(self, ctx: Context) -> None:
        """Validate whether the bot is currently a 7TV editor for the ctx.broadcaster."""
        partial_user = ctx.bot.stv.create_partial_user(ctx.broadcaster.id)
        editor_for = await partial_user.check_bot_editor()

        if not editor_for.is_enough_permissions:
            msg = (
                "7tv editor invite was sent but it does not have required permissions "
                f"(it needs 'Emote Sets > Manage') {self.EMOTE}"
            )
            raise errors.RespondWithError(msg)
        if editor_for.state != "ACCEPTED":
            msg = (
                f"7tv editor invite was sent, permissions are okay, invite state={editor_for.state}, "
                f"please use '{ctx.prefix}7tv editor accept' command to make the bot accept it {self.EMOTE}"
            )
            raise errors.RespondWithError(msg)

    async def validate_reward_id(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
        reward: Reward,
    ) -> bool:
        """Validate reward id.

        Also refunds points to Irene because you know, testing costs :D
        """
        await self.caches_ready.wait()  # need cache to be filled.
        if redemption.reward.id not in reward.cache:
            return False

        if self.is_dev(redemption.user.id):
            # Refund the points for Irene because you know, testing costs :D
            await self.redemption_refund(redemption)
        return True

    async def validate_is_emote_blacklisted(self, broadcaster_id: str, emote_id: str) -> Literal[True]:
        """Validate whether the emote is blacklisted.

        Raises
        ------
        errors.NotAllowedError
            Emote is blacklisted.
        """
        query = """
            SELECT e.emote_id, e.blacklisted_at, r.duration, r.remove_only
            FROM ttv_stv_blacklist_emotes e
                    JOIN ttv_stv_blacklist_rewards r
                        ON r.broadcaster_id = e.broadcaster_id
            WHERE e.emote_id = $1
                AND r.broadcaster_id = $2;
        """
        row: ValidateIsEmoteBlacklistedQueryRow | None = await self.bot.pool.fetchrow(query, emote_id, broadcaster_id)
        if row is None:
            # Emote is not blacklisted.
            return True
        if row["remove_only"]:
            # Blacklist is turned off.
            return True

        expire_dt = clock.get_next_hour_start(row["blacklisted_at"] + dt.timedelta(hours=row["duration"]))
        msg = (
            "The requested emote is blacklisted; "
            f"{clock.human_datetime_diff(expire_dt, mode='short')} until it is allowed {self.EMOTE}"
        )
        raise errors.NotAllowedError(msg)

    async def validate_is_emote_alias_a_common_word(
        self, broadcaster_id: str, emote_id: str, emote_alias: str | None = None
    ) -> Literal[True]:
        """Validate whether the emote alias is a common word.

        Internally, this just checks against a list of common words.
        Only lowercase strings are not allowed.
        For example, it's fine to have an emote "HELLO" because it's not a common word anymore.

        Raises
        ------
        errors.NotAllowedError
            Emote alias is a common word and the broadcaster does not allow such.
        """
        if await self.select_allow_common_words(broadcaster_id):
            # Common words are allowed as emote aliases
            return True
        if emote_alias is None:
            # we have to check emote's default name
            emote = await self.bot.stv.fetch_emote(emote_id)
            emote_alias = emote.default_name
        if emote_alias in COMMON_WORDS:
            msg = "Common words are not allowed to be used as emote aliases"
            raise errors.NotAllowedError(msg)
        if emote_alias.isnumeric():
            msg = "Numbers are considered as a common words and as such not allowed"
            raise errors.NotAllowedError(msg)
        return True

    async def run_add_emote_validators(
        self,
        emote_id: str,
        broadcaster_id: str,
        emote_alias: str | None = None,
    ) -> None:
        """Run all existing validations for 'Add Permanent/Cycle Emote' redemptions."""
        # Validations
        await self.validate_is_emote_blacklisted(broadcaster_id, emote_id)
        await self.validate_is_emote_alias_a_common_word(broadcaster_id, emote_id, emote_alias)

    #########################################################################################################################
    # HELPERS
    #########################################################################################################################

    async def create_custom_reward_helper(
        self,
        ctx: Context,
        *,
        reward: Reward,
        reward_title: str,
        reward_prompt: str,
        recreate: str,
    ) -> str:
        """Create reward helper."""
        await self.validate_editor_status(ctx)
        # Validate arguments
        recreate_flag = recreate == "--recreate"
        if recreate and not recreate_flag:
            # TODO: wait for twitchio flag converters
            msg = "Only '--recreate' flag is currently supported; did you make a typo?"
            raise errors.RespondWithError(msg)

        if len(reward_title) > 45:
            msg = "Custom reward title is not allowed to be more than 45 characters"
            raise ValueError(msg)
        if len(reward_prompt) > 200:
            msg = "Custom reward prompt is not allowed to be more than 200 characters"
            raise ValueError(msg)

        query = f"SELECT reward_id FROM {reward.table} WHERE broadcaster_id = $1"  # ruff: ignore[hardcoded-sql-expression]
        old_reward_id: str | None = await self.bot.pool.fetchval(query, ctx.broadcaster.id)

        # Validate database data
        if old_reward_id is not None:
            if not recreate_flag:
                msg = (
                    f"The bot's database already has information about {reward.name} channel points reward "
                    "for this channel;"
                    " if it's not a mistake and you really want to delete old reward record, create a new reward and "
                    "override old information then use '--recreate' command flag "
                    f"{self.EMOTE}"
                )
                raise errors.RespondWithError(msg)
            # Recreate: I guess we are deleting the old reward
            with contextlib.suppress(twitchio.HTTPException):
                await ctx.broadcaster.delete_custom_reward(old_reward_id)

        # Validate same title
        streamer_rewards = await ctx.broadcaster.fetch_custom_rewards()
        same_title_reward = next(
            (r for r in streamer_rewards if r.title == reward_title and r.id != old_reward_id), None
        )
        if same_title_reward is not None:
            msg = (
                f"This channel already has a channel points reward with a title '{reward_title}'? "
                "is it intentional that you call this command? If yes then rename/delete that reward then."
            )
            raise errors.RespondWithError(msg)

        custom_reward = await ctx.broadcaster.create_custom_reward(
            title=reward_title,
            cost=10,
            prompt=reward_prompt,
        )
        query = f"""
            INSERT INTO {reward.table}
            (broadcaster_id, reward_id)
            VALUES ($1, $2)
            ON CONFLICT (broadcaster_id)
                DO UPDATE SET reward_id = $2
        """  # ruff: ignore[hardcoded-sql-expression], table is developer-given.
        await self.bot.pool.execute(query, ctx.broadcaster.id, custom_reward.id)

        await self.fill_cache(reward)
        await ctx.send(
            f"Created {reward.name} channel points reward; "
            "PS. if you want to edit it (e.g. text or color) - visit your creator dashboard "
            f"(dashboard.twitch.tv/u/{ctx.broadcaster.name}/viewer-rewards/channel-points/rewards). "
            f"Just don't remove `Require Viewer to Enter Text`, please {self.EMOTE}",
        )
        return custom_reward.id

    async def get_custom_reward(self, reward: Reward, broadcaster: twitchio.PartialUser) -> twitchio.CustomReward:
        """Get custom reward helper."""
        query = f"SELECT reward_id FROM {reward.table} WHERE broadcaster_id = $1"  # ruff: ignore[hardcoded-sql-expression]
        reward_id: str | None = await self.bot.pool.fetchval(query, broadcaster.id)
        if reward_id is None:
            msg = f"Broadcaster does not have {reward.name} channel points reward set up {self.EMOTE}"
            raise errors.RespondWithError(msg)

        custom_reward = ut.ni(await broadcaster.fetch_custom_rewards(ids=[reward_id]))
        if custom_reward is None:
            msg = (
                f"It seems the {reward.name} reward was deleted? "
                f"Please, recreate it using `!7tv {reward.code} create --recreate`"
            )
            raise errors.RespondWithError(msg)

        return custom_reward

    #########################################################################################################################
    # MAIN COMMAND
    #########################################################################################################################

    @commands.group(name="7tv", aliases=["stv"], invoke_fallback=True)
    async def stv(self, ctx: Context) -> None:
        """Group command for `!7tv`.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

    #########################################################################################################################
    # ADD PERMANENT EMOTE CHANNEL POINTS REWARD
    #########################################################################################################################

    @stv.group(name="permanent", invoke_fallback=True)
    async def stv_permanent(self, ctx: Context) -> None:
        """Group command for `!7tv permanent`.

        These commands manage "Add Permanent Emote" channel points reward.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

    # TODO: Wait for FlagConverter
    @guards.is_broadcaster_or_dev()
    @stv_permanent.command(name="create")
    async def stv_permanent_create(self, ctx: Context, *, recreate: str = "") -> None:
        """Create 'Add Permanent Emote' channel points reward.

        The bot will listen to the redemptions of this reward and process them to add permanent 7tv emotes.

        A few notes about the created channel points reward:

        * It accepts user input in a format ``<emote_id_link_or_name> <emote_alias>``.
        * If emote name is provided (instead of emote id or emote link within ``<emote_id_link_or_name>``) then
          the bot will search for the most popular emote in 7tv matching it.
        * If ``<emote_alias>`` is also provided then the specified emote will be added with an alias.

          Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF smh" will add the "MinaSmh" emote as "smh".

        """
        await self.create_custom_reward_helper(
            ctx,
            reward=self.permanent,
            reward_title="Add 7TV emote",
            reward_prompt=(
                "Give me a 7TV emote link or emote ID. Optionally, type an emote alias. "
                'Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF SMH"'
            ),
            recreate=recreate,
        )

    @stv_permanent.command(name="status")
    async def stv_permanent_status(self, ctx: Context) -> None:
        """Get some information about 'Add Permanent Emote' channel points reward's status."""
        custom_reward = await self.get_custom_reward(self.permanent, ctx.broadcaster)
        status = " \N{BULLET} ".join([
            f"title={custom_reward.title}",
            f"cost={custom_reward.cost}",
            f"reward_id={custom_reward.id}",
        ])
        await ctx.send(f"{status} {self.EMOTE}")

    async def process_permanent_redemption(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
    ) -> None:
        """Process 'Add Permanent Emote' redemption.

        Errors are handled by global error handler and it refunds the points.
        """
        if not await self.validate_reward_id(redemption, self.permanent):
            return

        log.debug(
            "User @%s (%s) requested 'Add Permanent Emote' at broadcaster @%s (%s) with input: '%s'",
            redemption.user.display_name,
            redemption.user.id,
            redemption.broadcaster.display_name,
            redemption.broadcaster.id,
            redemption.user_input,
        )

        # Step 1. Parse User Input

        emote, alias = await parse_add_rename_reward_input(self.bot.stv, redemption.user_input)
        log.debug("Parsed user input: emote_id=%s emote_alias=%s", emote.id, alias)

        # Step 2. Get Emote Set

        emote_set = await self.select_emote_set(redemption.broadcaster.id)
        log.debug("Operating on emote_set #%s", emote_set.id)

        # Step 3. Add the requested emote

        await self.run_add_emote_validators(
            emote_id=emote.id, broadcaster_id=redemption.broadcaster.id, emote_alias=alias
        )
        await emote_set.add_emote(emote_id=emote.id, emote_alias=alias)
        log.debug("Added #%s", emote.id)

        await self.redemption_respond(redemption, f"Done {self.EMOTE}")
        await self.fulfil_redemption(redemption)
        log.info("Done with the redemption '%s' (%s)", alias, emote.id)

    @commands.Component.listener(name="custom_redemption_add")
    async def channel_points_permanent_redeem(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Somebody redeemed a custom channel points reward."""
        await self.process_permanent_redemption(redemption)

    #########################################################################################################################
    # CYCLE TASKS
    #########################################################################################################################

    @loop(hours=8)
    async def double_check_cycle_emotes_existence(self) -> None:
        """Double check database's data.

        For example, if the streamer manually deleted emotes while the bot is offline -
        then database might have wrong data.
        """
        query = "SELECT emote_id, emote_set_id FROM ttv_stv_cycle_emotes"
        emote_sets = defaultdict[str, list[str]](list)
        for row in await self.bot.pool.fetch(query):
            emote_sets[row["emote_set_id"]].append(row["emote_id"])

        for emote_set_id, emote_ids in emote_sets.items():
            emote_set = PartialEmoteSet(self.bot.stv, emote_set_id)
            all_emotes_ids = {emote.id for emote in await emote_set.fetch_all_emotes()}
            for emote_id in emote_ids:
                if emote_id in all_emotes_ids:
                    continue
                log.debug(
                    "Detected Cycle emote (%s) that was removed while bot was inactive - deleting from the database",
                    emote_id,
                )
                await self.delete_from_cycle_emotes(emote_id, emote_set_id)

    #########################################################################################################################
    # 7TV EMOTE CYCLING EMOTES CHANNEL POINTS REWARD
    #########################################################################################################################

    @stv.group(name="cycle", invoke_fallback=True)
    async def stv_cycle(self, ctx: Context) -> None:
        """Group command for `!7tv cycle`.

        These commands manage 7tv cycle channel points reward and related emotes.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

    # TODO: Wait for FlagConverter
    @guards.is_broadcaster_or_dev()
    @stv_cycle.command(name="create")
    async def stv_cycle_create(self, ctx: Context, recreate: str = "") -> None:
        """Create 'Add Cycle Emote' channel points reward, redeems for which will be and process to add/remove emotes.

        A few notes about the created channel points reward:

        * It accepts user input in a format ``<emote_id_link_or_name> <emote_alias>``.
        * If emote name is provided (instead of emote id or emote link within ``<emote_id_link_or_name>``) then
          the bot will search for the most popular emote in 7tv matching it.
        * If ``<emote_alias>`` is also provided then the specified emote will be added with an alias.

          Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF smh" will add the "MinaSmh" emote as "smh".
        """
        await self.create_custom_reward_helper(
            ctx,
            reward=self.cycle,
            reward_title="Add 7TV emote (limited slots, old cycle out)",
            reward_prompt=(
                "Give me a 7TV emote link or emote ID. Optionally, type an emote alias. "
                'Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF SMH"'
            ),
            recreate=recreate,
        )

    @stv_cycle.command(name="status")
    async def stv_cycle_status(self, ctx: Context) -> None:
        """Get some information about 'Add Cycle Emote' channel points reward's status."""
        custom_reward = await self.get_custom_reward(self.cycle, ctx.broadcaster)
        query = """
            SELECT r.reward_id,
                r.emote_limit,
                (SELECT COUNT(*)
                    FROM ttv_stv_cycle_emotes e
                    WHERE e.broadcaster_id = r.broadcaster_id) AS emote_count,
                u.emote_set_id
            FROM ttv_stv_cycle_rewards r
                JOIN ttv_stv_users u ON u.broadcaster_id = r.broadcaster_id
            WHERE u.broadcaster_id = $1;
        """
        row: CycleStatusQueryRow = await self.bot.pool.fetchrow(query, ctx.broadcaster.id)
        status = " \N{BULLET} ".join([
            f"title={custom_reward.title}",
            f"cost={custom_reward.cost}",
            f"reward_id={custom_reward.id}",
            f"emote_limit={row['emote_limit']}",
            f"emote_count={row['emote_count']}",
            f"emote_set_id={row['emote_set_id']}",
        ])
        await ctx.send(f"{status} {self.EMOTE}")

    # TODO: Wait for FlagConverter
    @is_broadcaster_dev_or_editor()
    @stv_cycle.command(name="settings")
    async def stv_cycle_settings(self, ctx: Context, emote_limit: int | None = None) -> None:
        """Change 'Add Cycle Emote' channel points reward's settings.

        Parameters
        ----------
        emote_limit
            Integer, emote limit setting. When total amount of cycle emote becomes more than this number,
            the bot will have to start deleting the oldest cycle emotes.
            When reward is initially created - this equals 10).
            Lowering the limit doesn't trim current 'Add Cycle Emote' emotes pool until the next redemption due
            implementation specifics.
        """
        if all(arg is None for arg in (emote_limit,)):
            msg = "You need to input at least one of the settings"
            raise errors.RespondWithError(msg)

        await self.validate_reward_exists(self.cycle, ctx.broadcaster.id)

        # Validate new_limit
        if emote_limit is not None:
            if emote_limit < 1:
                msg = f"Not allowed to have emote limit below 1 {self.EMOTE}"
                raise errors.RespondWithError(msg)
            if emote_limit > 999:
                msg = f"Not allowed to have emote limit above 999 {self.EMOTE}"
                raise errors.RespondWithError(msg)

        query = "UPDATE ttv_stv_cycle_rewards SET emote_limit = $1 WHERE broadcaster_id = $2;"
        await self.bot.pool.execute(query, emote_limit, ctx.broadcaster.id)
        await ctx.send(f"Updated {self.EMOTE}")

    @is_broadcaster_dev_or_editor()
    @stv_cycle.command(name="drop")
    async def stv_cycle_drop(
        self,
        ctx: Context,
        emote_id_link_or_name: Annotated[PartialEmote, UserEmoteConverter],
    ) -> None:
        """Drop an emote from the 'Add Cycle Emote' emotes list.

        This drops the emote from the bot's database essentially making it "permanent", leaving it
        up to other 7TV editors (or a broadcaster) to manage it.
        In other words, this command stops the emote from being eventually cycled out.

        Parameters
        ----------
        emote_id_link_or_name
            is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.

        Examples
        --------
        All these examples below drop same "smh" emote

        * ``!7tv cycle drop 01FP8TR8G8000EJT2EVEY3JQTF``
        * ``!7tv cycle drop smh``
        * ``!7tv cycle drop https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF``
        """
        query = "DELETE FROM ttv_stv_cycle_emotes WHERE emote_id = $1 AND broadcaster_id = $2 RETURNING emote_id"
        emote_id: str | None = await self.bot.pool.fetchval(query, emote_id_link_or_name.id, ctx.broadcaster.id)
        if emote_id is None:
            msg = "This emote is not related to 'Add Cycle Emote' reward."
            raise errors.RespondWithError(msg)
        await ctx.send(f"'{emote_id_link_or_name:.id}' was removed from the cycling emote list {self.EMOTE}")

    @stv_cycle.command(name="show-emotes", aliases=["all-emotes"])
    async def stv_cycle_showemotes(self, ctx: Context) -> None:
        """Show all emotes that were added with 'Add Cycle Emote' channel points reward redemptions."""
        query = "SELECT emote_id FROM ttv_stv_cycle_emotes WHERE broadcaster_id = $1;"
        emote_ids = [e for (e,) in await self.bot.pool.fetch(query, ctx.broadcaster.id)]
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        emote_set_emotes = await emote_set.fetch_all_emotes()
        cycle_emotes = [emote.alias for emote in emote_set_emotes if emote.id in emote_ids]
        content = f"Total: {len(cycle_emotes)}; " + " ".join(cycle_emotes)
        await ctx.chunk_send(content)

    async def process_cycle_redemption(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
    ) -> None:
        """Process 'Add Cycle Emote' Redemption.

        Errors are handled by global error handler and it refunds the points.
        """
        if not await self.validate_reward_id(redemption, self.cycle):
            return

        log.debug(
            "User @%s (%s) requested cycle-emote at broadcaster @%s (%s) with input: '%s'",
            redemption.user.display_name,
            redemption.user.id,
            redemption.broadcaster.display_name,
            redemption.broadcaster.id,
            redemption.user_input,
        )

        # Step 1. Parse User Input
        emote, alias = await parse_add_rename_reward_input(self.bot.stv, redemption.user_input)
        log.debug("Parsed user input: emote_id=%s emote_alias=%s", emote.id, alias)

        # Step 2. Get Emote Set
        emote_set = await self.select_emote_set(redemption.broadcaster.id)
        log.debug("Operating on emote_set #%s", emote_set.id)

        # Step 3. Need to validate the emote before attempting to remove
        await self.run_add_emote_validators(
            emote_id=emote.id, broadcaster_id=redemption.broadcaster.id, emote_alias=alias
        )

        # Step 4. Remove emote(-s) if above the limit
        query = """
            SELECT e.emote_id
            FROM ttv_stv_cycle_emotes e
            WHERE e.broadcaster_id = $1
                AND e.emote_set_id = $2
            ORDER BY e.added_at DESC
            OFFSET (
                SELECT r.emote_limit - 1
                FROM ttv_stv_cycle_rewards r
                WHERE r.broadcaster_id = $1
            )
        """
        emote_ids_to_remove: list[str] = [
            r for (r,) in await self.bot.pool.fetch(query, redemption.broadcaster.id, emote_set.id)
        ]
        log.debug("Removing emotes #%s", emote_ids_to_remove)

        for emote_id_to_remove in emote_ids_to_remove:
            try:
                await emote_set.remove_emote(emote_id=emote_id_to_remove)
            except EmoteNotFoundError:
                log.debug("Emote Not Found #%s - skipping", emote_id_to_remove)
            else:
                log.debug("Removed emote %s", emote_id_to_remove)
            await self.delete_from_cycle_emotes(emote_id_to_remove, emote_set.id)

        # Step 5. Add the requested emote
        await emote_set.add_emote(emote_id=emote.id, emote_alias=alias)
        log.debug("Added emote #%s", emote.id)

        query = """
            INSERT INTO ttv_stv_cycle_emotes
            (emote_id, broadcaster_id, emote_set_id, requested_by)
            VALUES ($1, $2, $3, $4)
        """
        await self.bot.pool.execute(query, emote.id, redemption.broadcaster.id, emote_set.id, redemption.user.id)
        await self.redemption_respond(redemption, f"Done {self.EMOTE}")
        await self.fulfil_redemption(redemption)
        log.info("Done with cycle redemption for '%s' (%s)", alias, emote.id)

    @commands.Component.listener(name="custom_redemption_add")
    async def channel_points_cycle_redeem(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Somebody redeemed a custom channel points reward."""
        await self.process_cycle_redemption(redemption)

    ####################################################################################################################
    # DEVELOPER TESTING COMMANDS
    ####################################################################################################################

    ####################################################################################################################
    # 7TV EDITOR STATUS / ACCEPT
    ####################################################################################################################

    @stv.group(name="editor", invoke_fallback=True)
    async def stv_editor(self, ctx: Context) -> None:
        """Editor Group."""
        await ctx.group_default_response()

    @stv_editor.command(name="status", aliases=["check"])
    async def stv_editor_status(self, ctx: Context) -> None:
        """Show some debug information about state of 7TV editor request for the streamer."""
        await self.validate_editor_status(ctx)
        content = f"7tv editor invite is accepted and permissions are good {self.EMOTE}"
        await ctx.send(content)

    @stv_editor.command(name="guide")
    async def stv_editor_guide(self, ctx: Context) -> None:
        """Send a small guide on how to make the bot your 7TV editor.

        Practically a TL;DR of the "Attention" admonition from above.
        """
        content = (
            f"{globs.DIGITS[1]} Go to 7tv.app/settings/editors "
            f"{globs.DIGITS[2]} Add Editor > @IrenesBot, make sure 'Emote Sets > Manage' permission is given "
            f"{globs.DIGITS[3]} Use '{ctx.prefix}7tv editor accept' command to make the bot accept the editor role "
            f"{self.EMOTE}"
        )
        await ctx.send(content)

    @guards.is_broadcaster_or_dev()
    @stv_editor.command(name="accept")
    async def stv_editor_accept(self, ctx: Context) -> None:
        """Make the bot accept a pending 7TV editor request from the streamer.

        Invoking this command also makes the bot attach to your currently active 7tv emote set.
        Which is identical to performing ``!7tv emoteset attach`` with no arguments.
        """
        partial_user = ctx.bot.stv.create_partial_user(ctx.broadcaster.id)
        res = await partial_user.accept_editor()
        insert_response = await self.insert_into_stv_users(ctx.broadcaster.id)
        content = f"Just {res.lower()} your 7TV editor request; also {insert_response} {self.EMOTE}"
        await ctx.send(content)

    ####################################################################################################################
    # 7TV EMOTESET
    ####################################################################################################################

    @stv.group(name="emoteset", invoke_fallback=True)
    async def stv_emoteset(self, ctx: Context) -> None:
        """Emote Set Group."""
        await ctx.group_default_response()

    @guards.is_broadcaster_or_dev()
    @stv_emoteset.command(name="attach")
    async def stv_emoteset_attach(self, ctx: Context, emote_set_id: str | None = None) -> None:
        """Attach bot's 7tv features to the emote set.

        Parameters
        ----------
        emote_set_id
            Optional, 7TV emote set id for the bot to attach to.
            If not provided - the bot will attach to streamer's currently active emote set. Due to my laziness
            this doesn't accept emote set links, so please, copy only ID part form the emote set's URL.
        """
        insert_response = await self.insert_into_stv_users(ctx.broadcaster.id, emote_set_id=emote_set_id)
        await ctx.send(f"Successfully {insert_response}")

    @stv_emoteset.command(name="status")
    async def stv_emoteset_status(self, ctx: Context) -> None:
        """Show some debug information about currently attached 7tv emote set."""
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        await ctx.send(f"{emote_set!r} {self.EMOTE}")

    ####################################################################################################################
    # 7TV EMOTE MANAGEMENT
    ####################################################################################################################

    async def add_helper(self, ctx: Context, emote: PartialEmote, alias: str | None) -> None:
        """Add 7TV emote helper.

        Note that this doesn't use `self.emote_set_add_with_validations` because "!7tv add" commands are
        supposed to be restricted to the broadcaster, developer and 7tv editors only.
        """
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        await emote_set.add_emote(emote_id=emote.id, emote_alias=alias)
        await ctx.send("Added")

    @is_broadcaster_dev_or_editor()
    @stv.command(name="add")
    async def stv_add(
        self,
        ctx: Context,
        emote_id_link_or_name: Annotated[PartialEmote, SearchEmoteConverter],
        alias: str | None = None,
    ) -> None:
        """Add 7TV emote.

        PS. This command also has a short version ``!add`` (so no need to type ``!7tv``).

        Parameters
        ----------
        emote_id_link_or_name
            is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.
        alias
            Optional, if provided then the emote will be added under this alias.

        Examples
        --------
        All these examples below add same "smh" emote

        * ``!7tv add 01FP8TR8G8000EJT2EVEY3JQTF``
        * ``!7tv add https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF SMH`` - adds it under "SMH" emote alias.
        * ``!7tv add smh`` - but it might add some other "smh" emote, if it's more popular.
        """
        await self.add_helper(ctx, emote_id_link_or_name, alias)

    @is_broadcaster_dev_or_editor()
    @commands.command(name="add")
    async def add(
        self,
        ctx: Context,
        emote_id_link_or_name: Annotated[PartialEmote, SearchEmoteConverter],
        alias: str | None = None,
    ) -> None:
        """Add 7TV emote.

        Shortcut for ``!7tv add``. Consult the documentation for that command.
        """
        await self.add_helper(ctx, emote_id_link_or_name, alias)

    ####################################################################################################################
    # 7TV VIEWER (OR POSSIBLE VIEWER) COMMANDS
    ####################################################################################################################

    async def validate_emote_ownership(self, ctx: Context, user_id: str, emote_id: str) -> OwnershipEnum:
        """Validate emote ownership.

        An emote is supposed to be managed by
        * broadcaster
        * developer
        * a person who added it in the first place.
        """
        try:
            await _is_broadcaster_dev_or_editor_predicate(ctx)
        except errors.NotAllowedError:
            pass
        else:
            return OwnershipEnum.broadcaster_dev_or_editor

        query = "SELECT requested_by FROM ttv_stv_cycle_emotes WHERE emote_id = $1 AND broadcaster_id = $2"
        requested_by: str | None = await self.bot.pool.fetchval(query, emote_id, ctx.broadcaster.id)
        if requested_by is None:
            msg = f"Invalid emote (probably not temporary one) {self.EMOTE}"
            raise errors.RespondWithError(msg)

        if requested_by != user_id:
            msg = f"You are not allowed to manage this emote {self.EMOTE}"
            raise errors.RespondWithError(msg)

        return OwnershipEnum.chatter

    async def rename_emote_worker(self, ctx: Context, emote: PartialEmote, alias: str) -> None:
        """Rename 7TV emote helper."""
        ownership_type = await self.validate_emote_ownership(ctx, ctx.chatter.id, emote.id)
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        if ownership_type == OwnershipEnum.chatter:
            # Need some validations since it's not an "elevated request"
            await self.validate_is_emote_alias_a_common_word(ctx.broadcaster.id, emote.id, alias)
        await emote_set.rename_emote(emote_id=emote.id, new_emote_alias=alias)
        await ctx.send(f"Renamed {self.EMOTE}")

    @is_broadcaster_dev_editor_or_adder()
    @stv.command(name="rename")
    async def stv_rename(
        self,
        ctx: Context,
        emote_id_link_or_name: Annotated[PartialEmote, UserEmoteConverter],
        new_alias: str,
    ) -> None:
        """Rename 7TV emote.

        PS. This command also has a short version ``!rename`` (so no need to type ``!7tv``).

        Parameters
        ----------
        emote_id_link_or_name
            is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.
        new_alias
            New emote alias with which the emote will be renamed.

        Examples
        --------
        All these examples below rename "smh" emote into "SMH"

        * ``!7tv rename 01FP8TR8G8000EJT2EVEY3JQTF SMH``
        * ``!7tv rename https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF SMH``
        * ``!7tv rename smh SMH``
        """
        await self.rename_emote_worker(ctx, emote_id_link_or_name, new_alias)

    @is_broadcaster_dev_editor_or_adder()
    @commands.command(name="rename")
    async def rename(
        self,
        ctx: Context,
        emote_id_link_or_name: Annotated[PartialEmote, UserEmoteConverter],
        new_alias: str,
    ) -> None:
        """Rename 7TV emote.

        Shortcut for ``!7tv rename``. Consult the documentation for that command.
        """
        await self.rename_emote_worker(ctx, emote_id_link_or_name, new_alias)

    async def remove_emote_worker(self, ctx: Context, emote: PartialEmote) -> None:
        """Remove 7TV emote helper."""
        await self.validate_emote_ownership(ctx, ctx.chatter.id, emote.id)
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        await emote_set.remove_emote(emote_id=emote.id)
        await self.delete_from_cycle_emotes(emote.id, emote_set.id)
        await ctx.send(f"Removed {self.EMOTE}")

    @is_broadcaster_dev_editor_or_adder()
    @stv.command(name="remove")
    async def stv_remove(
        self,
        ctx: Context,
        emote_id_link_or_name: Annotated[PartialEmote, UserEmoteConverter],
    ) -> None:
        """Remove 7TV emote.

        PS. This command also has a short version ``!remove`` (so no need to type ``!7tv``).

        Parameters
        ----------
        emote_id_link_or_name
            is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.
        """
        await self.remove_emote_worker(ctx, emote_id_link_or_name)

    @is_broadcaster_dev_editor_or_adder()
    @commands.command(name="remove")
    async def remove(
        self,
        ctx: Context,
        emote_id_link_or_name: Annotated[PartialEmote, UserEmoteConverter],
    ) -> None:
        """Remove 7TV emote.

        Shortcut for ``!7tv remove``. Consult the documentation for that command.
        """
        await self.remove_emote_worker(ctx, emote_id_link_or_name)

    async def replace_emote_worker(self, ctx: Context, emote: PartialEmote, alias: str | None) -> None:
        """Replace 7TV emote helper."""
        # Validate it's been 10 minutes
        query = """
            SELECT emote_id, added_at
            FROM ttv_stv_cycle_emotes
            WHERE broadcaster_id = $1 AND requested_by = $2
            ORDER BY added_at DESC
            LIMIT 1
        """
        row = await self.bot.pool.fetchrow(query, ctx.broadcaster.id, ctx.chatter.id)
        if row is None:
            msg = f"It seems you have not added any emotes yet {self.EMOTE}"
            raise errors.RespondWithError(msg)
        if clock.utcnow() - row["added_at"] > dt.timedelta(minutes=10):
            msg = f"It's been more than 10 minutes, I don't allow replacing after so long {self.EMOTE}"
            raise errors.RespondWithError(msg)

        await self.run_add_emote_validators(emote_id=emote.id, broadcaster_id=ctx.broadcaster.id, emote_alias=alias)
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        with contextlib.suppress(EmoteNotFoundError):
            await emote_set.remove_emote(emote_id=row["emote_id"])
        await emote_set.add_emote(emote.id, emote_alias=alias)

        query = """
            UPDATE ttv_stv_cycle_emotes
            SET emote_id = $1
            WHERE broadcaster_id = $2 AND emote_id = $3 AND requested_by = $4;
        """
        await self.bot.pool.execute(query, emote.id, ctx.broadcaster.id, row["emote_id"], ctx.chatter.id)
        await ctx.send(f"Replaced {self.EMOTE}")

    @is_broadcaster_dev_editor_or_adder()
    @stv.command(name="replace")
    async def stv_replace(
        self,
        ctx: Context,
        emote_id_link_or_name: Annotated[PartialEmote, SearchEmoteConverter],
        alias: str | None = None,
    ) -> None:
        """Replace 7TV emote.

        If a user who added the emote decides that they want to add a different emote -
        they can replace it with this command.
        For example, if in their redemption they typed "smh", but the bot added some uninteresting version of "smh" -
        they can use ``!replace <some-cool-emote-id>`` without spending any points.
        To prevent abuse, this command only allows replacing your most recent emote request if it was done within
        10 minutes of it.

        PS. This command also has a short version ``!replace`` (so no need to type ``!7tv``).

        Parameters
        ----------
        emote_id_link_or_name
            is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.
        alias
            Optional, if provided then the emote will be added under this alias.

        Examples
        --------
        All these examples below replace the most recent requested emote with a new one. Note that the user does not
        need to type an identifier for the emote that they want to replace - the bot fetches their most recent
        emote addition redemption.

        * ``!7tv replace 01F6R50PYR0004V0XPDH2CKXCH``
        * ``!7tv replace https://7tv.app/emotes/01F6R50PYR0004V0XPDH2CKXCH``
        * ``!7tv replace smh DuckSmh`` - the bot will search 7tv for "smh", note that the bot will still add the most
          popular one, so doing ``!replace smh`` after adding ``smh`` via redemption is pointless.
        """
        await self.replace_emote_worker(ctx, emote_id_link_or_name, alias)

    @is_broadcaster_dev_editor_or_adder()
    @commands.command(name="replace")
    async def replace(
        self,
        ctx: Context,
        emote_id_link_or_name: Annotated[PartialEmote, SearchEmoteConverter],
        alias: str | None = None,
    ) -> None:
        """Replace 7TV emote.

        Shortcut for ``!7tv replace``. Consult the documentation for that command.
        """
        await self.replace_emote_worker(ctx, emote_id_link_or_name, alias)

    ####################################################################################################################
    # BLACKLIST
    ####################################################################################################################

    @stv.group(name="blacklist", invoke_fallback=True)
    async def stv_blacklist(self, ctx: Context) -> None:
        """Group command for `!7tv blacklist`.

        These commands manage 7tv blacklist channel points reward and related emotes.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

    # TODO: Wait for FlagConverter
    @guards.is_broadcaster_or_dev()
    @stv_blacklist.command(name="create")
    async def stv_blacklist_create(self, ctx: Context, recreate: str = "") -> None:
        """Create 'Blacklist/Remove Emote' channel points reward.

        A few notes:

        * Emotes are blocked by emote id. This does mean that bad actors can keep adding emote duplicates.
        * You can read some tips about how bot's channel point rewards related features work here:
          :ref:`channel_points_reward_tips`.
        * The created channel points reward accepts emote links, emote ids and emote names in its user input.
          If emote name was provided then the bot will search for a match within the broadcaster's cycling emotes.
        """
        await self.create_custom_reward_helper(
            ctx,
            reward=self.blacklist,
            reward_title="Remove and blacklist 7TV emote",
            reward_prompt=(
                "This only works for emotes that were added via 'Add 7TV emote' redeem. "
                "Give me a 7TV emote name, link or emote ID. "
                'Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF"'
            ),
            recreate=recreate,
        )

    @stv_blacklist.command(name="status")
    async def stv_blacklist_status(self, ctx: Context) -> None:
        """Get some information about 'Blacklist/Remove Emote' channel points reward's status."""
        custom_reward = await self.get_custom_reward(self.blacklist, ctx.broadcaster)
        status = " \N{BULLET} ".join([
            f"title={custom_reward.title}",
            f"cost={custom_reward.cost}",
            f"reward_id={custom_reward.id}",
        ])
        await ctx.send(f"{status} {self.EMOTE}")

    # TODO: Wait for FlagConverter
    @is_broadcaster_dev_or_editor()
    @stv_blacklist.command(name="settings")
    async def stv_blacklist_settings(
        self, ctx: Context, days: int | None, hours: int | None, remove_only: bool | None  # ruff: ignore[boolean-type-hint-positional-argument]
    ) -> None:
        """Show or change settings related to 'Blacklist/Remove Emote' channel points reward.

        Parameters
        ----------
        days
            Amount of days the emotes will be blacklisted.
        hours
            Additionally, amount of hours the emotes will be blacklisted.

            A few notes:

            * The bot removes blacklisted status from emotes every hour at X:00. This means, for example,
              if current blacklist duration is set to 7 days, it's been 5 days since a certain emote was blacklisted and
              now the broadcaster sets new duration to 3 days then
              that emote (and other emotes) will be released at next X:00.
            * I guess, it's pedantic to point out that the emotes are not being blacklisted `precisely` for the inputted
              duration, since the bot does the blacklist-expiry task every hour at X:00. So an emote "AAA" that was
              blacklisted at 2:01AM will
              have its status lifted at the same time as an emote "BBB" that got blacklisted at 2:59AM.

        Examples
        --------
        * ``!7tv blacklist --days 10 --hours 13`` - 10 days, 13 hours.
        * ``!7tv blacklist --days 14`` - 2 weeks (14 days).
        * ``!7tv blacklist --remove_only yes``
        """
        await self.validate_reward_exists(self.blacklist, ctx.broadcaster.id)

        if all(x is None for x in (days, hours, remove_only)):
            # ``!7tv blacklist settings`` with no arguments: show current settings
            query = """
                SELECT duration, remove_only
                FROM ttv_stv_blacklist_rewards
                WHERE broadcaster_id = $1;
            """
            row = await self.bot.pool.fetchrow(query, ctx.broadcaster.id)
            response = " \N{BULLET} ".join([
                f"duration={clock.human_timedelta(hours=row['duration'])}",
                f"remove_only={row['remove_only']}",
            ])
            await ctx.send(f"{response} {self.EMOTE}")
            return

        # Duration
        if days is not None or hours is not None:
            days, hours = days or 0, hours or 0
            new_duration = days * 24 + hours
            if new_duration < 0:
                msg = "Negative blacklist duration is not allowed"
                raise errors.RespondWithError(msg)
            query = "UPDATE ttv_stv_blacklist_rewards SET duration = $1 WHERE broadcaster_id = $2"
            await self.bot.pool.execute(query, new_duration, ctx.broadcaster.id)
            await ctx.send(f"Changed duration to {clock.human_timedelta(days=days, hours=hours)} {self.EMOTE}")
        if remove_only is not None:
            query = "UPDATE ttv_stv_blacklist_rewards SET remove_only = $2 WHERE broadcaster_id = $1;"
            status: str = await self.bot.pool.execute(query, ctx.broadcaster.id, remove_only)
            if status == "UPDATE 0":
                msg = (
                    f"This broadcaster does not have 'Blacklist/Remove Emote' channel points reward set up {self.EMOTE}"
                )
                raise errors.RespondWithError(msg)
            await ctx.send(
                f"Changed 'Blacklist/Remove Emote' channel points reward behavior to remove-only {self.EMOTE}"
            )

    async def process_blacklist_redemption(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
    ) -> None:
        """Process 'Blacklist/Remove Emote' Redemption.

        Errors are handled by global error handler and it refunds the points.
        """
        if not await self.validate_reward_id(redemption, self.blacklist):
            return

        log.debug(
            "User @%s (%s) requested blacklist-emote at broadcaster @%s (%s) with input: '%s'",
            redemption.user.display_name,
            redemption.user.id,
            redemption.broadcaster.display_name,
            redemption.broadcaster.id,
            redemption.user_input,
        )

        emote = await parse_remove_reward_input(self.bot.stv, redemption.user_input, redemption.broadcaster.id)
        log.debug("Parsed user input: emote_id=%s", emote.id)

        emote_set = await self.select_emote_set(redemption.broadcaster.id)
        log.debug("Operating on emote_set #%s", emote_set.id)

        query = "SELECT emote_id FROM ttv_stv_cycle_emotes WHERE emote_id = $1 AND emote_set_id = $2;"
        selected_emote_id: str | None = await self.bot.pool.fetchval(query, emote.id, emote_set.id)
        if selected_emote_id is None:
            msg = f"This is not a known temporary emote {self.EMOTE}"
            raise errors.RespondWithError(msg)
        with contextlib.suppress(EmoteNotFoundError):
            await emote_set.remove_emote(emote_id=selected_emote_id)
        await self.delete_from_cycle_emotes(selected_emote_id, emote_set.id)

        query = "SELECT remove_only FROM ttv_stv_blacklist_rewards WHERE broadcaster_id = $1"
        remove_only: bool = await self.bot.pool.fetchval(query, redemption.broadcaster.id)
        if not remove_only:
            # Blacklist the emote.
            query = """
                INSERT INTO ttv_stv_blacklist_emotes
                (emote_id, broadcaster_id, requested_by)
                VALUES ($1, $2, $3)
            """
            await self.bot.pool.execute(query, emote.id, redemption.broadcaster.id, redemption.user.id)

        await self.redemption_respond(redemption, f"Done {self.EMOTE}")
        await self.fulfil_redemption(redemption)
        log.info("Done with blacklist redemption for (%s)", emote.id)

    @commands.Component.listener(name="custom_redemption_add")
    async def channel_points_blacklist_redeem(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Somebody redeemed a 'Blacklist/Remove Emote' channel points reward."""
        await self.process_blacklist_redemption(redemption)

    @loop(time=[dt.time(hour=hour) for hour in range(24)])
    async def expire_blacklisted_emotes(self) -> None:
        """Task to expire blacklisted emotes."""
        query = """
            DELETE FROM ttv_stv_blacklist_emotes e
            USING ttv_stv_blacklist_rewards r
            WHERE r.broadcaster_id = e.broadcaster_id
                AND e.blacklisted_at + make_interval(hours => r.duration) < now() AT TIME zone 'utc';
        """
        await self.bot.pool.execute(query)

    @is_broadcaster_dev_or_editor()
    @stv_blacklist.command(name="duration")
    async def stv_blacklist_duration(self, ctx: Context, days: int, hours: int = 0) -> None:
        """Set duration for which the emotes are going to be blacklisted."""

    #########################################################################################################################
    # SOME MODERATION RELATED
    #########################################################################################################################

    async def get_who_added(self, ctx: Context, emote: PartialEmote) -> None:
        """Get username of who added the emote via channel redemption."""
        query = "SELECT requested_by FROM ttv_stv_cycle_emotes WHERE broadcaster_id = $1 AND emote_id = $2"
        user_id: str | None = await self.bot.pool.fetchval(query, ctx.broadcaster.id, emote.id)
        if user_id is not None:
            user = await self.bot.fetch_user(id=user_id)
            if user is None:
                msg = f"Could not find the user who added it (did they delete their account?) {self.EMOTE}"
                raise errors.RespondWithError(msg)
            await ctx.send(f"Temp emote: it was added by {user.display_name} {self.EMOTE}")
            return

        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        added_by = await emote_set.get_emote_added_by(emote.id)
        display_name = await self.bot.stv.get_display_name_by_stv_id(added_by)
        await ctx.send(f"Permanent emote: it was added by {display_name} {self.EMOTE}")

    @stv.command(name="who-added", aliases=["whoadded"])  # cSpell: words: whoadded
    async def stv_who_added(
        self, ctx: Context, emote_id_link_or_name: Annotated[PartialEmote, UserEmoteConverter]
    ) -> None:
        """Get twitch user who added the emote via channel redemption.

        PS. This command also has a short version ``!who-added`` (so no need to type ``!7tv``).

        Parameters
        ----------
        emote_id_link_or_name
            is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.
        """
        await self.get_who_added(ctx, emote_id_link_or_name)

    @commands.command(name="who-added", aliases=["whoadded"])
    async def who_added(
        self, ctx: Context, emote_id_link_or_name: Annotated[PartialEmote, UserEmoteConverter]
    ) -> None:
        """Get twitch user who added the emote via channel redemption.

        Shortcut for ``!7tv who-added``. Consult the documentation for that command.
        """
        await self.get_who_added(ctx, emote_id_link_or_name)

    #########################################################################################################################
    # 7TV EDITORS
    #########################################################################################################################

    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    @stv.command(name="editors", aliases=["mods"])
    async def stv_editors(self, ctx: Context) -> None:
        """Get 7tv editors for this broadcaster.

        Important lazy quirk! I'm having troubles setting up receiving automatic updates from 7tv for emote / editor
        updates. Currently the bot does NOT automatically fetch 7tv editors information for the streamers.
        So it does NOT automatically update the list of users who can use elevated 7tv commands (such as ``!7tv add``).

        However, this command does - it refreshes the list of 7tv list editors for the broadcaster in the database.
        So if a broadcaster adds/removes a 7tv editor - they should use this command.

        Hopefully, I solve this quirk in future (stop being lazy and at least make an hourly task or better yet solve my
        problems with 7tv websockets)

        This is lazy and it does not check 7tv editor permissions
        (e.g. it's possible to be a 7tv editor without having add/remove emote permissions),
        but I guess, it's safe to assume that 7tv editors are always allowed to add/remove emotes -
        so the bot will allow them to proxy-manage emotes.
        """
        partial_user = ctx.bot.stv.create_partial_user(ctx.broadcaster.id)
        editors = await partial_user.get_stv_mods()

        editor_ids = [editor["platformId"] for editor in editors]
        # Insert new editors
        query = "INSERT INTO ttv_stv_mods (broadcaster_id, editor_id) VALUES ($1, $2) ON CONFLICT DO NOTHING;"
        await self.bot.pool.executemany(query, [(ctx.broadcaster.id, editor_id) for editor_id in editor_ids])
        content = " \N{BULLET} ".join([editor["platformDisplayName"] or "unknown_user" for editor in editors])
        await ctx.send(f"{content} {self.EMOTE}")

        # Delete old editors
        query = "DELETE FROM ttv_stv_mods WHERE broadcaster_id = $1 AND editor_id <> ALL($2::text[])"
        await self.bot.pool.execute(query, ctx.broadcaster.id, editor_ids)

    #########################################################################################################################
    # 7TV USER SETTINGS
    #########################################################################################################################

    @stv.group(name="settings", invoke_fallback=True)
    async def stv_settings(self, ctx: Context) -> None:
        """Group command for `!7tv settings`.

        These commands manage 7tv settings channel points reward and related emotes.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

    @is_broadcaster_dev_or_editor()
    @stv_settings.command(name="allow-common-words", aliases=["allowcommonwords"])  # cSpell: ignore: allowcommonwords
    async def stv_settings_allowcommonwords(self, ctx: Context, new_state: bool | None = None) -> None:  # ruff: ignore[boolean-type-hint-positional-argument]
        """Set whether common words are allowed to be emote aliases in this stream.

        Parameters
        ----------
        new_state
            Optional, boolean-like value, e.g. "yes", "no", "true", "false".
            If omitted, then the command will show current state of ``allow-common-words`` setting in the stream.
        """
        if new_state is None:
            # show status
            allow_common_words: bool = await self.select_allow_common_words(ctx.broadcaster.id)
            content = (
                f"Common words are {'allowed' if allow_common_words else 'not allowed'} "
                f"for 7tv emote aliases in this stream {self.EMOTE}"
            )
            await ctx.send(content)
            return

        # Set new_state
        query = "UPDATE ttv_stv_users SET allow_common_words = $1 WHERE broadcaster_id = $2;"
        await self.bot.pool.execute(query, new_state, ctx.broadcaster.id)
        await ctx.send(f"Changed allow-common-words setting to '{new_state!s}' {self.EMOTE}")


class SevenTVDevOnly(DevComponent):
    """Developer Only commands related to SevenTV features.

    Just some easy testing commands.
    """

    BALLS: ClassVar[dict[str, str]] = {
        # cSpell: disable
        "Blue": "01J8FC6EN0000DNWJ3ST67HH38",
        "Teal": "01J8FCA6RR0004HJ8DYSFE2PF2",
        "Purple": "01J8FCAY6R0006NP3M7JY4GDAA",
        "Yellow": "01J8FCBGRG000A5QBDAQ50YRYC",
        "Orange": "01J8FCC2B00005G1FWF2H9XPCE",
        "Pink": "01J8FCG750000D15QN0BDGKN3A",
        "Olive": "01J8FCGXKR000E0691W9XKC6X0",
        "LightBlue": "01J8FCHF68000E0691W9XKC6X5",
        "DarkGreen": "01J8FCHZSG000C93G7AYMMNCBC",
        "Brown": "01J8FCK00R0006NP3M7JY4GDB0",
        # cSpell: enable
    }

    @commands.command()
    async def balls(self, ctx: Context) -> None:
        """Balls."""
        content = " ".join(f"{k} {v}" for k, v in self.BALLS.items())
        await ctx.send(content)

    @commands.command(aliases=["dev_reset_cycle"])
    async def dev_cycle_reset(self, ctx: Context) -> None:
        """Developer command for temporary reset / testing.

        This
        * sets @Irene's `emote_limit` to 2;
        * removes all current @Irene's cycling emotes;
        * removes color emotes (Blue, Teal, Yellow, etc.) from Irene's active emote set;
        """
        query = "UPDATE ttv_stv_cycle_rewards SET emote_limit = $1 WHERE broadcaster_id = $2;"
        await self.bot.pool.execute(query, 2, const.UserID.Irene)

        query = "DELETE FROM ttv_stv_cycle_emotes tce WHERE tce.broadcaster_id = $1;"
        await self.bot.pool.execute(query, const.UserID.Irene)

        partial_emote_set = ctx.bot.stv.create_partial_emote_set(const.StvID.IRENE_EMOTE_SET)
        for emote_id in self.BALLS.values():
            with contextlib.suppress(EmoteNotFoundError):
                await partial_emote_set.remove_emote(emote_id)
        await ctx.send(f"Done {const.Stv.DonkCrayon}")


async def setup(bot: Bot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(SevenTVPublic(bot))
    await bot.add_component(SevenTVDevOnly(bot))
