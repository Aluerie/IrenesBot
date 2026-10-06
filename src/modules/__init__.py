"""Get modules to load.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import logging
from pathlib import Path
from pkgutil import iter_modules

try:
    from modules_subset import MODULES_SUBSET  # ty: ignore[unresolved-import, unused-ignore-comment, unused-ignore-comment]
except ModuleNotFoundError:
    MODULES_SUBSET: dict[str, list[str]] = {}

__all__ = ("get_modules",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def get_subset_modules(categories: dict[str, list[str]]) -> tuple[str, ...]:
    """Get a tuple of modules to load from a friendly formatted categories dictionary.

    Returns
    -------
    tuple[str, ...]
        Tuple of modules to load. Modules are listed in a dot-format, i.e. `"modules.public.dota_rp_flow"`.
    """
    return (
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


DISABLED_MODULES: tuple[str, ...] = (
    # modules that should not be loaded
    "modules.beta",
    # currently disabled
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

    log.debug("The list of modules (%s total) to load: %s", len(modules), modules)
    return modules
