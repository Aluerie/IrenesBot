"""Modules to load when `bot.subset_mode` is `True`.

Rename this file to 'm.py' and choose modules you want to load when
testing version of the bot is running.
Currently, I'm being lazy and it assumes "testing" version when it's Windows OS.

This is useful when we want to debug select features/modules of the bot without
launching the whole thing. Especially because some modules,
i.e. Dota 2 related ones take quite a long time to launch.
So that would be annoying to have to wait for it to load when testing other features.

I named it 'm.py' just so the tab name in my text editor is short (it's always pinned).
Maybe I should think of a better name;
"""

CATEGORY_MODULES_MAPPING = {
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
        # "9kmmrbot",
        # "meta"
    ],
}


LOAD_ALL_MODULES: bool = False
