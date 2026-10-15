"""Seven TV Public Features.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import re
from collections import defaultdict
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal, TypedDict, override

import twitchio
from discord.utils import copy_doc

# from stv_event_api import SevenTVWebSocket
# from stv_event_api.models import (
#     Dispatch,
#     EventType,
#     ResponseTypes,
#     SubscriptionCondition,
#     SubscriptionData,
# )
from twitchio.ext import commands

from core import IrePublicComponent, ireloop
from shared import clock, errors, ut
from shared.concepts.logs import PrefixLoggerAdapter
from shared.globs import DIGITS, Global7TV
from shared.seven_tv_gql import exceptions as stv_errors
from shared.seven_tv_gql.models import PartialEmote, PartialEmoteSet
from utils import const, guards

if TYPE_CHECKING:
    from core import IreBot, IreContext
    from shared.seven_tv_gql import GraphQL7TVClient

    # class BatchLastYearEntry(TypedDict):
    #     emote_id: int
    #     guild_id: int
    #     author_id: int
    #     used: str  # isoformat

    #########################################################################################################################
    # DATABASE QUERY ROW TYPE-HINTS
    #########################################################################################################################

    class ValidateIsEmoteBlacklistedQueryRow(TypedDict):
        emote_id: str
        blacklisted_at: datetime.datetime
        hours: int

    class CycleStatusQueryRow(TypedDict):
        reward_id: str
        emote_limit: int
        emote_count: int
        emote_set_id: str

    class PermanentStatusQueryRow(TypedDict):
        reward_id: str
        emote_set_id: str


__all__ = ("SevenTVFeatures",)

log = PrefixLoggerAdapter(logging.getLogger(__name__), "🤯")
log.setLevel(logging.DEBUG)

type PartialEmoteAndAlias = tuple[PartialEmote, str | None]

#############################################################################################################################
# CONSTANTS AND ENUMS
#############################################################################################################################


class OwnershipEnum(StrEnum):
    """Emote ownership enum."""

    broadcaster_dev_or_editor = "broadcaster_dev_or_editor"
    chatter = "chatter"


# fmt: off
# taken and edited from https://github.com/FrankerFaceZ/Add-Ons/blob/master/src/no-bad-emotes/common.json
# Removed: boat
# Added: color
# You can use pprint to print the list in a shortened way:
#     import pprint
#     pprint.pprint(COMMON_WORDS, width=125, compact=True)
COMMON_WORDS = frozenset((
'a', 'able', 'about', 'absolute', 'accept', 'account', 'achieve', 'across', 'act', 'active', 'actual', 'add', 'address',
'admit', 'advertise', 'affect', 'afford', 'after', 'afternoon', 'again', 'against', 'age', 'agent', 'ago', 'agree', 'air',
'all', 'allow', 'almost', 'along', 'already', 'alright', 'also', 'although', 'always', 'america', 'amount', 'and', 'ant',
'antenna', 'another', 'answer', 'any', 'angry', 'apart', 'apparent', 'appear', 'apply', 'appoint', 'approach',
'appropriate', 'area', 'argue', 'arm', 'around', 'arrange', 'art', 'as', 'ask', 'associate', 'assume', 'at', 'attend',
'authority', 'available', 'aware', 'away', 'awful', 'baby', 'back', 'bad', 'bag', 'balance', 'ball', 'bank', 'bar', 'base',
'basis', 'be', 'bear', 'beat', 'beauty', 'because', 'become', 'bed', 'before', 'begin', 'behind', 'believe', 'benefit',
'best', 'bet', 'between', 'big', 'bill', 'binoculars', 'birth', 'bit', 'black', 'bloke', 'blood', 'blow', 'blue', 'board',
'body', 'book', 'both', 'bother', 'bottle', 'bottom', 'box', 'boy', 'break', 'brief', 'brilliant', 'bring', 'britain',
'brother', 'budget', 'build', 'bus', 'business', 'busy', 'but', 'buy', 'by', 'bye', 'cake', 'call', 'can', 'car', 'card',
'care', 'carry', 'case', 'cat', 'catch', 'cause', 'cent', 'centre', 'certain', 'chair', 'chairman', 'chance', 'change',
'chap', 'character', 'charge', 'cheap', 'check', 'chicken', 'child', 'choice', 'choose', 'christ', 'christmas', 'church',
'city', 'claim', 'class', 'classic', 'clean', 'clear', 'client', 'clock', 'close', 'closes', 'clothe', 'club', 'coffee',
'cold', 'colleague', 'collect', 'college', 'color', 'colour', 'come', 'comment', 'commit', 'committee', 'common',
'community', 'company', 'compare', 'complete', 'compute', 'concern', 'conch', 'condition', 'confer', 'consider', 'consult',
'contact', 'continue', 'contract', 'control', 'converse', 'cook', 'copy', 'corner', 'correct', 'cost', 'could', 'council',
'count', 'country', 'county', 'couple', 'course', 'court', 'cover', 'create', 'cross', 'cup', 'current', 'cut', 'dad',
'danger', 'date', 'day', 'dead', 'deal', 'dear', 'debate', 'decide', 'decision', 'deep', 'definite', 'degree', 'department',
'depend', 'describe', 'design', 'detail', 'develop', 'die', 'difference', 'difficult', 'dinner', 'direct', 'disbelief',
'discuss', 'district', 'divide', 'do', 'doctor', 'document', 'dog', 'door', 'double', 'doubt', 'down', 'draw', 'dress',
'drink', 'drive', 'drop', 'dry', 'due', 'during', 'each', 'early', 'east', 'easy', 'eat', 'economy', 'educate', 'effect',
'egg', 'eight', 'either', 'elect', 'electric', 'eleven', 'else', 'employ', 'encourage', 'end', 'engine', 'english', 'enjoy',
'enough', 'enter', 'environment', 'equal', 'especial', 'europe', 'even', 'evening', 'ever', 'every', 'evidence', 'exact',
'example', 'except', 'excuse', 'exercise', 'exist', 'expect', 'expense', 'experience', 'explain', 'express', 'exquisite',
'extra', 'eye', 'face', 'fact', 'fair', 'fall', 'family', 'far', 'farm', 'fast', 'father', 'favour', 'feed', 'feel', 'few',
'field', 'fight', 'figure', 'file', 'fill', 'film', 'final', 'finance', 'find', 'fine', 'finish', 'fire', 'first', 'fish',
'fishing', 'fit', 'five', 'flat', 'flash', 'flashback', 'flirt', 'floor', 'fly', 'follow', 'food', 'foot', 'for', 'force',
'forget', 'form', 'fortune', 'forward', 'four', 'france', 'free', 'friday', 'friend', 'from', 'front', 'full', 'fun',
'function', 'fund', 'further', 'future', 'game', 'garden', 'gas', 'gaze', 'general', 'germany', 'get', 'girl', 'give',
'glass', 'go', 'god', 'good', 'goodbye', 'govern', 'grand', 'grant', 'great', 'green', 'ground', 'group', 'grow', 'guess',
'guy', 'hack', 'hacking', 'hair', 'half', 'hall', 'hand', 'hang', 'happen', 'happy', 'hard', 'hate', 'have', 'he', 'head',
'health', 'hear', 'heart', 'heat', 'heavy', 'hell', 'hello', 'help', 'here', 'hi', 'high', 'history', 'hit', 'hold',
'holiday', 'home', 'honest', 'hope', 'horse', 'hospital', 'hot', 'hour', 'house', 'how', 'however', 'hullo', 'hundred',
'husband', 'idea', 'identify', 'idiot', 'if', 'imagine', 'important', 'improve', 'in', 'include', 'income', 'increase',
'indeed', 'individual', 'industry', 'inform', 'inside', 'instead', 'insure', 'interest', 'into', 'intro', 'introduce',
'invest', 'involve', 'issue', 'it', 'item', 'jesus', 'job', 'join', 'judge', 'jump', 'just', 'keep', 'key', 'kid', 'kill',
'kind', 'king', 'kitchen', 'knock', 'know', 'labour', 'lad', 'lady', 'land', 'language', 'large', 'last', 'late', 'laugh',
'law', 'lay', 'lead', 'learn', 'leave', 'left', 'leg', 'less', 'let', 'letter', 'level', 'lie', 'life', 'light', 'like',
'likely', 'limit', 'line', 'link', 'list', 'listen', 'listening', 'little', 'live', 'load', 'local', 'lock', 'london',
'long', 'look', 'lord', 'lose', 'lot', 'love', 'low', 'luck', 'lunch', 'machine', 'main', 'major', 'make', 'man', 'manage',
'many', 'mark', 'market', 'marry', 'match', 'matter', 'maw', 'may', 'maybe', 'mean', 'meaning', 'measure', 'meow', 'meet',
'member', 'mention', 'middle', 'might', 'mile', 'milk', 'million', 'mind', 'minister', 'minus', 'minute', 'miss', 'mister',
'mitosis', 'mod', 'mods', 'modding', 'moderator', 'moderators', 'moment', 'monday', 'money', 'month', 'more', 'morning',
'most', 'mother', 'motion', 'move', 'mrs', 'much', 'music', 'must', 'name', 'nation', 'nature', 'near', 'necessary', 'need',
'never', 'new', 'news', 'next', 'nice', 'night', 'nine', 'no', 'non', 'none', 'normal', 'north', 'not', 'note', 'notes',
'notice', 'now', 'number', 'observe', 'observing', 'obvious', 'occasion', 'odd', 'of', 'off', 'offer', 'office', 'often',
'ok', 'okay', 'old', 'on', 'once', 'one', 'only', 'open', 'operate', 'opportunity', 'oppose', 'or', 'orange', 'order',
'organize', 'original', 'other', 'otherwise', 'ought', 'out', 'over', 'own', 'pack', 'pain', 'page', 'paint', 'pair',
'panic', 'paper', 'paragraph', 'pardon', 'parent', 'park', 'part', 'particular', 'party', 'pass', 'past', 'pay', 'pence',
'pension', 'people', 'per', 'percent', 'perfect', 'perhaps', 'period', 'person', 'photograph', 'pick', 'picture', 'piece',
'place', 'plan', 'play', 'please', 'plus', 'point', 'police', 'policy', 'politic', 'poor', 'position', 'positive',
'possible', 'post', 'pound', 'power', 'practice', 'practise', 'prepare', 'present', 'press', 'pressure', 'presume', 'pretty',
'previous', 'price', 'prince', 'princess', 'print', 'private', 'probable', 'problem', 'proceed', 'process', 'produce',
'product', 'programme', 'project', 'proper', 'propose', 'protect', 'provide', 'public', 'pull', 'purpose', 'push', 'put',
'quality', 'quarter', 'question', 'quick', 'quid', 'quiet', 'quite', 'radio', 'rail', 'raise', 'range', 'rate', 'rather',
'react', 'reacting', 'read', 'ready', 'real', 'realise', 'realize', 'really', 'reason', 'receive', 'recent', 'reckon',
'recognize', 'recommend', 'record', 'recording', 'red', 'reduce', 'refer', 'regard', 'region', 'regret', 'relation',
'remember', 'report', 'represent', 'require', 'research', 'resource', 'respect', 'responsible', 'rest', 'result', 'return',
'rid', 'right', 'ring', 'rise', 'road', 'role', 'roll', 'room', 'round', 'rule', 'run', 'safe', 'sale', 'same', 'saturday',
'save', 'say', 'scare', 'scared', 'scheme', 'school', 'science', 'score', 'scotland', 'seat', 'second', 'secretary',
'section', 'secure', 'see', 'seem', 'self', 'sell', 'send', 'sense', 'separate', 'serious', 'serve', 'service', 'set',
'settle', 'seven', 'sex', 'shall', 'share', 'she', 'sheet', 'shoe', 'shoot', 'shop', 'short', 'should', 'show', 'shut',
'sick', 'side', 'sign', 'similar', 'simple', 'since', 'sing', 'single', 'sir', 'sister', 'sit', 'sitting', 'site', 'situate',
'six', 'size', 'sleep', 'slight', 'slow', 'small', 'smoke', 'sneak', 'sneaking', 'so', 'social', 'society', 'some', 'son',
'soon', 'sorry', 'sort', 'sound', 'south', 'space', 'speak', 'special', 'specific', 'speed', 'spell', 'spend', 'square',
'staff', 'stage', 'stairs', 'stand', 'standard', 'start', 'state', 'station', 'stay', 'step', 'stick', 'still', 'stop',
'story', 'straight', 'strategy', 'street', 'strike', 'strong', 'structure', 'student', 'study', 'stuff', 'stupid', 'subject',
'succeed', 'such', 'sudden', 'suggest', 'suit', 'summer', 'sun', 'sunday', 'supply', 'support', 'suppose', 'sure',
'surprise', 'switch', 'system', 'table', 'take', 'talk', 'tape', 'tax', 'tea', 'teach', 'team', 'telephone', 'television',
'tell', 'ten', 'tend', 'term', 'terrible', 'test', 'than', 'thank', 'the', 'then', 'there', 'therefore', 'they', 'thing',
'think', 'thirteen', 'thirty', 'this', 'thou', 'though', 'thousand', 'three', 'through', 'throw', 'thursday', 'tie', 'time',
'timeout', 'to', 'today', 'together', 'tomorrow', 'tonight', 'too', 'top', 'total', 'touch', 'toward', 'town', 'trade',
'traffic', 'train', 'transport', 'travel', 'treat', 'tree', 'trouble', 'true', 'trust', 'try', 'tuesday', 'turn', 'twelve',
'twenty', 'two', 'type', 'under', 'understand', 'union', 'unit', 'unite', 'university', 'unless', 'until', 'up', 'upon',
'use', 'usual', 'value', 'various', 'very', 'vibe', 'vibing', 'video', 'view', 'village', 'visit', 'voice', 'voices',
'vote', 'wage', 'wait', 'waiting', 'walk', 'walking', 'wall', 'want', 'war', 'warm', 'warn', 'warning', 'wash', 'waste',
'watch', 'watching', 'water', 'way', 'we', 'wear', 'wednesday', 'wee', 'week', 'weigh', 'welcome', 'well', 'west', 'what',
'when', 'where', 'whether', 'which', 'while', 'white', 'who', 'whole', 'why', 'wide', 'wife', 'will', 'win', 'wind',
'window', 'wish', 'with', 'within', 'without', 'woman', 'wonder', 'wood', 'woof', 'word', 'work', 'world', 'worry', 'worse',
'worth', 'would', 'wow', 'write', 'wrong', 'year', 'yes', 'yesterday', 'yet', 'yellow', 'yo', 'you', 'young')
)
# fmt: on


#############################################################################################################################
# USER INPUT PARSERS
#############################################################################################################################


def regex_to_emote(stv_gql: GraphQL7TVClient, emote_id_or_link: str) -> PartialEmote:
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

    Raises
    ------
    errors.BadUserInputError
        Could not parse emote id / emote link.
    """
    search = re.search(
        # Valid 7tv ids are
        # * new format - ULID format: [0-7][0-9A-HJKMNP-TV-Z]{25}
        # * old format - MongoDB ObjectID format: [0-9a-fA-F]{24}
        pattern=r"(?P<emote_id>[0-7][0-9A-HJKMNP-TV-Z]{25}|[0-9a-fA-F]{24})",
        string=emote_id_or_link,
    )
    if search is None:
        msg = "Bad <emote_id_or_link>, check the input"
        raise errors.BadUserInputError(msg)
    return PartialEmote(stv_gql, search["emote_id"])


async def parse_or_search_emote(
    stv_gql: GraphQL7TVClient, emote_id_link_or_name: str, broadcaster_id: str | None
) -> PartialEmote:
    """Parse or search."""
    try:
        # try parsing `emote_id`
        return regex_to_emote(stv_gql, emote_id_link_or_name)
    except errors.BadUserInputError:
        # `emote_name` was provided to search
        if broadcaster_id is not None:
            # search within the broadcaster
            user = stv_gql.create_partial_user(broadcaster_id)
            return await user.search_emote(emote_id_link_or_name)
        # search top globally
        return await stv_gql.search_emote(emote_id_link_or_name)


async def parse_add_rename_input(
    stv_gql: GraphQL7TVClient,
    user_input: str,
    broadcaster_id: str | None = None,
) -> PartialEmoteAndAlias:
    """Get emote_id from `user_input`.

    Parameters
    ----------
    stv_gql
        SevenTV GraphQL client
    user_input
        User input
    broadcaster_id
        If provided then the 7tv client will search for the emote within the user emotes, if not - it will search globally.
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

    emote = await parse_or_search_emote(stv_gql, split[0], broadcaster_id)
    return (emote, emote_alias)


async def parse_remove_input(
    stv_gql: GraphQL7TVClient,
    user_input: str,
    broadcaster_id: str,
) -> PartialEmote:
    """Get emote_id from `user_input`."""
    split = user_input.split()
    if len(split) > 1:
        msg = "Bad Input; I require '<emote_link_or_id>' - no extra words"
        raise errors.BadUserInputError(msg)
    if len(split) <= 0:
        msg = "Bad Input; why would you type an empty text?"
        raise errors.BadUserInputError(msg)

    return await parse_or_search_emote(stv_gql, split[0], broadcaster_id)


#############################################################################################################################
# ARGUMENT CONVERTERS
#############################################################################################################################


class RenameEmoteConverter(commands.Converter[PartialEmoteAndAlias]):
    """Seven TV Emote Converter.

    Converts user_input from `str` type into 7TV emote_id.

    Format: ``<user_emote_id_name_or_link> <new_alias>`` -> emote, alias
    """

    @override
    async def convert(self, ctx: IreContext, user_input: str) -> PartialEmoteAndAlias:  # ty: ignore[invalid-method-override]
        """Convert `user_input` to 7TV emote_id."""
        return await parse_add_rename_input(ctx.bot.stv, user_input, ctx.broadcaster.id)


class AddEmoteConverter(commands.Converter[PartialEmoteAndAlias]):
    """Seven TV Emote Converter.

    Converts user_input from `str` type into 7TV emote_id.

    Format: ``<global_emote_id_name_or_link> <alias>`` -> emote, alias
    """

    @override
    async def convert(self, ctx: IreContext, user_input: str) -> PartialEmoteAndAlias:  # ty: ignore[invalid-method-override]
        """Convert `user_input` to 7TV emote_id."""
        return await parse_add_rename_input(ctx.bot.stv, user_input)


class RemoveEmoteConverter(commands.Converter[PartialEmote]):
    """Seven TV Emote Converter.

    Converts user_input from `str` type into 7TV emote_id.

    Format: ``<user_emote_id_name_or_link>`` -> emote
    """

    @override
    async def convert(self, ctx: IreContext, user_input: str) -> PartialEmote:  # ty: ignore[invalid-method-override]
        """Convert `user_input` to 7TV emote_id."""
        return await parse_remove_input(ctx.bot.stv, user_input, ctx.broadcaster.id)


#############################################################################################################################
# GUARDS
#############################################################################################################################


async def _is_broadcaster_dev_or_editor_predicate(ctx: IreContext) -> Literal[True]:
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

    def predicate(_: IreContext) -> Literal[True]:
        return True

    return commands.guard(predicate)


#############################################################################################################################
# COMPONENT
#############################################################################################################################


class SevenTVFeatures(IrePublicComponent):
    """Cycling Emotes."""

    EMOTE = Global7TV.FeelsDankMan

    def __init__(self, bot: IreBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)

        self.cache_permanent_reward_ids: set[str] = set()
        self.cache_cycle_reward_ids: set[str] = set()
        self.cache_blacklist_reward_ids: set[str] = set()
        self.caches_ready: asyncio.Event = asyncio.Event()

        # stats
        # self._batch_total: defaultdict[int, Counter[int]] = defaultdict(Counter)
        # self._batch_last_year: list[BatchLastYearEntry] = []
        # self._batch_lock = asyncio.Lock()
        # self.bulk_insert.add_exception_type(asyncpg.PostgresConnectionError)

    # async def ws_callback(data: ResponseTypes) -> None:
    #     """7TV WebSocket Callback.

    #     When emotes get deleted - they should be deleted from the bot's database too.
    #     """
    #     if not isinstance(data, Dispatch):
    #         return
    #     if data.type != EventType.EMOTE_SET_UPDATE:
    #         return

    #     # log.debug("7TV WebSocket %s", data)

    #     if data.body.pulled:
    #         # Emote Deleted
    #         for pulled in data.body.pulled:
    #             query = "DELETE FROM ttv_stv_cycle_emotes WHERE emote_id = $1 AND emote_set_id = $2;"
    #             emote_id: str = pulled.old_value["id"]
    #             emote_set_id = data.body.id

    #             await self.bot.pool.execute(query, emote_id, emote_set_id)

    # self.stv_ws = SevenTVWebSocket(callback=ws_callback, websocket_url="wss://events.7tv.io/v3/")

    # async def stv_ws_subscribe(self, emote_set_id: str) -> None:
    #     """Make 7TV WebSocket Subscription."""
    #     condition = SubscriptionCondition(object_id=emote_set_id)  # your emote-set id
    #     subscription = SubscriptionData(subscription_type=EventType.EMOTE_SET_ALL, condition=condition)
    #     await self.stv_ws.subscribe(subscription_data=subscription)

    # async def stv_ws_multi_subscribe(self) -> None:
    #     """Make 7TV WebSocket Subscriptions."""
    #     query = "SELECT DISTINCT emote_set_id FROM ttv_stv_users;"
    #     for (emote_set_id,) in await self.bot.pool.fetch(query):
    #         await self.stv_ws_subscribe(emote_set_id)

    @override
    async def component_load(self) -> None:
        # await self.stv_ws.connect()
        # await self.stv_ws_multi_subscribe()
        self.fill_caches.start()

        self.double_check_reward_redemptions_queues.start()
        self.double_check_cycle_emotes_existence.start()
        self.expire_blacklisted_emotes.start()
        # self.bulk_insert.start()
        # self.clean_up_old_records.start()
        await super().component_load()

    @override
    async def component_teardown(self) -> None:
        # await self.stv_ws.close()
        self.fill_caches.stop()

        self.double_check_reward_redemptions_queues.stop()
        self.double_check_cycle_emotes_existence.stop()
        self.expire_blacklisted_emotes.stop()
        # self.bulk_insert.stop()
        # self.clean_up_old_records.stop()
        await super().component_teardown()

    #########################################################################################################################
    # COMMON TASKS
    #########################################################################################################################

    async def fill_cache_permanent_rewards(self) -> None:
        """Task that fills a set of rewards ids for convenience to cut on a few database queries."""
        query = "SELECT reward_id FROM ttv_stv_permanent_rewards"
        self.cache_permanent_reward_ids = {r for (r,) in await self.bot.pool.fetch(query)}

    async def fill_cache_cycle_rewards(self) -> None:
        """Task that fills a set of rewards ids for convenience to cut on a few database queries."""
        query = "SELECT reward_id FROM ttv_stv_cycle_rewards"
        self.cache_cycle_reward_ids = {r for (r,) in await self.bot.pool.fetch(query)}

    async def fill_cache_blacklist_rewards(self) -> None:
        """Task that fills a set of rewards ids for convenience to cut on a few database queries."""
        query = "SELECT reward_id FROM ttv_stv_blacklist_rewards"
        self.cache_blacklist_reward_ids = {r for (r,) in await self.bot.pool.fetch(query)}

    @ireloop(count=1)
    async def fill_caches(self) -> None:
        """Task to fill caches on startup."""
        await self.fill_cache_permanent_rewards()
        await self.fill_cache_cycle_rewards()
        await self.fill_cache_blacklist_rewards()
        self.caches_ready.set()

    @ireloop(hours=8)
    async def double_check_reward_redemptions_queues(self) -> None:
        """Double-check the reward redemption queues.

        This double-checks the redemption queue for the following channel points rewards:
        * "Add cycle emote"
        * "Remove + blacklist emote"
        * "Add permanent emote"
        """
        for table, method in [
            ("ttv_stv_cycle_rewards", self.process_cycle_redemption),
            ("ttv_stv_blacklist_rewards", self.process_blacklist_redemption),
            ("ttv_stv_permanent_rewards", self.process_permanent_redemption),
        ]:
            query = f"SELECT reward_id, broadcaster_id FROM {table}"  # ruff: ignore[hardcoded-sql-expression]
            for row in await self.bot.pool.fetch(query):
                reward = ut.ni(
                    await self.bot.create_partialuser(row["broadcaster_id"]).fetch_custom_rewards(
                        ids=[row["reward_id"]], manageable=True
                    )
                )
                if reward is None:
                    continue

                async for redemption in reward.fetch_redemptions(status="UNFULFILLED", sort="OLDEST"):
                    try:
                        await method(redemption)
                    except Exception as error:
                        await self.redemption_refund(redemption)
                        if isinstance(
                            error,
                            (
                                stv_errors.UnsatisfyingResultError,
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
        try:
            if isinstance(redemption, twitchio.ChannelPointsRedemptionAdd):
                await redemption.fulfill(token_for=redemption.broadcaster.id)
            else:
                await redemption.fulfill()
        except twitchio.HTTPException:
            log.warning("Failed to fulfil %s", redemption)

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

        try:
            if isinstance(redemption, twitchio.ChannelPointsRedemptionAdd):
                await redemption.refund(token_for=redemption.broadcaster.id)
            else:
                # ``CustomRewardRedemption`` automatically puts proper token
                await redemption.refund()
        except twitchio.HTTPException:
            log.warning("Failed to refund %s", redemption)

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

    async def validate_reward_id(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
        cache: set[str],
    ) -> bool:
        """Validate reward id.

        Also refunds points to Irene because you know, testing costs :D
        """
        await self.caches_ready.wait()  # need cache to be filled.
        if redemption.reward.id not in cache:
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
            SELECT emote_id,
                blacklisted_at,
                (SELECT duration FROM ttv_stv_blacklist_rewards WHERE broadcaster_id = $2) as hours
            FROM ttv_stv_blacklist_emotes
            WHERE emote_id = $1 AND broadcaster_id = $2
        """
        row: ValidateIsEmoteBlacklistedQueryRow | None = await self.bot.pool.fetchrow(query, emote_id, broadcaster_id)
        if row is None:
            # Emote is not blacklisted
            return True

        expire_dt = clock.round_to_next_hour(row["blacklisted_at"] + datetime.timedelta(hours=row["hours"]))
        msg = (
            "The requested emote is blacklisted; "
            f"{clock.human_timedelta(expire_dt, mode='short')} until it is allowed {self.EMOTE}"
        )
        raise errors.NotAllowedError(msg)

    async def validate_is_emote_alias_a_common_word(
        self, broadcaster_id: str, emote_id: str, emote_alias: str | None = None
    ) -> Literal[True]:
        """Validate whether the emote alias is a common word (if common words are not allowed to be used as emote aliases).

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
            msg = "Common words are not allowed to be used as emote aliases for this emote set"
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

    def validate_cycle_emote_limit(self, new_limit: int) -> None:
        """Validate whether emote_limit is above 0."""
        if new_limit < 1:
            msg = "Not allowed to have emote limit below 1"
            raise errors.RespondWithError(msg)

    #########################################################################################################################
    # MAIN COMMAND
    #########################################################################################################################

    @commands.group(name="7tv", aliases=["stv"], invoke_fallback=True)
    async def stv(self, ctx: IreContext) -> None:
        """Group command for `!7tv`.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

    #########################################################################################################################
    # ADD PERMANENT EMOTE CHANNEL POINTS REWARD
    #########################################################################################################################

    @stv.group(name="permanent", invoke_fallback=True)
    async def stv_permanent(self, ctx: IreContext) -> None:
        """Group command for `!7tv permanent`.

        These commands manage "Add Permanent Emote" channel points reward.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

    @guards.is_broadcaster_or_dev()
    @stv_permanent.command(name="create")
    async def stv_permanent_create(self, ctx: IreContext) -> None:
        """Create 'Add Permanent Emote' channel points reward.

        The bot will listen to the redemptions of this reward and process them to add permanent 7tv emotes.

        A few notes about the created channel points reward:

        * It accepts user input in a format ``<emote_id_link_or_name> <emote_alias>``.
        * If emote name is provided (instead of emote id or emote link within ``<emote_id_link_or_name>``) then
          the bot will search for the most popular emote in 7tv matching it.
        * If ``<emote_alias>`` is also provided then the specified emote will be added with an alias.

          Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF smh" will add the "MinaSmh" emote as "smh".

        """
        custom_reward = await ctx.broadcaster.create_custom_reward(
            # This prompt can be 45 characters max
            title="Add 7TV emote",
            cost=10,
            prompt=(
                # This prompt can be 200 characters max
                "Give me a 7TV emote link or emote ID. Optionally, type an emote alias. "
                'Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF SMH"'
            ),
        )

        query = """
            INSERT INTO ttv_stv_permanent_rewards
            (broadcaster_id, reward_id)
            VALUES ($1, $2)
            ON CONFLICT (broadcaster_id)
                DO UPDATE SET reward_id = $2
            returning broadcaster_id;
        """
        broadcaster_id: str | None = await self.bot.pool.fetchval(query, ctx.broadcaster.id, custom_reward.id)
        if broadcaster_id is None:
            msg = f"This channel already has 7TV emotes permanent channel reward {self.EMOTE}"
            raise errors.RespondWithError(msg)

        await self.fill_cache_permanent_rewards()
        await ctx.send(
            "Created 'Add Permanent emote' channel points reward; "
            "PS. if you want to edit it (e.g. text or color) - visit your creator dashboard "
            f"(dashboard.twitch.tv/u/{ctx.broadcaster.name}/viewer-rewards/channel-points/rewards). "
            f"Just don't remove `Require Viewer to Enter Text`, please {self.EMOTE}",
        )

    @stv_permanent.command(name="status")
    async def stv_permanent_status(self, ctx: IreContext) -> None:
        """Get some information about 'Add Permanent Emote' channel points reward's status."""
        query = """
            SELECT r.reward_id, u.emote_set_id
            FROM ttv_stv_permanent_rewards r
                JOIN ttv_stv_users u ON u.broadcaster_id = r.broadcaster_id
            WHERE u.broadcaster_id = $1;
        """
        row: PermanentStatusQueryRow | None = await self.bot.pool.fetchrow(query, ctx.broadcaster.id)

        if row is None:
            msg = f"The streamer doesn't have 'Add Permanent Emote' channel points reward set up {self.EMOTE}"
            raise errors.RespondWithError(msg)

        reward = next(iter(await ctx.broadcaster.fetch_custom_rewards(ids=[row["reward_id"]])), None)
        if reward is None:
            msg = (
                "Somehow my database has wrong information about the current streamer's 'Add Permanent Emote' reward - "
                f"please, use '!7tv permanent create' to recreate the reward {self.EMOTE}"
            )
            raise errors.RespondWithError(msg)

        content = (
            f"title={reward.title} cost={reward.cost} reward_id={row['reward_id']} "
            f" emote_set_id={row['emote_set_id']} {self.EMOTE}"
        )
        await ctx.send(content)

    async def process_permanent_redemption(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
    ) -> None:
        """Process 'Add Permanent Emote' redemption.

        Errors are handled by global error handler and it refunds the points.
        """
        if not await self.validate_reward_id(redemption, self.cache_permanent_reward_ids):
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

        emote, alias = await parse_add_rename_input(self.bot.stv, redemption.user_input)
        log.debug("Parsed user input: emote_id=%s emote_alias=%s", emote.id, alias)

        # Step 2. Get Emote Set

        emote_set = await self.select_emote_set(redemption.broadcaster.id)
        log.debug("Operating on emote_set #%s", emote_set.id)

        # Step 3. Add the requested emote

        await self.run_add_emote_validators(emote_id=emote.id, broadcaster_id=redemption.broadcaster.id, emote_alias=alias)
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

    @ireloop(hours=8)
    async def double_check_cycle_emotes_existence(self) -> None:
        """Double check database's data.

        For example, if the streamer manually deleted emotes while the bot is offline - then database might have wrong data.
        """
        query = "SELECT emote_id, emote_set_id FROM ttv_stv_cycle_emotes"
        emote_sets = defaultdict[str, list[str]](list)
        for row in await self.bot.pool.fetch(query):
            emote_sets[row["emote_set_id"]].append(row["emote_id"])

        for emote_set_id, emote_ids in emote_sets.items():
            emote_set = PartialEmoteSet(self.bot.stv, emote_set_id)
            all_emotes_ids = [emote.id for emote in await emote_set.fetch_all_emotes()]
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
    async def stv_cycle(self, ctx: IreContext) -> None:
        """Group command for `!7tv cycle`.

        These commands manage 7tv cycle channel points reward and related emotes.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

    @guards.is_broadcaster_or_dev()
    @stv_cycle.command(name="create")
    async def stv_cycle_create(self, ctx: IreContext, emote_limit: int = 10) -> None:
        """Create 'Add Cycle Emote' channel points reward, redeems for which will be and process to add/remove emotes.

        A few notes about the created channel points reward:

        * It accepts user input in a format ``<emote_id_link_or_name> <emote_alias>``.
        * If emote name is provided (instead of emote id or emote link within ``<emote_id_link_or_name>``) then
          the bot will search for the most popular emote in 7tv matching it.
        * If ``<emote_alias>`` is also provided then the specified emote will be added with an alias.

          Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF smh" will add the "MinaSmh" emote as "smh".

        Parameters
        ----------
        emote_limit
            Optional, 10 by default. Upper limit for total amount of cycling emotes.
            When total amount of cycle emote becomes more than this number,
            the bot will have to start deleting the oldest cycle emotes.
        """
        self.validate_cycle_emote_limit(emote_limit)
        custom_reward = await ctx.broadcaster.create_custom_reward(
            # This prompt can be 45 characters max
            title=f"Add 7TV emote ({emote_limit} slots, oldest cycle out)",
            cost=10,
            prompt=(
                # This prompt can be 200 characters max
                "Give me a 7TV emote link or emote ID. Optionally, type an emote alias. "
                'Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF SMH"'
            ),
        )

        query = """
            INSERT INTO ttv_stv_cycle_rewards
            (broadcaster_id, reward_id, emote_limit)
            VALUES ($1, $2, $3)
            ON CONFLICT (broadcaster_id)
                DO UPDATE SET reward_id = $2,
                            emote_limit = $3
            returning broadcaster_id;
        """
        broadcaster_id: str | None = await self.bot.pool.fetchval(query, ctx.broadcaster.id, custom_reward.id, emote_limit)
        if broadcaster_id is None:
            msg = f"This channel already has 7TV emotes cycle channel reward {self.EMOTE}"
            raise errors.RespondWithError(msg)

        await self.fill_cache_cycle_rewards()
        await ctx.send(
            "Created 'Add Cycle Emote' channel points reward; "
            "PS. if you want to edit it (e.g. text or color) - visit your creator dashboard "
            f"(dashboard.twitch.tv/u/{ctx.broadcaster.name}/viewer-rewards/channel-points/rewards). "
            f"Just don't remove `Require Viewer to Enter Text`, please {self.EMOTE}",
        )
        # await self.stv_ws_subscribe(partial_emote_set.id)

    @is_broadcaster_dev_or_editor()
    @stv_cycle.command(name="drop")
    async def stv_cycle_drop(
        self,
        ctx: IreContext,
        emote: Annotated[PartialEmote, RemoveEmoteConverter],
    ) -> None:
        """Drop an emote from the 'Add Cycle Emote' emotes list.

        This drops the emote from the bot's database essentially making it "permanent", leaving it
        up to other 7TV editors (or a broadcaster) to manage it.
        In other words, this command stops the emote from being eventually cycled out.

        Parameters
        ----------
        emote
            ``<emote_name_link_or_id>`` which is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence in after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.

        Examples
        --------
        All these examples below drop same "smh" emote

        * ``!7tv cycle drop 01FP8TR8G8000EJT2EVEY3JQTF``
        * ``!7tv cycle drop smh``
        * ``!7tv cycle drop https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF``
        """
        query = "DELETE FROM ttv_stv_cycle_emotes WHERE emote_id = $1 AND broadcaster_id = $2"
        await self.bot.pool.execute(query, emote.id, ctx.broadcaster.id)
        await ctx.send(f"'{emote.id}' was removed from the cycling emote list {self.EMOTE}")

    @stv_cycle.command(name="status")
    async def stv_cycle_status(self, ctx: IreContext) -> None:
        """Get some information about 'Add Cycle Emote' channel points reward's status."""
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
        row: CycleStatusQueryRow | None = await self.bot.pool.fetchrow(query, ctx.broadcaster.id)

        if row is None:
            msg = f"The streamer doesn't have 7tv emotes cycle channel points reward set up {self.EMOTE}"
            raise errors.RespondWithError(msg)

        reward = next(iter(await ctx.broadcaster.fetch_custom_rewards(ids=[row["reward_id"]])), None)
        if reward is None:
            msg = (
                "Somehow my database has wrong information about the current streamer's 7tv cycle reward - "
                f"please, use '!7tv cycle create' to recreate the reward {self.EMOTE}"
            )
            raise errors.RespondWithError(msg)

        content = (
            f"title={reward.title} cost={reward.cost} reward_id={row['reward_id']} emote_limit={row['emote_limit']} "
            f"emote_count={row['emote_count']} emote_set_id={row['emote_set_id']} {self.EMOTE}"
        )
        await ctx.send(content)

    @is_broadcaster_dev_or_editor()
    @stv_cycle.command(name="limit")
    async def stv_cycle_limit(self, ctx: IreContext, new_limit: int) -> None:
        """Change 'Add Cycle Emote' channel points reward's limit.

        Lowering the limit doesn't trim current 'Add Cycle Emote' emotes pool until the next redemption.

        Parameters
        ----------
        new_limit
            Integer, new limit setting for cycle emote reward.
        """
        self.validate_cycle_emote_limit(new_limit)
        query = """
            UPDATE ttv_stv_cycle_rewards
            SET emote_limit = $1
            WHERE broadcaster_id = $2
            RETURNING (SELECT emote_limit FROM ttv_stv_cycle_rewards WHERE broadcaster_id = $2);
        """
        # TODO: after upgrading to PostgresQL 18 https://stackoverflow.com/a/7927957/19217368
        old_emote_limit = await self.bot.pool.fetchval(query, new_limit, ctx.broadcaster.id)
        await ctx.send(f"Changed emote_limit from {old_emote_limit} to {new_limit} {self.EMOTE}")

    @stv_cycle.command(name="show-emotes", aliases=["all-emotes"])
    async def stv_cycle_showemotes(self, ctx: IreContext) -> None:
        """Show all cycle emote rewards for the streamer."""
        query = "SELECT emote_id FROM ttv_stv_cycle_emotes WHERE broadcaster_id = $1;"
        emote_ids = [e for (e,) in await self.bot.pool.fetch(query, ctx.broadcaster.id)]
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        emote_set_emotes = await emote_set.fetch_all_emotes()
        cycle_emotes = [emote.alias for emote in emote_set_emotes if emote.id in emote_ids]
        content = f"Total: {len(cycle_emotes)}; " + " ".join(cycle_emotes)
        await ctx.chunk_send(content)

    @is_broadcaster_dev_or_editor()
    @stv_cycle.command(name="allow-common-words", aliases=["allowcommonwords"])  # cSpell: ignore: allowcommonwords
    async def stv_cycle_allowcommonwords(self, ctx: IreContext, *, new_state: bool | None = None) -> None:
        """Set whether common words are allowed to be emote aliases in this stream.

        Parameters
        ----------
        new_state
            Optional, boolean-like value, e.g. "yes", "no", "true", "false".
            If omitted, then the command will show current state of ``allow-common-words`` setting in the stream.
        """
        if new_state is None:
            # show status
            query = "SELECT allow_common_words FROM ttv_stv_users WHERE broadcaster_id = $1;"
            allow_common_words: bool = await self.bot.pool.fetchval(query, ctx.broadcaster.id)
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

    async def process_cycle_redemption(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
    ) -> None:
        """Process 'Add Cycle Emote' Redemption.

        Errors are handled by global error handler and it refunds the points.
        """
        if not await self.validate_reward_id(redemption, self.cache_cycle_reward_ids):
            return

        # shortcuts
        broadcaster_id = redemption.broadcaster.id

        log.debug(
            "User @%s (%s) requested cycle-emote at broadcaster @%s (%s) with input: '%s'",
            redemption.user.display_name,
            redemption.user.id,
            redemption.broadcaster.display_name,
            broadcaster_id,
            redemption.user_input,
        )

        # Step 1. Parse User Input
        emote, alias = await parse_add_rename_input(self.bot.stv, redemption.user_input)
        log.debug("Parsed user input: emote_id=%s emote_alias=%s", emote.id, alias)

        # Step 2. Get Emote Set
        emote_set = await self.select_emote_set(broadcaster_id)
        log.debug("Operating on emote_set #%s", emote_set.id)

        # Step 3. Need to validate the emote before attempting to remove
        await self.run_add_emote_validators(emote_id=emote.id, broadcaster_id=redemption.broadcaster.id, emote_alias=alias)

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
        emote_ids_to_remove: list[str] = [r for (r,) in await self.bot.pool.fetch(query, broadcaster_id, emote_set.id)]
        log.debug("Removing emotes #%s", emote_ids_to_remove)

        for emote_id_to_remove in emote_ids_to_remove:
            try:
                await emote_set.remove_emote(emote_id=emote_id_to_remove)
            except stv_errors.EmoteNotFoundError:
                log.debug("Emote Not Found #%s - skipping", emote_id_to_remove)
            else:
                await self.delete_from_cycle_emotes(emote_id_to_remove, emote_set.id)
                log.debug("Removed emote %s", emote_id_to_remove)

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

    #########################################################################################################################
    # DEVELOPER TESTING COMMANDS                                                                                            #
    #########################################################################################################################

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

    @guards.is_dev()
    @commands.command()
    async def balls(self, ctx: IreContext) -> None:
        """Balls."""
        content = " ".join(f"{k} {v}" for k, v in self.BALLS.items())
        await ctx.send(content)

    @guards.is_dev()
    @commands.command(aliases=["dev_reset_cycle"])
    async def dev_cycle_reset(self, ctx: IreContext) -> None:
        """Developer command for temporary reset / testing.

        This
        * sets @Irene's `emote_limit` to 2;
        * removes all current @Irene's cycling emotes;
        * removes color emotes (Blue, Teal, Yellow, etc) from Irene's active emote set;
        """
        query = "UPDATE ttv_stv_cycle_rewards SET emote_limit = $1 WHERE broadcaster_id = $2;"
        await self.bot.pool.execute(query, 2, const.UserID.Irene)

        query = "DELETE FROM ttv_stv_cycle_emotes tce WHERE tce.broadcaster_id = $1;"
        await self.bot.pool.execute(query, const.UserID.Irene)

        partial_emote_set = ctx.bot.stv.create_partial_emote_set(const.SevenTV.IRENE_EMOTE_SET_ID)
        for emote_id in self.BALLS.values():
            with contextlib.suppress(stv_errors.EmoteNotFoundError):
                await partial_emote_set.remove_emote(emote_id)
        await ctx.send(f"Done {const.STV.DonkCrayon}")

    #########################################################################################################################
    # 7TV EDITOR STATUS / ACCEPT                                                                                            #
    #########################################################################################################################

    @stv.group(name="editor", invoke_fallback=True)
    async def stv_editor(self, ctx: IreContext) -> None:
        """Editor Group."""
        await ctx.group_default_response()

    @stv_editor.command(name="status", aliases=["check"])
    async def stv_editor_status(self, ctx: IreContext) -> None:
        """Show some debug information about state of 7TV editor request for the streamer."""
        partial_user = ctx.bot.stv.create_partial_user(ctx.broadcaster.id)
        editor_for = await partial_user.check_bot_editor()

        if not editor_for.is_enough_permissions:
            content = f"7tv editor invite doesn't have required permissions (it needs 'Emote Sets > Manage') {self.EMOTE}"
        elif editor_for.state != "ACCEPTED":
            content = (
                f"7tv editor invite permissions are okay, invite state={editor_for.state}, "
                f"please use '{ctx.prefix}7tv editor accept' command to make the bot accept it {self.EMOTE}"
            )
        else:
            content = f"7tv editor invite is accepted and permissions are good {self.EMOTE}"
        await ctx.send(content)

    @stv_editor.command(name="guide")
    async def stv_editor_guide(self, ctx: IreContext) -> None:
        """Send a small guide on how to make the bot your 7TV editor.

        Practically a TL;DR of the "Attention" admonition from above.
        """
        content = (
            f"{DIGITS[1]} Go to 7tv.app/settings/editors "
            f"{DIGITS[2]} Add Editor > @IrenesBot, make sure 'Emote Sets > Manage' permission is given "
            f"{DIGITS[3]} Use '{ctx.prefix}7tv editor accept' command to make the bot accept the editor role {self.EMOTE}"
        )
        await ctx.send(content)

    @guards.is_broadcaster_or_dev()
    @stv_editor.command(name="accept")
    async def stv_editor_accept(self, ctx: IreContext) -> None:
        """Make the bot accept a pending 7TV editor request from the streamer.

        Invoking this command also makes the bot attach to your currently active 7tv emote set.
        Which is identical to performing ``!7tv emoteset attach`` with no arguments.
        """
        partial_user = ctx.bot.stv.create_partial_user(ctx.broadcaster.id)
        res = await partial_user.accept_editor()
        insert_response = await self.insert_into_stv_users(ctx.broadcaster.id)
        content = f"Just {res.lower()} your 7TV editor request; also {insert_response} {self.EMOTE}"
        await ctx.send(content)

    #########################################################################################################################
    # 7TV EMOTESET                                                                                                          #
    #########################################################################################################################

    @stv.group(name="emoteset", invoke_fallback=True)
    async def stv_emoteset(self, ctx: IreContext) -> None:
        """Emote Set Group."""
        await ctx.group_default_response()

    @guards.is_broadcaster_or_dev()
    @stv_emoteset.command(name="attach")
    async def stv_emoteset_attach(self, ctx: IreContext, emote_set_id: str | None = None) -> None:
        """Attach bot's 7tv features to the emote set.

        Parameters
        ----------
        emote_set_id
            Optional, 7TV emote set id for the bot to attach to.
            If not provided - the bot will attach to streamer's currently active emote set.
            Due to my laziness this doesn't accept emote set links, so please, copy only ID part form the emote set's URL.
        """
        insert_response = await self.insert_into_stv_users(ctx.broadcaster.id, emote_set_id=emote_set_id)
        await ctx.send(f"Successfully {insert_response}")

    @stv_emoteset.command(name="status")
    async def stv_emoteset_status(self, ctx: IreContext) -> None:
        """Show some debug information about currently attached 7tv emote set."""
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        await ctx.send(f"{emote_set!r} {self.EMOTE}")

    #########################################################################################################################
    # 7TV EMOTE MANAGEMENT                                                                                                  #
    #########################################################################################################################

    async def add_helper(self, ctx: IreContext, emote_and_alias: PartialEmoteAndAlias) -> None:
        """Add 7TV emote helper.

        Note that this doesn't use `self.emote_set_add_with_validations` because "!7tv add" commands are
        supposed to be restricted to the broadcaster, developer and 7tv editors only.
        """
        emote, alias = emote_and_alias
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        await emote_set.add_emote(emote_id=emote.id, emote_alias=alias)
        await ctx.send("Added")

    @is_broadcaster_dev_or_editor()
    @stv.command(name="add", extras={"usage": "!7tv add XDD XDD"})
    async def stv_add(
        self,
        ctx: IreContext,
        *,
        emote_and_alias: Annotated[PartialEmoteAndAlias, AddEmoteConverter],
    ) -> None:
        """Add 7TV emote.

        PS. This command also has a short version ``!add`` (so no need to type ``!7tv``).

        Parameters
        ----------
        emote_and_alias
            In the following format: ``<emote_name_link_or_id> <optional_emote_alias>``,
            separated by space, 1 or 2 "words":

            The 1st one (``<emote_name_link_or_id>``) is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence in after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.

            The 2nd one (``<optional_emote_alias>``) is optional and
            it can be an emote alias with which the emote will be added.

        Examples
        --------
        All these examples below add same "smh" emote

        * ``!7tv add 01FP8TR8G8000EJT2EVEY3JQTF``
        * ``!7tv add https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF SMH`` - adds it under "SMH" emote alias.
        * ``!7tv add smh`` - but it might add some other "smh" emote, if it's more popular.
        """
        await self.add_helper(ctx, emote_and_alias)

    @copy_doc(stv_add)
    @is_broadcaster_dev_or_editor()
    @commands.command(name="add")
    async def add(
        self,
        ctx: IreContext,
        *,
        emote_alias: Annotated[PartialEmoteAndAlias, AddEmoteConverter],
    ) -> None:
        """Add 7TV emote."""
        await self.add_helper(ctx, emote_alias)

    #########################################################################################################################
    # 7TV VIEWER (OR POSSIBLE VIEWER) COMMANDS                                                                              #
    #########################################################################################################################

    async def validate_emote_ownership(self, ctx: IreContext, user_id: str, emote_id: str) -> OwnershipEnum:
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

    async def rename_emote_worker(self, ctx: IreContext, emote_and_alias: PartialEmoteAndAlias) -> None:
        """Rename 7TV emote helper."""
        emote, alias = emote_and_alias
        if alias is None:
            msg = f"You need to provide a new emote alias when using 7tv rename command {self.EMOTE}"
            raise errors.RespondWithError(msg)

        ownership_type = await self.validate_emote_ownership(ctx, ctx.chatter.id, emote.id)
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        if ownership_type == OwnershipEnum.broadcaster_dev_or_editor:
            await emote_set.rename_emote(emote_id=emote.id, new_emote_alias=alias)
        else:
            # Need some validations since it's not an "elevated request"
            await self.validate_is_emote_alias_a_common_word(ctx.broadcaster.id, emote.id, alias)
            await emote_set.rename_emote(emote_id=emote.id, new_emote_alias=alias)
        await ctx.send(f"Renamed {self.EMOTE}")

    @is_broadcaster_dev_editor_or_adder()
    @stv.command(name="rename")
    async def stv_rename(
        self,
        ctx: IreContext,
        *,
        emote_and_alias: Annotated[PartialEmoteAndAlias, RenameEmoteConverter],
    ) -> None:
        """Rename 7TV emote.

        PS. This command also has a short version ``!rename`` (so no need to type ``!7tv``).

        Parameters
        ----------
        emote_and_alias
            In the following format: ``<emote_name_link_or_id> <new_emote_alias>``,
            separated by space, 1 or 2 "words":

            The 1st one (``<emote_name_link_or_id>``) is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence in after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.

            The 2nd one (``<new_emote_alias>``) is a new emote alias with which the emote will be renamed.

        Examples
        --------
        All these examples below rename "smh" emote into "SMH"

        * ``!7tv rename 01FP8TR8G8000EJT2EVEY3JQTF SMH``
        * ``!7tv rename https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF SMH``
        * ``!7tv rename smh SMH``
        """
        await self.rename_emote_worker(ctx, emote_and_alias)

    @copy_doc(stv_rename)
    @is_broadcaster_dev_editor_or_adder()
    @commands.command(name="rename")
    async def rename(
        self,
        ctx: IreContext,
        *,
        emote_and_alias: Annotated[PartialEmoteAndAlias, RenameEmoteConverter],
    ) -> None:
        """Rename 7TV emote."""
        await self.rename_emote_worker(ctx, emote_and_alias)

    async def remove_emote_worker(self, ctx: IreContext, emote: PartialEmote) -> None:
        """Remove 7TV emote helper."""
        await self.validate_emote_ownership(ctx, ctx.chatter.id, emote.id)
        partial_emote_set = await self.select_emote_set(ctx.broadcaster.id)
        await partial_emote_set.remove_emote(emote_id=emote.id)
        await ctx.send(f"Removed {self.EMOTE}")

    @is_broadcaster_dev_editor_or_adder()
    @stv.command(name="remove")
    async def stv_remove(
        self,
        ctx: IreContext,
        *,
        emote: Annotated[PartialEmote, RemoveEmoteConverter],
    ) -> None:
        """Remove 7TV emote.

        PS. This command also has a short version ``!remove`` (so no need to type ``!7tv``).

        Parameters
        ----------
        emote
            In the following format: ``<emote_name_link_or_id>`` which is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence in after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.
        """
        await self.remove_emote_worker(ctx, emote)

    @copy_doc(stv_remove)
    @is_broadcaster_dev_editor_or_adder()
    @commands.command(name="remove")
    async def remove(
        self,
        ctx: IreContext,
        *,
        emote: Annotated[PartialEmote, RemoveEmoteConverter],
    ) -> None:
        """Remove 7TV emote."""
        await self.remove_emote_worker(ctx, emote)

    async def replace_emote_worker(self, ctx: IreContext, emote_and_alias: PartialEmoteAndAlias) -> None:
        """Replace 7TV emote helper."""
        emote, alias = emote_and_alias

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
        if clock.utcnow() - row["added_at"] > datetime.timedelta(minutes=10):
            msg = f"It's been more than 10 minutes, I don't allow replacing after so long {self.EMOTE}"
            raise errors.RespondWithError(msg)

        await self.run_add_emote_validators(emote_id=emote.id, broadcaster_id=ctx.broadcaster.id, emote_alias=alias)
        emote_set = await self.select_emote_set(ctx.broadcaster.id)
        with contextlib.suppress(stv_errors.EmoteNotFoundError):
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
        ctx: IreContext,
        *,
        emote_and_alias: Annotated[PartialEmoteAndAlias, AddEmoteConverter],
    ) -> None:
        """Replace 7TV emote.

        If a user who added the emote decides that they want to add a different emote -
        they can replace it with this command.
        For example, if in their redemption they typed "smh", but the bot added some uninteresting version of "smh" -
        they can use ``!replace <some-cool-emote-id>`` without spending any points.
        To prevent abuse, this command only allows replacing your most recent emote request if it was done within 10 minutes
        of it.

        PS. This command also has a short version ``!replace`` (so no need to type ``!7tv``).

        Parameters
        ----------
        emote_and_alias
            In the following format: ``<emote_name_link_or_id> <optional_emote_alias>``,
            separated by space, 1 or 2 "words":

            The 1st one (``<emote_name_link_or_id>``) is supposed to be an emote identifier:

            * emote link (any link containing its ID, e.g. emote link or its CDN-link),
            * emote ID (characters sequence in after the last "/" in the emote link)
            * or emote name that the bot will use to search the desired emote globally across 7TV.

            The 2nd one (``<optional_emote_alias>``) is optional and
            it can be an emote alias with which the emote will be added.

        Examples
        --------
        All these examples below replace the most recent requested emote with a new one. Note that the user does not need to
        type an identifier for the emote that they want to replace - the bot fetches their most recent emote addition
        redemption.

        * ``!7tv replace 01F6R50PYR0004V0XPDH2CKXCH``
        * ``!7tv replace https://7tv.app/emotes/01F6R50PYR0004V0XPDH2CKXCH``
        * ``!7tv replace smh DuckSmh`` - the bot will search 7tv for "smh", note that the bot will still add the most popular
          one, so doing ``!replace smh`` after adding ``smh`` via redemption is pointless.
        """
        await self.replace_emote_worker(ctx, emote_and_alias)

    @copy_doc(stv_replace)
    @is_broadcaster_dev_editor_or_adder()
    @commands.command(name="replace")
    async def replace(
        self,
        ctx: IreContext,
        *,
        emote_and_alias: Annotated[PartialEmoteAndAlias, AddEmoteConverter],
    ) -> None:
        """Replace 7TV emote."""
        await self.replace_emote_worker(ctx, emote_and_alias)

    #########################################################################################################################
    # BLACKLIST                                                                                                             #
    #########################################################################################################################

    @stv.group(name="blacklist", invoke_fallback=True)
    async def stv_blacklist(self, ctx: IreContext) -> None:
        """Group command for `!7tv blacklist`.

        These commands manage 7tv blacklist channel points reward and related emotes.

        Without a subcommand this lists subcommands.
        """
        await ctx.group_default_response()

    @guards.is_broadcaster_or_dev()
    @stv_blacklist.command(name="create")
    async def stv_blacklist_create(self, ctx: IreContext) -> None:
        """Create 'Blacklist/Remove Emote' channel points reward.

        A few notes:

        * Emotes are blocked by emote id. This does mean that bad actors can keep adding emote duplicates.
        * You can read some tips about how bot's channel point rewards related features work here:
          :ref:`channel_points_reward_tips`.
        * The created channel points reward accepts emote links, emote ids and emote names in its user input.
          If emote name was provided then the bot will search for a match within the broadcaster's cycling emotes.
        """
        custom_reward = await ctx.broadcaster.create_custom_reward(
            # This prompt can be 45 characters max
            title="Remove and blacklist 7TV emote",
            cost=10,
            prompt=(
                # This prompt can be 200 characters max
                "This only works for emotes that were added via 'Add 7TV emote' redeem. "
                "Give me a 7TV emote name, link or emote ID. "
                'Example: "https://7tv.app/emotes/01FP8TR8G8000EJT2EVEY3JQTF"'
            ),
        )

        query = """
            INSERT INTO ttv_stv_blacklist_rewards
            (broadcaster_id, reward_id)
            VALUES ($1, $2)
            ON CONFLICT (broadcaster_id)
                DO UPDATE SET reward_id = $2
            returning broadcaster_id;
        """
        broadcaster_id: str | None = await self.bot.pool.fetchval(query, ctx.broadcaster.id, custom_reward.id)
        if broadcaster_id is None:
            msg = f"This channel already has 7TV blacklist channel reward {self.EMOTE}"
            raise errors.RespondWithError(msg)

        await self.fill_cache_blacklist_rewards()
        await ctx.send(
            "Created 'Remove/Blacklist Emote' channel points reward; "
            "PS. if you want to edit it (e.g. text or color) - visit your creator dashboard "
            f"(dashboard.twitch.tv/u/{ctx.broadcaster.name}/viewer-rewards/channel-points/rewards). "
            f"Just don't remove `Require Viewer to Enter Text`, please {self.EMOTE}",
        )

    async def process_blacklist_redemption(
        self,
        redemption: twitchio.ChannelPointsRedemptionAdd | twitchio.CustomRewardRedemption,
    ) -> None:
        """Process 'Blacklist/Remove Emote' Redemption.

        Errors are handled by global error handler and it refunds the points.
        """
        if not await self.validate_reward_id(redemption, self.cache_blacklist_reward_ids):
            return

        log.debug(
            "User @%s (%s) requested blacklist-emote at broadcaster @%s (%s) with input: '%s'",
            redemption.user.display_name,
            redemption.user.id,
            redemption.broadcaster.display_name,
            redemption.broadcaster.id,
            redemption.user_input,
        )

        emote, alias = await parse_add_rename_input(self.bot.stv, redemption.user_input, redemption.broadcaster.id)
        log.debug("Parsed user input: emote_id=%s emote_alias=%s", emote.id, alias)

        emote_set = await self.select_emote_set(redemption.broadcaster.id)
        log.debug("Operating on emote_set #%s", emote_set.id)

        query = "SELECT emote_id FROM ttv_stv_cycle_emotes WHERE emote_id = $1 AND emote_set_id = $2;"
        selected_emote_id: str | None = await self.bot.pool.fetchval(query, emote.id, emote_set.id)
        if selected_emote_id is None:
            msg = f"This is not a known temporary emote {self.EMOTE}"
            raise errors.RespondWithError(msg)

        await emote_set.remove_emote(emote_id=selected_emote_id)
        await self.delete_from_cycle_emotes(selected_emote_id, emote_set.id)
        query = """
            INSERT INTO ttv_stv_blacklist_emotes
            (emote_id, broadcaster_id, requested_by)
            VALUES ($1, $2, $3)
        """
        await self.bot.pool.execute(query, emote.id, redemption.broadcaster.id, redemption.user.id)

        await self.redemption_respond(redemption, f"Done {self.EMOTE}")
        await self.fulfil_redemption(redemption)
        log.info("Done with blacklist redemption for '%s' (%s)", alias, emote.id)

    @commands.Component.listener(name="custom_redemption_add")
    async def channel_points_blacklist_redeem(self, redemption: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Somebody redeemed a 'Blacklist/Remove Emote' channel points reward."""
        await self.process_blacklist_redemption(redemption)

    @ireloop(time=[datetime.time(hour=hour) for hour in range(24)])
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
    async def stv_blacklist_duration(self, ctx: IreContext, days: int, hours: int = 0) -> None:
        """Set duration for which the emotes are going to be blacklisted.

        A few notes:

        * The bot removes blacklisted status from emotes every hour at X:00. This means, for example,
          if current blacklist duration is set to 7 days,
          it's been 5 days since a certain emote was blacklisted and now the broadcaster sets new duration to 3 days then
          that emote (and other emotes) will be released at next X:00.
        * I guess, it's pedantic to point out that the emotes are not being blacklisted `precisely` for the input'ed
          duration, since the bot does the blacklist-expiry task every hour at X:00. So an emote "AAA" that was blacklisted
          at 2:01AM will have its status lifted at the same time as an emote "BBB" that got blacklisted at 2:59AM.

        Parameters
        ----------
        days
            Amount of days the emotes will be blacklisted.
        hours
            Additionally, amount of hours the emotes will be blacklisted.

        Examples
        --------
        * ``7tv blacklist duration 10 13`` - 10 days, 13 hours.
        * ``7tv blacklist duration 14`` - 2 weeks (14 days).
        """
        new_duration = days * 24 + hours
        if new_duration < 0:
            msg = "Negative blacklist duration is not allowed"
            raise errors.RespondWithError(msg)

        query = "UPDATE ttv_stv_blacklist_rewards SET duration = $1 WHERE broadcaster_id = $2;"
        await self.bot.pool.execute(query, new_duration, ctx.broadcaster.id)
        await ctx.send(
            f"Changed duration to {clock.dm_human_timedelta(datetime.timedelta(days=days, hours=hours))} {self.EMOTE}"
        )

    #########################################################################################################################
    # SOME MODERATION RELATED
    #########################################################################################################################

    async def get_who_added(self, ctx: IreContext, emote: PartialEmote) -> None:
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
    async def stv_who_added(self, ctx: IreContext, *, emote: Annotated[PartialEmote, RemoveEmoteConverter]) -> None:
        """Get twitch user who added the emote via channel redemption.

        PS. This command also has a short version ``!who-added`` (so no need to type ``!7tv``).

        Parameters
        ----------
        emote
            Format: ``<emote_name_link_or_id>`` which is supposed to be an emote identifier for the bot to find the emote:
            emote link (any link containing its ID, e.g. emote link or its CDN-link),
            emote ID (characters sequence in after the last "/" in the emote link) or name that the bot will use to
            search for desired emote in the broadcaster's emote set.
        """
        await self.get_who_added(ctx, emote)

    @copy_doc(stv_who_added)
    @commands.command(name="who-added", aliases=["whoadded"])
    async def who_added(self, ctx: IreContext, *, emote: Annotated[PartialEmote, RemoveEmoteConverter]) -> None:
        """Get twitch user who added the emote via channel redemption."""
        await self.get_who_added(ctx, emote)

    #########################################################################################################################
    # 7TV EDITORS
    #########################################################################################################################

    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    @stv.command(name="editors", aliases=["mods"])
    async def stv_editors(self, ctx: IreContext) -> None:
        """Get 7tv editors for this broadcaster.

        Important lazy quirk! I'm having troubles setting up receiving automatic updates from 7tv for emote / editor updates.
        Currently the bot does NOT automatically fetch 7tv editors information for the streamers.
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
    # 7TV EMOTE STATS                                                                                                       #
    #########################################################################################################################

    # @guards.is_broadcaster_or_dev()
    # @stv.group(name="stats")
    # async def stv_stats(self, ctx: IreContext) -> None:
    #     """Group command for !7tv stats."""
    #     await ctx.group_default_response()

    # # @guards.is_broadcaster_or_dev()
    # # @stv_stats.group(name="allow")
    # # async def stv_stats_allow(self, ctx: IreContext) -> None:
    # #     """Group command for !7tv stats."""
    # #     await ctx.send("")

    # @ireloop(seconds=60.0)
    # async def bulk_insert(self) -> None:
    #     """Bulk insert gathered emoji stats in the last minute."""
    #     async with self._batch_lock:
    #         if not self._batch_last_year:
    #             # there was no data to commit to the database.
    #             return

    #         # TOTAL COUNT
    #         transformed = [
    #             {"guild": guild_id, "emote": emote_id, "added": count}
    #             for guild_id, data in self._batch_total.items()
    #             for emote_id, count in data.items()
    #         ]
    #         query_total = """
    #             INSERT INTO ttv_emote_stats_total (broadcaster_id, emote_id, total)
    #                 SELECT x.broadcaster, x.emote, x.added
    #                 FROM jsonb_to_recordset($1::jsonb) AS
    #                 x(
    #                     broadcaster TEXT,
    #                     emote TEXT,
    #                     added INT
    #                 )
    #             ON CONFLICT (broadcaster_id, emote_id) DO UPDATE
    #             SET total = ttv_emote_stats_total.total + excluded.total;
    #         """

    #         # LAST YEAR COUNT
    #         query_last_year = """
    #             INSERT INTO ttv_emote_stats_last_year (emote_id, broadcaster_id, author_id, used)
    #                 SELECT x.emote_id, x.broadcaster_id, x.author_id, x.used
    #                 FROM jsonb_to_recordset($1::jsonb) AS
    #                 x(
    #                     emote_id TEXT,
    #                     broadcaster_id TEXT,
    #                     author_id TEXT,
    #                     used TIMESTAMP
    #                 )
    #             """
    #         async with self.bot.pool.acquire() as connection:
    #             tr = connection.transaction()
    #             await tr.start()

    #             try:
    #                 await connection.execute(query_total, transformed)
    #                 await connection.execute(query_last_year, self._batch_last_year)
    #             except Exception:
    #                 await tr.rollback()
    #                 raise
    #             else:
    #                 await tr.commit()

    #         self._batch_total.clear()
    #         self._batch_last_year.clear()

    # @ireloop(time=datetime.time(hour=12, minute=11, second=45))
    # async def clean_up_old_records(self) -> None:
    #     """Clean up "way too old" records from the Last Year emote usage database.

    #     I'm kinda afraid of running out of memory so I'm just keeping a one year records max.
    #     If I'm proven wrong and we can hold much more data than this - I will consider extending the database.
    #     But for now - we clean up the database from 1 year+ records.

    #     Note that this doesn't affect `emote_stats_total` in any way. Everything is correct there.
    #     """
    #     async with self._batch_lock:
    #         clean_up_dt = clock.utcnow() - datetime.timedelta(days=365)

    #         query = """
    #                 DELETE FROM emote_stats_last_year
    #                 WHERE used < $1::date
    #             """
    #         await self.bot.pool.execute(query, clean_up_dt)

    # @commands.Component.listener(name="message")
    # async def collect_emote_usage_stats(self, message: twitchio.ChatMessage) -> None:
    #     """Collect emote usage data in batches from twitch chat messages to be ready for database INSERT.

    #     Parameters
    #     ----------
    #     message: twitchio.ChatMessage
    #         message to filter emotes from.
    #     """
    #     if not message.text:
    #         return

    #     if message.chatter.display_name is not None and message.chatter.display_name.lower() in const.BotsLowerName:
    #         # Not counting known bots
    #         return

    #     if next((x for x in message.chatter.badges if x.set_id == "bot-badge"), None):
    #         # Not counting bots
    #         return


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(SevenTVFeatures(bot))
