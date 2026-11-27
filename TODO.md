# 📝 TODO

- [ ] Make the healthcheck heartbeat (`heartbeat_task` in `src/ext/dev/reload.py`) also request the bot's own public ngrok URL (`Bot.domain`), and skip the ping when it doesn't answer. Right now a dropped ngrok tunnel breaks the bot's web pages (Twitch OAuth, the 7TV token page) while the healthcheck stays green, and nothing else watches ngrok.
  - Request a cheap route that the adapter always serves, and accept any HTTP answer: only a connection error or ngrok's own error page (e.g. `ERR_NGROK_3200`, tunnel offline) means the tunnel is down.
  - Only when the bot runs with the remote adapter; with the local one there's no tunnel to check.
