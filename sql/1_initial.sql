/* --- Bot Variables and internals ---------------------------------------------------------------------------------- */
CREATE TABLE
    IF NOT EXISTS bot_variables (
        key TEXT PRIMARY KEY,
        VALUE JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW ()
    );

-- TODO: Move Erms here^^^