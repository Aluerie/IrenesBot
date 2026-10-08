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
        added_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc'::text),
        requested_by TEXT NOT NULL -- twitch_id string;
    );

CREATE TABLE
    /* EMOTE STATS TOTAL
     */
    IF NOT EXISTS ttv_stv_emote_stats_total (
        id BIGSERIAL PRIMARY KEY,
        broadcaster_id TEXT,
        emote_id TEXT,
        total INTEGER DEFAULT (0)
    );

CREATE INDEX IF NOT EXISTS ttv_stv_emote_stats_total_broadcaster_id_idx ON ttv_stv_emote_stats_total (broadcaster_id);

CREATE INDEX IF NOT EXISTS ttv_stv_emote_stats_total_emote_id_idx ON ttv_stv_emote_stats_total (emote_id);

CREATE UNIQUE INDEX IF NOT EXISTS ttv_stv_emote_stats_total_uniq_idx ON ttv_stv_emote_stats_total (broadcaster_id, emote_id);

CREATE TABLE
    /* EMOTE STATS LAST YEAR
     */
    IF NOT EXISTS ttv_stv_emote_stats_last_year (
        id BIGSERIAL PRIMARY KEY,
        emote_id TEXT,
        broadcaster_id TEXT,
        author_id TEXT,
        used TIMESTAMP
    );

CREATE INDEX IF NOT EXISTS ttv_stv_emote_stats_last_year_emote_id_idx ON ttv_stv_emote_stats_last_year (emote_id);

CREATE INDEX IF NOT EXISTS ttv_stv_emote_stats_last_year_broadcaster_id_idx ON ttv_stv_emote_stats_last_year (broadcaster_id);

CREATE INDEX IF NOT EXISTS ttv_stv_emote_stats_last_year_author_id_idx ON ttv_stv_emote_stats_last_year (author_id);

CREATE INDEX IF NOT EXISTS ttv_stv_emote_stats_last_year_used_idx ON ttv_stv_emote_stats_last_year (used);

CREATE TABLE
    /* Blacklist Emote Rewards */
    IF NOT EXISTS ttv_stv_blacklist_rewards (
        broadcaster_id TEXT PRIMARY KEY REFERENCES ttv_stv_users (broadcaster_id) ON DELETE CASCADE,
        reward_id TEXT NOT NULL,
        duration INTEGER NOT NULL DEFAULT (169)
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