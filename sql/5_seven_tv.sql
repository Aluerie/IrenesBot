CREATE TABLE
    /* 7TV streamers */
    IF NOT EXISTS ttv_stv_users (
        broadcaster_id TEXT PRIMARY KEY REFERENCES ttv_tokens (user_id) ON DELETE CASCADE,
        stv_user_id TEXT NOT NULL,
        emote_set_id TEXT NOT NULL,
        allow_common_words BOOLEAN
    );

CREATE TABLE
    /* Cycling Emote Rewards */
    IF NOT EXISTS ttv_stv_cycle_rewards (
        broadcaster_id TEXT PRIMARY KEY REFERENCES ttv_stv_users (broadcaster_id) ON DELETE CASCADE,
        reward_id TEXT NOT NULL,
        emote_limit INT NOT NULL DEFAULT (10)
    );

CREATE TABLE
    /* Cycling Emotes */
    IF NOT EXISTS ttv_stv_cycle_emotes (
        id SERIAL PRIMARY KEY,
        emote_id TEXT NOT NULL,
        broadcaster_id TEXT NOT NULL REFERENCES ttv_stv_cycle_rewards (broadcaster_id) ON DELETE CASCADE,
        emote_set_id TEXT NOT NULL,
        added_at TIMESTAMPTZ DEFAULT (now () AT TIME ZONE 'utc'),
        requested_by TEXT NOT NULL -- twitch_id string;
    );

CREATE TABLE
    /* Blacklist Emote Rewards */
    IF NOT EXISTS ttv_stv_blacklist_rewards (
        broadcaster_id TEXT PRIMARY KEY REFERENCES ttv_stv_users (broadcaster_id) ON DELETE CASCADE,
        reward_id TEXT NOT NULL,
        duration INTEGER NOT NULL DEFAULT (167), -- in hours
        remove_only BOOLEAN DEFAULT (FALSE)
    );

CREATE TABLE
    /* Blacklist Emotes */
    IF NOT EXISTS ttv_stv_blacklist_emotes (
        id SERIAL PRIMARY KEY,
        emote_id TEXT NOT NULL,
        broadcaster_id TEXT NOT NULL REFERENCES ttv_stv_cycle_rewards (broadcaster_id) ON DELETE CASCADE,
        blacklisted_at TIMESTAMPTZ DEFAULT (NOW () AT TIME zone 'utc'),
        requested_by TEXT NOT NULL -- twitch_id string;
    );

CREATE TABLE
    /* 7TV mods */
    IF NOT EXISTS ttv_stv_mods (
        broadcaster_id TEXT NOT NULL,
        editor_id TEXT NOT NULL,
        PRIMARY KEY (broadcaster_id, editor_id)
    );

CREATE TABLE
    /* Permanent Emote Rewards */
    IF NOT EXISTS ttv_stv_permanent_rewards (
        broadcaster_id TEXT PRIMARY KEY REFERENCES ttv_stv_users (broadcaster_id) ON DELETE CASCADE,
        reward_id TEXT NOT NULL
    );