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
    from twitchio.ext import commands

log = getLogger(__name__)

if TYPE_CHECKING:
    from docutils.statemachine import StringList
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

PREFIX = "!"

GUARD_NOTE_MAPPING = {
    "is_moderator": "Only channel moderators are allowed to use this command.",
    "is_owner": "Only Irene_Adler__ is allowed to use this command.",
    "is_broadcaster": "Only broadcaster is allowed to use this command.",
    "is_broadcaster_or_dev": "Only broadcaster is allowed to use this command.",
    "is_broadcaster_dev_or_editor": "Only broadcaster and 7tv editors can use this command.",
    "is_broadcaster_dev_editor_or_adder": (
        "Only broadcaster, 7tv editors and a person who added the emote can use this command."
    ),
}


class ChatCommandDocumenter(MethodDocumenter):
    """Chat Command Documenter."""

    objtype = "chatcommand"
    directivetype = MethodDocumenter.objtype
    content_indent = ""

    @override
    def add_directive_header(self, sig: str) -> None:
        sourcename = self.get_sourcename()
        cmd: commands.Command[Any, Any] = self.parent.__dict__.get(self.object_name, self.object)

        command_name = f"{PREFIX}{cmd.qualified_name}"
        self.add_line(command_name, sourcename)
        self.add_line("-" * len(command_name), sourcename)

        # Syntax
        # self.add_line(".. rubric:: **Syntax**", sourcename)
        # self.add_line("", sourcename)
        self.add_line(".. code-block::", sourcename)
        self.add_line("   :caption: Usage Syntax", sourcename)
        self.add_line("", sourcename)
        params = " " + " ".join(f"<{param}>" for param in cmd.parameters) if cmd.parameters else ""
        self.add_line(f"   {command_name}{params}\n", sourcename)
        if cmd.aliases:
            parent = f"{cmd.full_parent_name} " if cmd.full_parent_name else ""
            aliases = ", ".join(f"``{PREFIX}{parent}{alias}``" for alias in cmd.aliases)
            self.add_line(".. admonition:: Aliases", sourcename)
            self.add_line("   :class: dropdown", sourcename)
            self.add_line("", sourcename)
            self.add_line(f"   {aliases}", sourcename)
        self.add_line("", sourcename)

        # Permissions
        if cmd.guards:
            self.add_line(".. admonition:: Permissions", sourcename)
            self.add_line("   :class: hint", sourcename)
            self.add_line("", sourcename)
            note_description = "\n".join(
                GUARD_NOTE_MAPPING.get(
                    guard_name := getattr(guard, "__qualname__", "unknown_guard").removesuffix(".<locals>.predicate"),
                    guard_name,
                )
                for guard in cmd.guards
            )
            self.add_line(f"   {note_description}", sourcename)
        self.add_line("", sourcename)

        self.add_line(".. admonition:: Description", sourcename)
        self.add_line("   :class: note", sourcename)
        self.add_line("", sourcename)
        help_ = cmd.help or "No Description."
        doc = NumpyDocString(help_)

        for line in doc["Summary"]:
            self.add_line(f"   {line}", sourcename)
        self.add_line("", sourcename)
        for line in doc["Extended Summary"]:
            self.add_line(f"   {line}", sourcename)
        self.add_line("", sourcename)

        if doc["Parameters"]:
            # self.add_line(".. rubric:: Arguments", sourcename)
            # self.add_line("", sourcename)
            self.add_line(".. admonition:: Arguments", sourcename)
            self.add_line("   :class: tip", sourcename)
            self.add_line("", sourcename)
            for param in doc["Parameters"]:
                for line_count, param_line in enumerate(param.desc):
                    if line_count == 0:
                        self.add_line(f"   * ``<{param.name}>`` -", sourcename)
                    self.add_line(f"     {param_line}", sourcename)
                self.add_line("", sourcename)
            self.add_line("", sourcename)
        if doc["Examples"]:
            # self.add_line(".. rubric:: Examples", sourcename)
            # self.add_line("", sourcename)
            self.add_line(".. admonition:: Examples", sourcename)
            self.add_line("   :class: caution", sourcename)
            self.add_line("", sourcename)
            for line in doc["Examples"]:
                self.add_line(f"   {line}", sourcename)
            self.add_line("", sourcename)

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
