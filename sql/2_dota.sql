CREATE TABLE
    IF NOT EXISTS ttv_dota_accounts (
        friend_id BIGINT PRIMARY KEY, -- steam32id (friend id) format;
        twitch_id TEXT NOT NULL,
        estimated_mmr INT DEFAULT (0),
        last_seen TIMESTAMPTZ DEFAULT (NOW () AT TIME zone 'utc'),
        CONSTRAINT fk_twitch_id FOREIGN KEY (twitch_id) REFERENCES ttv_streamers (user_id) ON DELETE CASCADE
    );

CREATE TABLE
    IF NOT EXISTS ttv_dota_matches (
        match_id BIGINT PRIMARY KEY,
        start_time TIMESTAMPTZ DEFAULT (NOW () AT TIME zone 'utc'),
        lobby_type INT NOT NULL,
        game_mode INT NOT NULL,
        outcome INT DEFAULT (NULL),
        live INT DEFAULT (1),
        failed INT DEFAULT (0)
    );

CREATE TABLE
    IF NOT EXISTS ttv_dota_match_players (
        friend_id BIGINT NOT NULL,
        match_id BIGINT NOT NULL,
        PRIMARY KEY (friend_id, match_id),
        hero_id INT NOT NULL,
        player_slot INT NOT NULL,
        abandon BOOLEAN DEFAULT (NULL),
        CONSTRAINT fk_account FOREIGN KEY (friend_id) REFERENCES ttv_dota_accounts (friend_id) ON DELETE CASCADE,
        CONSTRAINT fk_match FOREIGN KEY (match_id) REFERENCES ttv_dota_matches (match_id) ON DELETE CASCADE
    );

CREATE TABLE
    IF NOT EXISTS ttv_dota_notable_players (
        friend_id BIGINT PRIMARY KEY,
        nickname TEXT -- either twitch name, pro player tag or nickname;
    );