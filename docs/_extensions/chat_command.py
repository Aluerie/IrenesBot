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
    "is_emote_owner": (
        "Only broadcaster and a person who initially requested this emote (e.g. via a channel redeem) "
        "to be added can use this command."
    ),
}


class FakeChatCommandDocumenter(MethodDocumenter):
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
        # self.add_line(".. admonition:: Syntax", sourcename)
        # self.add_line("   :class: important", sourcename)
        # self.add_line("", sourcename)
        params = " " + " ".join(f"<{param}>" for param in cmd.parameters) if cmd.parameters else ""
        self.add_line(f"**Syntax**: ``{command_name}{params}``\n", sourcename)
        self.add_line("", sourcename)
        if cmd.aliases:
            parent = f"{cmd.full_parent_name} " if cmd.full_parent_name else ""
            aliases = " ".join(f"``{PREFIX}{parent}{alias}``" for alias in cmd.aliases)
            self.add_line(f"**Aliases**: {aliases}", sourcename)
        self.add_line("", sourcename)

        help_ = cmd.help or "No Description."
        doc = NumpyDocString(help_)

        if doc["Parameters"]:
            # self.add_line(".. rubric:: Arguments", sourcename)
            # self.add_line("", sourcename)
            # self.add_line(".. admonition:: Arguments", sourcename)
            # self.add_line("   :class: tip", sourcename)
            # self.add_line("", sourcename)
            self.add_line("**Arguments**:", sourcename)
            self.add_line("", sourcename)
            for param in doc["Parameters"]:
                self.add_line(f"* ``<{param.name}>`` - {' '.join(param.desc)}", sourcename)
            self.add_line("", sourcename)

        # Permissions
        if cmd.guards:
            self.add_line(".. admonition:: Permissions", sourcename)
            self.add_line("   :class: hint", sourcename)
            self.add_line("", sourcename)
            note_description = "\n".join(
                GUARD_NOTE_MAPPING.get(guard_name := guard.__qualname__.removesuffix(".<locals>.predicate"), guard_name)
                for guard in cmd.guards
            )
            self.add_line(f"   {note_description}", sourcename)
        self.add_line("", sourcename)

        # self.add_line(".. admonition:: Description", sourcename)
        # self.add_line("   :class: note", sourcename)
        # self.add_line("", sourcename)

        for line in doc["Summary"]:
            self.add_line(f"{line}", sourcename)
        self.add_line("", sourcename)
        for line in doc["Extended Summary"]:
            self.add_line(f"{line}", sourcename)
        self.add_line("", sourcename)

        if doc["Examples"]:
            # self.add_line(".. rubric:: Examples", sourcename)
            # self.add_line("", sourcename)
            # self.add_line(".. admonition:: Examples", sourcename)
            # self.add_line("   :class: caution", sourcename)
            # self.add_line("", sourcename)
            self.add_line("**Examples:**", sourcename)
            self.add_line("", sourcename)
            for line in doc["Examples"]:
                self.add_line(f"{line}", sourcename)
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
        self.add_line(".. admonition:: Syntax", sourcename)
        self.add_line("   :class: important", sourcename)
        self.add_line("", sourcename)
        params = " " + " ".join(f"<{param}>" for param in cmd.parameters) if cmd.parameters else ""
        self.add_line(f"   * **Usage**: ``{command_name}{params}``\n", sourcename)
        if cmd.aliases:
            parent = f"{cmd.full_parent_name} " if cmd.full_parent_name else ""
            aliases = " ".join(f"``{PREFIX}{parent}{alias}``" for alias in cmd.aliases)
            self.add_line(f"   * **Aliases**: {aliases}", sourcename)
        self.add_line("", sourcename)

        # Permissions
        if cmd.guards:
            self.add_line(".. admonition:: Permissions", sourcename)
            self.add_line("   :class: hint", sourcename)
            self.add_line("", sourcename)
            note_description = "\n".join(
                GUARD_NOTE_MAPPING.get(guard_name := guard.__qualname__.removesuffix(".<locals>.predicate"), guard_name)
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
                self.add_line(f"   * ``<{param.name}>`` - {' '.join(param.desc)}", sourcename)
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
    """Setup. Framework of Sphinx."""
    app.setup_extension("sphinx.ext.autodoc")  # Require autodoc extension
    app.add_autodocumenter(ChatCommandDocumenter)
    return {
        "parallel_read_safe": True,
    }
