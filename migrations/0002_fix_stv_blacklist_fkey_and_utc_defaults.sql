/* ---------------------------------------------------------------------------------------------------------------------
Two slips from the baseline:

* `stv_blacklist_emotes.broadcaster_id` referenced `stv_cycle_rewards` instead of `stv_blacklist_rewards`,
  so a broadcaster with only a blacklist reward couldn't have blacklisted emotes. Now removing the blacklist reward
  removes its emotes, like removing the cycle reward removes the cycle emotes.
* `NOW() AT TIME ZONE 'utc'` as the default of `TIMESTAMPTZ` columns is only correct when the server's timezone is UTC
  (it turns the moment into a UTC wall time, which is then read back in the server's timezone). `NOW()` is correct anywhere.
--------------------------------------------------------------------------------------------------------------------- */

ALTER TABLE irenesbot.stv_blacklist_emotes
    DROP CONSTRAINT stv_blacklist_emotes_broadcaster_id_fkey,
    ADD CONSTRAINT stv_blacklist_emotes_broadcaster_id_fkey
        FOREIGN KEY (broadcaster_id) REFERENCES irenesbot.stv_blacklist_rewards (broadcaster_id) ON DELETE CASCADE;

ALTER TABLE irenesbot.stv_blacklist_emotes ALTER COLUMN blacklisted_at SET DEFAULT NOW();

ALTER TABLE irenesbot.stv_cycle_emotes ALTER COLUMN added_at SET DEFAULT NOW();

ALTER TABLE irenesbot.stv_bot_token ALTER COLUMN updated_at SET DEFAULT NOW();
