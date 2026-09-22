"""
Subscriptions and Oath.

Contains functions to subscribe to proper EventSub subscriptions as well as helper functions for twitch permissions.

A lot of confusion and pain about Twitch Dev is related to Event Sub subscriptions.
So here are some notes.

Notes
-----
* If there are some issues (e.g. no event appearing) after
    1. Adding or removing subscriptions from `get_user_subscriptions` function
    2. Some user authorizing through an oauth url

    Then it's likely we need to run the bot with `--force-subscribe` flag to reset the conduits.

Links
----------
TwitchDev Docs
    * Eventsub:        https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types
    * Scopes:          https://dev.twitch.tv/docs/authentication/scopes/
TwitchIO  Docs
    * Event Reference: https://twitchio.dev/en/latest/references/events/events.html
    * Models:          https://twitchio.dev/en/latest/references/eventsub/index.html

License
-------
* This Source Code Form is subject to the terms of the [Mozilla Public License v2.0](<http://mozilla.org/MPL/2.0/>).
* Copyright (C) 2020-present [@Aluerie](<https://github.com/Aluerie>).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypedDict

import twitchio
from twitchio import eventsub

from utils import const

if TYPE_CHECKING:
    from shared.types_.database import PoolTypedWithAny

    class GetMemberAccountsQueryRow(TypedDict):
        user_id: str


__all__ = (
    "get_all_oauth_urls",
    "get_eventsub_subscriptions",
    "get_user_subscriptions",
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def get_user_subscriptions(
    user: twitchio.PartialUser | str,
    bot: twitchio.PartialUser | str,
) -> list[eventsub.SubscriptionPayload]:
    """Get user-specific EventSub subscriptions that are required for the bot's EventSub related features to work.

    This function separates Irene's personal EventSubs (with more features) and public EventSubs (a bit less features).
    The function also includes (in code) a table showcasing which subscriptions/scopes are required for what.
    """
    if user == const.UserID.Irene:
        # My personal account to have all the features on.
        return [
            *get_public_subscriptions(user, bot),
            # EventSub Subscriptions Table (order - function name sorted by alphabet).
            # Subscription Name                         Permission
            # ----------------------------------------------------
            # ✅ Ad break begin                         channel:read:ads
            eventsub.AdBreakBeginSubscription(broadcaster_user_id=user),
            # ✅ Bans                                   channel:moderate
            eventsub.ChannelBanSubscription(broadcaster_user_id=user),
            # ✅ Follows                                moderator:read:followers
            eventsub.ChannelFollowSubscription(broadcaster_user_id=user, moderator_user_id=bot),
            # ✅ Raids to the channel                   No authorization required
            eventsub.ChannelRaidSubscription(to_broadcaster_user_id=user),
            # ✅ Channel Update (title/game)            No authorization required
            eventsub.ChannelUpdateSubscription(broadcaster_user_id=user),
            # ❓ Channel Subscribe (paid)               channel:read:subscriptions
            eventsub.ChannelSubscribeSubscription(broadcaster_user_id=user),
            # ❓ Channel Subscribe Message (paid)       channel:read:subscriptions
            eventsub.ChannelSubscribeMessageSubscription(broadcaster_user_id=user),
        ]
    return get_public_subscriptions(user, bot)


def get_public_subscriptions(
    user: twitchio.PartialUser | str,
    bot: twitchio.PartialUser | str,
) -> list[eventsub.SubscriptionPayload]:
    # Then it's a public member
    # Public accounts are people who are only allowed to use public features.
    # Their accounts do not need all EventSub models activated.
    return [
        # EventSub Subscriptions Table (order - function name sorted by alphabet).
        # Subscription Name                                 Permission
        # ------------------------------------------------------------
        # ✅ Channel Points Redeem                         channel:read:redemptions or channel:manage:redemptions
        eventsub.ChannelPointsRedeemAddSubscription(broadcaster_user_id=user),
        # ✅ Channel Points Custom Reward Update           channel:read:redemptions or channel:manage:redemptions
        eventsub.ChannelPointsRewardUpdateSubscription(broadcaster_user_id=user),
        # Channel Points Custom Reward Remove               channel:read:redemptions or channel:manage:redemptions
        eventsub.ChannelPointsRewardRemoveSubscription(broadcaster_user_id=user),
        # ✅ Message                                       user:read:chat from the chatbot, channel:bot from broadcaster
        eventsub.ChatMessageSubscription(broadcaster_user_id=user, user_id=bot),
        # ✅ Stream went offline                           No authorization required
        eventsub.StreamOfflineSubscription(broadcaster_user_id=user),
        # ✅ Stream went live                              No authorization required
        eventsub.StreamOnlineSubscription(broadcaster_user_id=user),
    ]


async def get_eventsub_subscriptions(
    pool: PoolTypedWithAny, *, test_account: bool
) -> list[twitchio.eventsub.SubscriptionPayload]:
    """Get all EventSub subscriptions that are required for the bot's EventSub related features to work."""
    if test_account:
        bot = const.UserID.Test
        tokens_table = "ttv_test_tokens"
    else:
        bot = const.UserID.Bot
        tokens_table = "ttv_tokens"

    subscriptions: list[eventsub.SubscriptionPayload] = []

    # 1. My personal account
    subscriptions.extend(get_user_subscriptions(const.UserID.Irene, bot))

    # 2. Public member accounts
    query = f"""
        SELECT t.user_id
        FROM {tokens_table} t
        JOIN ttv_streamers s ON t.user_id = s.user_id
        WHERE active = TRUE AND t.user_id != ANY($1)
    """
    exclude_ids = {const.UserID.Irene, bot}
    public_rows: list[GetMemberAccountsQueryRow] = await pool.fetch(query, exclude_ids)
    for user in public_rows:
        subscriptions.extend(get_user_subscriptions(user["user_id"], bot))
    return subscriptions


def get_bot_oauth_url(domain: str) -> str:
    """Print a link for me (developer) to click and authorize the bot scopes for the bot account.

    Note, that we need to login with the bot account (do not use this link for personal accounts).
    Required for proper work of Twitch Eventsub events and API requests (such as helix).
    """
    scopes = [
        "user:read:chat",
        "user:write:chat",
        "user:bot",
        "moderator:read:followers",
        "moderator:manage:shoutouts",
        "moderator:manage:announcements",
        "moderator:manage:banned_users",
        "clips:edit",
    ]
    return get_oauth_url(domain, scopes, "🤖🤖🤖 BOT OAUTH LINK: 🤖🤖🤖")


def get_personal_oauth_url(domain: str) -> str:
    """Print a link for me (personal bot user with all the features) to click and authorize the scopes for the bot."""
    scopes = [
        "channel:bot",
        "channel:edit:commercial",  # "channel:read:ads",
        "channel:moderate",
        "channel:read:redemptions",
        "channel:manage:redemptions",
        "channel:manage:broadcast",
        "channel:read:subscriptions",
    ]
    return get_oauth_url(domain, scopes, "🎬🎬🎬 PERSONAL OAUTH LINK: 🎬🎬🎬")


def get_public_oauth_url(domain: str) -> str:
    """Print a link for public streamers to click and authorize the scopes for the bot."""
    scopes = [
        "channel:bot",
        "channel:read:redemptions",
        "channel:manage:redemptions",
    ]
    return get_oauth_url(domain, scopes, "🌈🌈🌈 PUBLIC OAUTH LINK: 🌈🌈🌈")


def get_oauth_url(domain: str, scopes: list[str], prefix: str) -> str:
    """Helper function for `get_bot_oauth_url`, `get_personal_oauth_url`, `get_public_oauth_url`.

    The authorization is required for proper work of Twitch Eventsub events and API requests.
    Currently, we separate bot features into two categories:
    * Personal - that are only used by me;
    * Public - that I allow to be used by everybody;
    They require different sets of scopes. And also, we need a separate oauth for the bot account.
    Therefore, we have 3 distinct links depending on which account should click on it.

    """
    link = f"{domain}/oauth?scopes={'+'.join(scopes)}&force_verify=true"
    return f"{prefix}\n{link}"


def get_all_oauth_urls(domain: str) -> str:
    """Helper function to get all bot oauth urls at once."""
    return "\n".join(
        [
            get_bot_oauth_url(domain),
            get_personal_oauth_url(domain),
            get_public_oauth_url(domain),
        ]
    )
