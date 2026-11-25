# 📝 TODO

- [ ] Apply `sql/` schema changes to the VPS database automatically on deploy, e.g. a step in `deploy_service.yml` that runs the `CREATE TABLE IF NOT EXISTS` files before restarting the bot. Right now new tables have to be created by hand, and a missing `irenesbot.bot_variables` table once put the bot into a crash loop while the deploy still reported success.
  - Check which `sql/` files are safe to re-run first; `1_main_old.sql` and `3_unsorted.sql` might not be.
  - Once it works, add a `make migrate` command to run it by hand too.
- [ ] Decide how to run the local development database. `compose.yml` defines a Docker Postgres on port 5431 (5432 is taken by the local PgAdmin Postgres), but it's unclear whether to keep using Docker for it or a natively installed Postgres.
  - If Docker stays, add `make db` / `make db-down` commands for `docker compose up -d db` / `docker compose down`.
  - If not, remove the `db` service from `compose.yml`.
  - Either way, make `POSTGRES_HOME` in `.env.example` point at the chosen one.
