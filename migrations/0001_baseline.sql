/* ---------------------------------------------------------------------------------------------------------------------
Baseline: the `irenesbot` schema as it was on prod on 2026-11-26.

`scheduled_jobs` isn't here: `shared.scheduler` creates it on start.
Dota2Bot's `dota2bot.dota_accounts` references `irenesbot.tokens`, so on an empty database this file runs before Dota2Bot's baseline.
--------------------------------------------------------------------------------------------------------------------- */

CREATE SCHEMA irenesbot;

-- `similarity()` for fuzzy nickname search in `mmrbot`
CREATE EXTENSION IF NOT EXISTS pg_trgm;

/* --- Bot internals ------------------------------------------------------------------------------------------------ */

CREATE TABLE irenesbot.bot_variables (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE irenesbot.tokens (
    /* Twitch OAuth tokens of the bot and the broadcasters who authorized it */
    user_id TEXT PRIMARY KEY,
    token TEXT NOT NULL,
    refresh TEXT NOT NULL,
    display_name TEXT,
    user_type TEXT NOT NULL DEFAULT 'public'
);

CREATE TABLE irenesbot.stv_bot_token (
    /* The bot's 7TV Bearer token (single row), replaceable at runtime via the `/stv-token` web page */
    id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
    token TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

/* --- Personal channel features ------------------------------------------------------------------------------------ */

CREATE TABLE irenesbot.tags (
    tag_name TEXT PRIMARY KEY,
    tag_content TEXT NOT NULL
);

CREATE TABLE irenesbot.counters (
    name TEXT PRIMARY KEY,
    value BIGINT DEFAULT 0
);

CREATE TABLE irenesbot.chatters (
    user_id TEXT PRIMARY KEY,
    name_lower TEXT NOT NULL
);

/* --- First chatter redeems ---------------------------------------------------------------------------------------- */

CREATE TABLE irenesbot.first_chatter_rewards (
    /* Each streamer's "First" channel reward, if they have one set up */
    streamer_id TEXT PRIMARY KEY,
    reward_id TEXT NOT NULL,
    original_title TEXT
);

CREATE TABLE irenesbot.first_chatter_redeems (
    /* How many times a person redeemed a streamer's "First" channel reward */
    user_id TEXT,
    streamer_id TEXT,
    first_times INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, streamer_id)
);

/* --- 7TV ---------------------------------------------------------------------------------------------------------- */

CREATE TABLE irenesbot.stv_users (
    broadcaster_id TEXT PRIMARY KEY REFERENCES irenesbot.tokens (user_id) ON DELETE CASCADE,
    stv_user_id TEXT NOT NULL,
    emote_set_id TEXT NOT NULL,
    allow_common_words BOOLEAN DEFAULT TRUE
);

CREATE TABLE irenesbot.stv_mods (
    broadcaster_id TEXT,
    editor_id TEXT,
    PRIMARY KEY (broadcaster_id, editor_id)
);

CREATE TABLE irenesbot.stv_cycle_rewards (
    broadcaster_id TEXT PRIMARY KEY REFERENCES irenesbot.stv_users (broadcaster_id) ON DELETE CASCADE,
    reward_id TEXT NOT NULL,
    emote_limit INTEGER NOT NULL DEFAULT 10
);

CREATE TABLE irenesbot.stv_cycle_emotes (
    id SERIAL PRIMARY KEY,
    emote_id TEXT NOT NULL,
    broadcaster_id TEXT NOT NULL REFERENCES irenesbot.stv_cycle_rewards (broadcaster_id) ON DELETE CASCADE,
    emote_set_id TEXT NOT NULL,
    added_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'utc'),
    requested_by TEXT NOT NULL -- Twitch user ID
);

CREATE TABLE irenesbot.stv_blacklist_rewards (
    broadcaster_id TEXT PRIMARY KEY REFERENCES irenesbot.stv_users (broadcaster_id) ON DELETE CASCADE,
    reward_id TEXT NOT NULL,
    duration INTEGER DEFAULT 168, -- hours
    remove_only BOOLEAN DEFAULT FALSE
);

CREATE TABLE irenesbot.stv_blacklist_emotes (
    id SERIAL PRIMARY KEY,
    emote_id TEXT NOT NULL,
    broadcaster_id TEXT NOT NULL REFERENCES irenesbot.stv_cycle_rewards (broadcaster_id) ON DELETE CASCADE,
    blacklisted_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'utc'),
    requested_by TEXT NOT NULL -- Twitch user ID
);

CREATE TABLE irenesbot.stv_permanent_rewards (
    broadcaster_id TEXT PRIMARY KEY REFERENCES irenesbot.stv_users (broadcaster_id) ON DELETE CASCADE,
    reward_id TEXT NOT NULL
);
