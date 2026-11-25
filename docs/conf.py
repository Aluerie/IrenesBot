# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Configuration file for the Sphinx documentation builder."""

# -- Project information

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotenv import dotenv_values

sys.path.insert(0, str(Path("..", "src").resolve()))
sys.path.append(str(Path("_extensions").resolve()))

# autodoc imports the bot's modules, and `config.py` requires every setting from `.env` on import.
# The placeholder values from `.env.example` are enough for that, so load them unless real ones are already set.
for key, value in dotenv_values(Path("..", ".env.example")).items():
    if value is not None:
        os.environ.setdefault(key, value)

if TYPE_CHECKING:
    from sphinx import application


project = "IrenesBot - Documentation"
copyright = "Copyright &copy; 2020-present; Aluerie (Irene Adler)"  # ruff: ignore[builtin-variable-shadowing]
author = "Aluerie"

release = "0.7"
version = "0.7.7"

html_favicon = "_static/favicon.ico"

language = "en"

html_title = "@IrenesBot"
html_static_path = ["_static"]
html_css_files = [
    "custom.css",
]
html_theme = "shibuya"

html_theme_options = {
    "accent_color": "purple",
}
# html_context = {
#     "source_type": "github",
#     "source_user": "Aluerie",
#     "source_repo": "IrenesBot",
# }

html_theme_options = {
    "nav_links": [
        {
            "title": "🎥 Twitch",
            "url": "https://twitch.tv/IrenesBot",
        },
        {
            "title": "🐈‍⬛ GitHub",
            "url": "https://github.com/Aluerie/IrenesBot",
        },
        {
            "title": "💋 Irene_Adler__",
            "url": "https://twitch.tv/Irene_Adler__",
        },
    ],
    "page_layout": "default",
    "show_ai_links": False,
    "nav_socials": [],
    "foot_socials": [
        {
            "name": "GitHub",
            "url": "https://github.com/Aluerie",
            "icon": "simple-icons:github",
        }
    ],
    # "globaltoc_expand_depth": 1,
}


extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    # "numpydoc",
    "sphinx_design",
    "sphinx_iconify",
    "chat_command",
    "sphinx_copybutton",
    "sphinx_togglebutton",
    "translate_lang_table"
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
intersphinx_disabled_domains = ["std"]
# Without a timeout, an inventory download that stalls (it does on my home network) hangs the whole build.
# With it, the build just warns and leaves those links unresolved.
intersphinx_timeout = 15


templates_path = ["_templates"]


epub_show_urls = "no"


def remove_module_docstring(
    app: application.Sphinx,  # ruff: ignore[unused-function-argument]
    what: str,
    name: str,  # ruff: ignore[unused-function-argument]
    obj: Any,  # ruff: ignore[unused-function-argument]
    options: Any,  # ruff: ignore[unused-function-argument]
    lines: list[Any],
) -> None:
    """Delete all module docstrings.

    Generally, We include license/copyright notions there so we don't want the documentation to be spammed with it.

    Source
    ------
    * https://stackoverflow.com/a/18031024/19217368
    """
    if what == "module":
        del lines[:]  # ruff: ignore[delete-full-slice]


def setup(app: application.Sphinx) -> None:
    """Sphinx framework. Adding some handlers."""
    app.connect("autodoc-process-docstring", remove_module_docstring)
