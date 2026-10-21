"""Chat-command directive.

This is all quite badly coded but idk how to make it better.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

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

    def _emit(self, *lines: str) -> None:
        source = self.get_sourcename()
        for line in lines:
            self.add_line(line, source)

    def _add_header(self, cmd: commands.Command[Any, Any]) -> None:
        command_name = f"{PREFIX}{cmd.qualified_name}"
        self._emit(
            command_name,
            "-" * len(command_name),
        )

    def _add_syntax(self, cmd: commands.Command[Any, Any]) -> None:
        command_name = f"{PREFIX}{cmd.qualified_name}"
        params = " " + " ".join(f"<{param}>" for param in cmd.parameters) if cmd.parameters else ""
        self._emit(
            ".. code-block::",
            "   :caption: Usage Syntax",
            "",
            f"   {command_name}{params}",
            "",
        )

    def _add_aliases(self, cmd: commands.Command[Any, Any]) -> None:
        to_emit: list[str] = []
        if cmd.aliases:
            parent = f"{cmd.full_parent_name} " if cmd.full_parent_name else ""
            aliases = ", ".join(f"``{PREFIX}{parent}{alias}``" for alias in cmd.aliases)
            to_emit += [
                ".. admonition:: Aliases",
                "   :class: dropdown",
                "",
                f"   {aliases}",
            ]
        to_emit.append("")
        self._emit(*to_emit)

    def _add_permissions_cooldown(self, cmd: commands.Command[Any, Any]) -> None:
        permissions = (
            "; ".join(
                GUARD_NOTE_MAPPING.get(
                    guard_name := getattr(guard, "__qualname__", "unknown_guard").removesuffix(".<locals>.predicate"),
                    guard_name,
                )
                for guard in cmd.guards
            )
            if cmd.guards
            else "Everybody"
        )
        self._emit(
            ".. grid:: 1 1 2 3",
            "   :gutter: 2",
            "   :padding: 0",
            "   :class-container: surface",
            "",
            "   .. grid-item-card:: :octicon:`lock` Who can use",
            "",
            f"      {permissions}",
            "",
            "   .. grid-item-card:: :octicon:`clock` Cooldown",
            "",
            "      Will implement later",
            "",
        )

    def _add_description(self, doc: NumpyDocString) -> None:
        summary, extended = doc["Summary"], doc["Extended Summary"]
        body = [*summary, "", *extended] if extended else summary
        self._emit(
            ".. admonition:: Description",
            "   :class: note",
            "",
            *(f"   {line}" for line in body),
            "",
        )

    def _add_arguments(self, doc: NumpyDocString) -> None:
        if not doc["Parameters"]:
            return
        lines = [
            ".. admonition:: Arguments",
            "   :class: tip",
            "",
        ]
        for param in doc["Parameters"]:
            first, *rest = param.desc or [""]
            lines.append(f"   * ``<{param.name}>`` - {first}")
            lines.extend(f"     {line}" for line in rest)
            lines.append("")
        self._emit(*lines)

    def _add_examples(self, doc: NumpyDocString) -> None:
        if not doc["Examples"]:
            return
        lines = [
            ".. admonition:: Examples",
            "   :class: caution",
            "",
        ]
        lines.extend(f"   {line}" for line in doc["Examples"])
        lines.append("")
        self._emit(*lines)

    @override
    def add_directive_header(self, sig: str) -> None:
        cmd: commands.Command[Any, Any] = self.parent.__dict__.get(self.object_name, self.object)

        self._add_header(cmd)
        self._add_syntax(cmd)
        self._add_aliases(cmd)
        self._add_permissions_cooldown(cmd)

        help_ = cmd.help or "No Description."
        doc = NumpyDocString(help_)

        self._add_description(doc)
        self._add_arguments(doc)
        self._add_examples(doc)

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
