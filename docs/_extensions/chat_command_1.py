from __future__ import annotations

from docutils import nodes

# class HelloRole(SphinxRole):
#     """A role to say hello!"""
#     def run(self) -> tuple[list[nodes.Node], list[nodes.system_message]]:
#         node = nodes.inline(text=f"Hello {self.text}!")
#         return [node], []
from docutils.parsers.rst import Directive
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective, SphinxRole
from sphinx.util.typing import ExtensionMetadata


class HelloDirective(Directive):
    """A directive to say hello!"""

    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}
    has_content = True

    def run(self) -> list[nodes.Node]:
        paragraph_node = nodes.container(text=f"hello {''.join(self.arguments)}!", CLASS="hello")
        return [paragraph_node]


def setup(app: Sphinx) -> ExtensionMetadata:
    # app.add_role("hello", HelloRole())
    app.add_directive("hello", HelloDirective)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
