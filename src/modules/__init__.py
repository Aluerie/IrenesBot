"""
_Insert Module Docstring Here_.

License
-------
* This Source Code Form is subject to the terms of the [Mozilla Public License v2.0](<http://mozilla.org/MPL/2.0/>).
* Copyright (C) 2020-present [@Aluerie](<https://github.com/Aluerie>).
"""

# VPS / HOME import difference
# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import logging
from pathlib import Path
from pkgutil import iter_modules

from shared.globals import Global7TV

try:
    from modules_subset import MODULES_SUBSET  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:
    MODULES_SUBSET: dict[str, list[str]] = {}  # pyright: ignore[reportConstantRedefinition]

__all__ = (
    "MODULES_EMOTE_MAPPING",
    "get_modules",
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# named modules const
PUBLIC_D9MMRBOT = "modules.public.d9kmmrbot"
DEV_REQUIRED = "modules.dev.required"


MODULES_EMOTE_MAPPING: dict[str, str] = {
    "modules.dev.required": "",
    "modules.dev.control": "",
    "modules.dev.other": "",
    "modules.dev.webhook_logs": "",
    "modules.personal.alerts": "",
    "modules.personal.counters": "",
    "modules.personal.discord_notifications": "",
    "modules.personal.emotes_common": "",
    "modules.personal.information": "",
    "modules.personal.keywords": "",
    "modules.personal.stable": "",
    "modules.personal.tags": "",
    "modules.personal.temporary": "",
    "modules.personal.timers": "",
    "modules.public": "",
    "modules.public.d9kmmrbot": "",
    "modules.public.d7tv": Global7TV.FeelsDankMan,
    "modules.public.first": "",
    "modules.public.meta": "",
    "modules.beta": "",
}


def get_subset_modules(categories: dict[str, list[str]]) -> tuple[str, ...]:
    """Get a tuple of modules to load from a friendly formatted categories dictionary.

    Returns
    -------
    tuple[str, ...]
        Tuple of modules to load. Modules are listed in a dot-format, i.e. `"modules.public.dota_rp_flow"`.
    """
    modules_to_load: tuple[str, ...] = (
        # Categorized modules
        *tuple(
            f"modules.{category}.{extension}"
            for category, extensions in categories.items()
            for extension in extensions
            if extensions
        ),
        # Extras
        "modules.beta",
    )
    # Component-based dependencies
    if PUBLIC_D9MMRBOT in modules_to_load:
        modules_to_load += (DEV_REQUIRED,)
    return modules_to_load


DISABLED_MODULES: tuple[str, ...] = (
    # modules that should not be loaded
    "modules.beta",
    # currently disabled
    # "modules.public.dota",
)


def get_modules(*, is_subset_mode: bool) -> tuple[str, ...]:
    """Get list of bot modules to load.

    Returns
    -------
    tuple[str, ...]
        Tuple of modules for the bot to load.
        The modules are given in a full dot form.
        Example: `('modules.personal.alerts', 'modules.dev.control', 'modules.public.dota_rp_flow', )`
    """
    if is_subset_mode:
        # assume testing specific modules from `m.py`
        return get_subset_modules(MODULES_SUBSET)

    # assume running full bot functionality (besides `DISABLED_MODULES`)
    current_folder = "src/" + str(__package__)
    modules: tuple[str, ...] = ()
    module_categories = [path for path in Path(current_folder).iterdir() if path.is_dir() and not path.name.startswith("_")]
    for module_category in module_categories:
        # Personal and Public modules
        modules += tuple(
            module.name
            for module in iter_modules([module_category.absolute()], prefix=f"{__package__}.{module_category.name}.")
            if module.name not in DISABLED_MODULES
        )

    # Could just do, lol
    # modules = tuple(module for module in MODULES if module not in DISABLED_MODULES)

    log.debug("The list of modules (%s total) to load: %s", len(modules), modules)
    return modules
