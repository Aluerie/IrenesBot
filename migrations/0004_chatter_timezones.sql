/* ---------------------------------------------------------------------------------------------------------------------
Chatters' timezones for `!remind`: `!remind tz MSK` saves one, so "3pm" in that chatter's reminders means 3pm on
their clocks (Twitch doesn't tell the bot anybody's timezone). The key is the Twitch user ID.
--------------------------------------------------------------------------------------------------------------------- */

CREATE TABLE IF NOT EXISTS irenesbot.chatter_timezones (
    user_id BIGINT PRIMARY KEY,
    timezone TEXT NOT NULL, -- IANA key, e.g. 'Europe/Moscow'
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
