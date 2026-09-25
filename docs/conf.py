"""Configuration file for the Sphinx documentation builder."""

# -- Project information
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path("..", "src").resolve()))
sys.path.append(str(Path("_extensions").resolve()))

if TYPE_CHECKING:
    from sphinx import application


project = "IrenesBot - Documentation"
copyright = "Copyright &copy; 2020-present; Aluerie (Irene Adler)"  # noqa: A001
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
    # Extra
    "sphinx_design",
    "sphinx_iconify",
    "chat_command",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
intersphinx_disabled_domains = ["std"]


templates_path = ["_templates"]


epub_show_urls = "no"


def remove_module_docstring(app: application.Sphinx, what: str, name: str, obj: Any, options: Any, lines: list[Any]) -> None:  # noqa: ARG001
    """Delete all module docstrings.

    Generally, We include license/copyright notions there so we don't want the documentation to be spammed with it.

    Source
    ------
    * https://stackoverflow.com/a/18031024/19217368
    """
    if what == "module":
        del lines[:]


def setup(app: application.Sphinx) -> None:
    """Sphinx framework. Adding some handlers."""
    app.connect("autodoc-process-docstring", remove_module_docstring)
