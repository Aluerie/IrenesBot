"""Chat-command directive.

This is all quite badly coded but idk how to make it better.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from numpydoc.docscrape import NumpyDocString
from sphinx.ext.autodoc import MethodDocumenter
from sphinx.util.logging import getLogger

if TYPE_CHECKING:
    from docutils.statemachine import StringList
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata
    from twitchio.ext import commands

log = getLogger(__name__)


PREFIX = "!"

GUARD_NOTE_MAPPING = {
    "is_moderator": "Broadcaster, moderators",
    "is_owner": "Only Irene",
    "is_broadcaster": "Broadcaster",
    "is_broadcaster_or_dev": "Broadcaster",
    "_is_broadcaster_dev_or_editor_predicate": "Broadcaster, 7tv editors",
    "is_broadcaster_dev_editor_or_adder": ("Broadcaster, 7tv editors, a person who added the emote"),
}


class ChatCommandDocumenter(MethodDocumenter):
    """Chat Command Documenter."""

    objtype = "chatcommand"
    directivetype = MethodDocumenter.objtype
    content_indent = ""

    @override
    def add_directive_header(self, sig: str) -> None:
        source = self.get_sourcename()
        cmd: commands.Command[Any, Any] = self.parent.__dict__.get(self.object_name, self.object)

        command_name = f"{PREFIX}{cmd.qualified_name}"
        self.add_line(command_name, source)
        self.add_line("-" * len(command_name), source)

        # Syntax
        # self.add_line(".. rubric:: **Syntax**", sourcename)
        # self.add_line("", sourcename)
        self.add_line(".. code-block::", source)
        self.add_line("   :caption: Usage Syntax", source)
        self.add_line("", source)
        params = " " + " ".join(f"<{param}>" for param in cmd.parameters) if cmd.parameters else ""
        self.add_line(f"   {command_name}{params}\n", source)
        if cmd.aliases:
            parent = f"{cmd.full_parent_name} " if cmd.full_parent_name else ""
            aliases = ", ".join(f"``{PREFIX}{parent}{alias}``" for alias in cmd.aliases)
            self.add_line(".. admonition:: Aliases", source)
            self.add_line("   :class: dropdown", source)
            self.add_line("", source)
            self.add_line(f"   {aliases}", source)
        self.add_line("", source)

        self.add_line(".. grid:: 1 1 2 3", source)
        self.add_line("   :gutter: 2", source)
        self.add_line("   :padding: 0", source)
        self.add_line("   :class-container: surface", source)
        self.add_line("", source)
        self.add_line("   .. grid-item-card:: :octicon:`lock` Who can use", source)
        self.add_line("", source)
        permissions_line = (
            "\n".join(
                GUARD_NOTE_MAPPING.get(
                    guard_name := getattr(guard, "__qualname__", "unknown_guard").removesuffix(".<locals>.predicate"),
                    guard_name,
                )
                for guard in cmd.guards
            )
            if cmd.guards
            else "Everybody"
        )
        self.add_line(f"      {permissions_line}", source)
        self.add_line("", source)
        self.add_line("   .. grid-item-card:: :octicon:`clock` Cooldown", source)
        self.add_line("", source)
        self.add_line("      Will implement later", source)
        self.add_line("", source)

        self.add_line(".. admonition:: Description", source)
        self.add_line("   :class: note", source)
        self.add_line("", source)
        help_ = cmd.help or "No Description."
        doc = NumpyDocString(help_)

        for line in doc["Summary"]:
            self.add_line(f"   {line}", source)
        self.add_line("", source)
        for line in doc["Extended Summary"]:
            self.add_line(f"   {line}", source)
        self.add_line("", source)

        if doc["Parameters"]:
            # self.add_line(".. rubric:: Arguments", sourcename)
            # self.add_line("", sourcename)
            self.add_line(".. admonition:: Arguments", source)
            self.add_line("   :class: tip", source)
            self.add_line("", source)
            for param in doc["Parameters"]:
                first, *rest = param.desc or [""]
                self.add_line(f"   * ``<{param.name}>`` - {first}", source)
                for line in rest:
                    self.add_line(f"     {line}", source)
                self.add_line("", source)
        if doc["Examples"]:
            # self.add_line(".. rubric:: Examples", sourcename)
            # self.add_line("", sourcename)
            self.add_line(".. admonition:: Examples", source)
            self.add_line("   :class: caution", source)
            self.add_line("", source)
            for line in doc["Examples"]:
                self.add_line(f"   {line}", source)
            self.add_line("", source)

    @override
    def format_signature(self, **kwargs: Any) -> str:
        return ""

    @override
    def add_content(
        self,
        more_content: StringList | None,
    ) -> None:
        return None


def setup(app: Sphinx) -> ExtensionMetadata:
    """Set up. Framework of Sphinx."""
    app.setup_extension("sphinx.ext.autodoc")  # Require autodoc extension
    app.add_autodocumenter(ChatCommandDocumenter)
    return {
        "parallel_read_safe": True,
    }
