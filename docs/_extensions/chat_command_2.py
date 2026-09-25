from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes
from sphinx.ext.autodoc import MethodDocumenter
from sphinx.ext.autodoc._shared import LOGGER
from sphinx.util.docutils import SphinxDirective
from sphinx.writers.html5 import HTML5Translator

if TYPE_CHECKING:
    from docutils.statemachine import StringList
    from sphinx.application import Sphinx


from docutils.parsers.rst import Directive, directives
from docutils.parsers.rst.roles import set_classes
from sphinx.directives.other import Only


class details(nodes.General, nodes.Element):
    pass


class summary(nodes.General, nodes.Element):
    pass


def visit_details_node(self, node):
    self.body.append(self.starttag(node, "div", CLASS="hello"))


def visit_summary_node(self, node):
    self.body.append(self.starttag(node, "summary", CLASS="hello"))
    self.body.append(node.rawsource)


def depart_details_node(self, node):
    self.body.append("</div>\n")


def depart_summary_node(self, node):
    self.body.append("</summary>")


class DetailsDirective(Directive):
    final_argument_whitespace = True
    optional_arguments = 1

    option_spec = {
        "class": directives.class_option,
        "summary-class": directives.class_option,
    }

    has_content = True

    def run(self):
        # set_classes(self.options)
        # self.assert_has_content()

        text = "\n".join(self.content)
        LOGGER.critical(f"xdddddddddddddddddddddddd {self.content} {self.arguments}")
        node = details(self.arguments[0], **self.options)

        # if self.arguments:
        #     summary_node = summary(self.arguments[0], **self.options)
        #     summary_node.source, summary_node.line = self.state_machine.get_source_and_line(self.lineno)
        #     node += summary_node

        # self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


class output_node(nodes.General, nodes.Element):
    pass


class output_directive(Only):
    option_spec = Only.option_spec

    def run(self):
        node = output_node("\n".join(self.content))
        return [node]


def html_visit_output_node(self, node):
    self.body.append(self.starttag(node, "div", CLASS="hello"))


def html_depart_output_node(self, node):
    self.body.append("</div>")


class hello(nodes.General, nodes.Element):
    pass


def visit_hello_node(self: HTML5Translator, node: hello):
    self.body.append(self.starttag(node, "div", CLASS="hello"))


def depart_hello_node(self: HTML5Translator, node: hello):
    self.body.append("</div>")


class HelloDirective(SphinxDirective):
    """A directive to say hello!"""

    required_arguments = 1

    def run(self) -> list[nodes.Node]:
        paragraph_node = nodes.paragraph(text=f"hello {self.arguments[0]}!")
        return [paragraph_node]


class OldChatCommandDocumenter(MethodDocumenter):
    objtype = "xdchatcommand"
    directivetype = MethodDocumenter.objtype

    def add_directive_header(self, sig: str) -> None:
        super().add_directive_header(sig)

        source_name = self.get_sourcename()

        obj = self.parent.__dict__.get(self.object_name, self.object)
        LOGGER.critical("🔥🔥🔥")
        LOGGER.critical(obj.qualified_name)
        self.add_line("\n", "2")
        self.add_line(f".. details:: {obj.qualified_name}", source_name)
        self.add_line("", source_name)
        self.add_line("   yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy", source_name)
        self.add_line("", source_name)
        self.add_line(str({obj.qualified_name}), source_name)
        self.add_line(" ", source_name)
        # self.add_line("=" * len(obj.qualified_name), source_name)
        # self.add_line((obj.qualified_name), source_name)
        # self.add_line("🔥🔥🔥", source_name)
        # self.add_line(f".. py:method:: {obj.qualified_name}", source_name)
        # self.add_line("   ", source_name)
        # self.add_line("   xd", source_name)
        LOGGER.critical(obj.__dict__)
        LOGGER.critical("🔥🔥🔥")

    def add_content(
        self,
        more_content: StringList | None,
    ) -> None:
        super().add_content(more_content)

        # source_name = self.get_sourcename()

        # self.add_line("xd", "3")
        # self.add_line("aaaaaa", "3")


def setup(app: Sphinx) -> dict[str, Any]:
    app.setup_extension("sphinx.ext.autodoc")  # Require autodoc extension
    app.add_autodocumenter(OldChatCommandDocumenter)
    app.add_directive("hello", HelloDirective)
    app.add_node(hello, html=(visit_hello_node, depart_hello_node))
    app.add_node(output_node, html=(html_visit_output_node, html_depart_output_node))
    app.add_directive("output", output_directive)
    app.add_node(details, html=(visit_details_node, depart_details_node))
    app.add_node(summary, html=(visit_summary_node, depart_summary_node))
    app.add_directive("details", DetailsDirective)
    return {"parallel_read_safe": True}


# .. autochatcommand:: modules.public.d7tv.SevenTVFeatures.stv_editor_status
