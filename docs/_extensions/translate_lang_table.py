"""Sphinx directive that renders the ``!translate`` supported languages table.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import math
import operator
from typing import TYPE_CHECKING, ClassVar, override

from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

from shared.translate import LANGUAGES

if TYPE_CHECKING:
    from docutils import nodes
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

__all__ = ("LanguageTable", "setup")


class LanguageTable(SphinxDirective):
    """Render ``shared.translate.LANGUAGES`` as a ``list-table``.

    Languages are sorted by name and laid out column-major, so they read alphabetically top to bottom,
    then left to right.

    Examples
    --------
    .. code-block:: rst

        .. language-table::
           :columns: 4
    """

    has_content = False
    option_spec: ClassVar = {"columns": directives.positive_int}  # ty: ignore[invalid-attribute-override]

    @override
    def run(self) -> list[nodes.Node]:
        """Build the table nodes."""
        columns: int = self.options.get("columns", 4)
        languages = sorted(LANGUAGES.items(), key=operator.itemgetter(1))
        rows = math.ceil(len(languages) / columns)

        lines = [
            ".. list-table::",
            f"   :widths: {' '.join(['1'] * columns * 2)}",
            "   :header-rows: 1",
            "",
        ]
        # header
        lines.extend((
            "   * - Code",
            "     - Language",
        ))
        for _ in range(columns - 1):
            lines.extend((
                "     - Code",
                "     - Language",
            ))

        # body, column-major fill
        for row in range(rows):
            for column in range(columns):
                index = column * rows + row
                prefix = "   * -" if column == 0 else "     -"
                if index < len(languages):
                    code, name = languages[index]
                    lines.extend((
                        f"{prefix} ``{code}``",
                        f"     - {name.capitalize()}",
                    ))
                else:
                    # pad the last column so every row has the same number of cells
                    lines.extend((
                        prefix,
                        "     -",
                    ))

        return self.parse_text_to_nodes("\n".join(lines))


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the directive (Sphinx entry point)."""
    app.add_directive("language-table", LanguageTable)
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
