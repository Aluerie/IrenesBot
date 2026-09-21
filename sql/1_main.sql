/* 
SQL Tables Schema for IreBot

Notes
-----
1. Table names used for IreBot should start with `ttv_` to differentiate them from other tables in the database that are used
by AluBot.
-*/
CREATE TABLE
    /* Twitch Oauth Tokens */
    IF NOT EXISTS ttv_tokens (
        user_id TEXT PRIMARY KEY,
        token TEXT NOT NULL,
        refresh TEXT NOT NULL
    );

CREATE TABLE
    IF NOT EXISTS ttv_streamers (
        user_id TEXT PRIMARY KEY,
        display_name TEXT,
        active BOOLEAN DEFAULT (TRUE)
    );

CREATE TABLE
    /* Tags */
    IF NOT EXISTS ttv_tags (
        tag_name TEXT PRIMARY KEY,
        tag_content TEXT NOT NULL
    );

CREATE TABLE
    /* Cycling Emote Rewards */
    IF NOT EXISTS ttv_cycling_emote_rewards (
        streamer_id TEXT PRIMARY KEY,
        reward_id TEXT NOT NULL,
        emote_limit INT NOT NULL
    );

CREATE TABLE
    /* Cycling Emotes */
    IF NOT EXISTS ttv_cycling_emotes (
        id SERIAL PRIMARY KEY,
        emote_id TEXT NOT NULL,
        streamer_id TEXT NOT NULL,
        emote_set_id TEXT NOT NULL,
        added_at TIMESTAMPTZ DEFAULT (NOW () AT TIME zone 'utc'),
        requested_by TEXT NOT NULL -- twitch_id string;
    );

CREATE TABLE
    /* First Chatter Channel Reward Redeems
    
    Contains records of how many times a person redeemed 'First' channel reward
    for streamers in the database. 
     */
    IF NOT EXISTS ttv_first_chatter_redeems (
        user_id TEXT,
        streamer_id TEXT,
        PRIMARY KEY (user_id, streamer_id),
        first_times INT DEFAULT (1)
    );

CREATE TABLE
    /* First Chatter Channel Rewards 
    
    Contains relation between streamers and their 'First' Channel Reward, if they have it set up.
     */
    IF NOT EXISTS ttv_first_chatter_rewards (
        streamer_id TEXT PRIMARY KEY,
        reward_id TEXT NOT NULL,
        original_title TEXT
    );

CREATE TABLE
    /* EMOTE STATS TOTAL
     */
    IF NOT EXISTS ttv_emote_stats_total (
        id BIGSERIAL PRIMARY KEY,
        broadcaster_id TEXT,
        emote_id TEXT,
        total INTEGER DEFAULT (0)
    );

CREATE INDEX IF NOT EXISTS ttv_emote_stats_total_broadcaster_id_idx ON ttv_emote_stats_total (broadcaster_id);

CREATE INDEX IF NOT EXISTS ttv_emote_stats_total_emote_id_idx ON ttv_emote_stats_total (emote_id);

CREATE UNIQUE INDEX IF NOT EXISTS ttv_emote_stats_total_uniq_idx ON ttv_emote_stats_total (broadcaster_id, emote_id);

CREATE TABLE
    /* EMOTE STATS LAST YEAR
     */
    IF NOT EXISTS ttv_emote_stats_last_year (
        id BIGSERIAL PRIMARY KEY,
        emote_id TEXT,
        broadcaster_id TEXT,
        author_id TEXT,
        used TIMESTAMP
    );

CREATE INDEX IF NOT EXISTS ttv_emote_stats_last_year_emote_id_idx ON ttv_emote_stats_last_year (emote_id);

CREATE INDEX IF NOT EXISTS ttv_emote_stats_last_year_broadcaster_id_idx ON ttv_emote_stats_last_year (broadcaster_id);

CREATE INDEX IF NOT EXISTS ttv_emote_stats_last_year_author_id_idx ON ttv_emote_stats_last_year (author_id);

CREATE INDEX IF NOT EXISTS ttv_emote_stats_last_year_used_idx ON ttv_emote_stats_last_year (used);