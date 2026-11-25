# 📝 TODO

- [ ] Apply `sql/` schema changes to the VPS database automatically on deploy, e.g. a step in `deploy_service.yml` that runs the `CREATE TABLE IF NOT EXISTS` files before restarting the bot. Right now new tables have to be created by hand, and a missing `irenesbot.bot_variables` table once put the bot into a crash loop while the deploy still reported success.
