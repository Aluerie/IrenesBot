"""Modules to load when `--subset-mode` CLI argument is used.

Rename this file to 'modules_subset.py' and choose modules you want to load when
testing version of the bot (`--subset-mode`) is running.

This is useful when we want to debug select features/modules of the bot without launching the whole thing.
Especially because some modules take quite a long time to launch or have some heavy tasks on startup.
So that would be annoying to have to wait for it to load when testing other features.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

CATEGORY_MODULES_MAPPING: dict[str, list[str]] = {
    "dev": [
        # "required",
        # ---
        # "control",
        # "other",
        # "webhook_logs",
    ],
    "personal": [
        # "alerts",
        # "counters",
        # "edit_information",
        "emotes"
        # "keywords",
        # "stable",
        # "tags",
        # "temporary",
        # "timers",
    ],
    "public": [
        # "mmrbot",
        # "meta"
    ],
}


LOAD_ALL_MODULES: bool = False
