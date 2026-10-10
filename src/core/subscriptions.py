"""Subscriptions and Oath.

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
    * Eventsub:  https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types
    * Scopes: https://dev.twitch.tv/docs/authentication/scopes/
TwitchIO  Docs
    * Event Reference: https://twitchio.dev/en/latest/references/events/events.html
    * Models: https://twitchio.dev/en/latest/references/eventsub/index.html

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, TypedDict

import twitchio
from twitchio import eventsub

from utils import const

if TYPE_CHECKING:
    from shared.concepts.db import PoolTypedWithAny

    class GetMemberAccountsQueryRow(TypedDict):
        user_id: str


__all__ = (
    "get_eventsub_subscriptions",
    "get_oauth_urls",
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
    bot = const.UserID.Test if test_account else const.UserID.Bot
    subscriptions: list[eventsub.SubscriptionPayload] = []

    # 1. My personal account
    subscriptions.extend(get_user_subscriptions(const.UserID.Irene, bot))

    # 2. Public member accounts
    query = "SELECT user_id FROM ttv_tokens WHERE user_type = 'public';"
    public_rows: list[GetMemberAccountsQueryRow] = await pool.fetch(query)
    for user in public_rows:
        subscriptions.extend(get_user_subscriptions(user["user_id"], bot))
    return subscriptions


def get_oauth_urls(domain: str) -> str:
    """Get all oauth urls.

    In order to add the bot to their channels - users need to authorize the bot via twitch oauth link with proper scopes.
    This is required for Twitch Eventsub events and API requests (such as helix) to work an overall a standard permissions
    kinda system.

    Currently, I divide the bot's feature set into 2 categories:
    * Public - for general public, features ready and useful for general public.
    * Personal - that are only used by me, and they need some extra scopes.
    So public features need a set of scopes for broadcasters to allow. Personal features extend that so Irene needs to
    allow extra scopes so that's a 2nd set of scopes.

    The way twitch bot development works is that the developers also need to authorize the bot's account with
    bot-user-related scopes. That's a 3rd set of scopes.

    This functions prints authorization links for all these 3 sets of scopes:
    * public - for public broadcasters to use;
    * personal - for irene only;
    * bot - for irene to authorize the bot account with;

    Parameters
    ----------
    domain
        Callback domain to use for the oauth. Either localhost or a public domain where a web-app is running.
    """
    # BOT SCOPES - developers should authorize the bot's account with these.
    bot_scopes = twitchio.Scopes(
        user_read_chat=True,
        user_write_chat=True,
        user_bot=True,
        moderator_read_followers=True,
        moderator_manage_shoutouts=True,
        moderator_manage_announcements=True,
        moderator_manage_banned_users=True,
        clips_edit=True,
    )
    # PUBLIC SCOPES - general public should authorize with these.
    public_scopes = twitchio.Scopes(
        channel_bot=True,
        channel_read_redemptions=True,
        channel_manage_redemptions=True,
        channel_manage_moderators=True,
    )
    # PERSONAL SCOPES - Irene should authorize with these because of extra personal features.
    personal_scopes = copy.deepcopy(public_scopes)
    personal_scopes.channel_edit_commercial = True
    personal_scopes.channel_edit_commercial = True
    personal_scopes.channel_moderate = True
    personal_scopes.channel_manage_broadcast = True
    personal_scopes.channel_read_subscriptions = True

    return "\n".join(
        f"{title}\n{domain}/oauth?scopes={scopes.urlsafe(unquote=True)}&force_verify=true"
        for scopes, title in (
            (bot_scopes, "🤖🤖🤖 BOT OAUTH LINK: 🤖🤖🤖"),
            (public_scopes, "🌈🌈🌈 PUBLIC OAUTH LINK: 🌈🌈🌈"),
            (personal_scopes, "🎬🎬🎬 PERSONAL OAUTH LINK: 🎬🎬🎬"),
        )
    )
