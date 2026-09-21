"""Modules to load when `bot.subset_mode` is `True`."""

MODULES_SUBSET: dict[str, list[str]] = {
    "dev": [
        "required",
        # ---
        "control",
        # "other",
        # "webhook_logs",
    ],
    "personal": [
        # "alerts",
        # "counters",
        # "discord_notifications",
        # "emotes_common"
        # "information",
        # "keywords",
        # "stable",
        # "tags",
        # "temporary",
        # "timers",
    ],
    "public": [
        # "d9kmmrbot",
        "emotes_7tv",
        # "first",
        # "meta"
    ],
}
