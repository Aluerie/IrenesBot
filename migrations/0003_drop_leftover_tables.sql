/* ---------------------------------------------------------------------------------------------------------------------
Drop the tables that are left over from older code (the daily backups up to 2026-11-27 still have them):

* `first_redeems`: the old version of `first_chatter_redeems`.
* `tokens_test`: no code reads it; the test bot keeps its tokens in `tokens` of the home database.

`IF EXISTS`, since a database built from the baseline never had them.
--------------------------------------------------------------------------------------------------------------------- */

DROP TABLE IF EXISTS irenesbot.first_redeems;

DROP TABLE IF EXISTS irenesbot.tokens_test;
