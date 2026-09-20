# Configuration file for the Sphinx documentation builder.

# -- Project information

import sys
from pathlib import Path

# I don't understand how to solve Pydantic + Sphinx mess properly
# ---------------------------------------------------------------
# os.environ["PROJECT_NAME"] = ""
# os.environ["TWITCH_CLIENT_ID"] = ""
# os.environ["TWITCH_CLIENT_SECRET"] = ""
# os.environ["POSTGRES_VPS"] = ""
# os.environ["POSTGRES_HOME"] = ""
# os.environ["STEAM_FRIEND_IRENE_ID64"] = "1"
# os.environ["STEAM_FRIEND_IRENE_ID32"] = "1"
# os.environ["STEAM_IRENESTEST_USERNAME"] = ""
# os.environ["STEAM_IRENESTEST_PASSWORD"] = ""
# os.environ["STEAM_IRENESBOT_USERNAME"] = ""
# os.environ["STEAM_IRENESBOT_PASSWORD"] = ""
# os.environ["STRATZ_BEARER"] = ""
# os.environ["STEAM_API_KEY"] = ""
# os.environ["SEVEN_TV_BEARER"] = ""
# os.environ["SPOTIFY_AIDENWALLIS"] = ""
# os.environ["EVENTSUB"] = ""
# os.environ["WEBHOOK_LOGGER"] = ""
# os.environ["WEBHOOK_ERROR"] = ""
# os.environ["WEBHOOK_STREAM_NOTIFS"] = ""
# os.environ["WEBHOOK_HEARTBEAT"] = ""
# os.environ["WEBHOOK_HEARTBEAT"] = ""

sys.path.insert(0, str(Path("..", "src").resolve()))

project = "IrenesBot - Documentation"
copyright = "Copyright &copy; 2020-present; Aluerie"  # noqa: A001
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
            "url": "https://github/Aluerie/IrenesBot",
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
    # Extra
    "sphinx_design",
    "sphinx_iconify",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
intersphinx_disabled_domains = ["std"]


templates_path = ["_templates"]


epub_show_urls = "no"
