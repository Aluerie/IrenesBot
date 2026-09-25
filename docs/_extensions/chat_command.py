from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.parsers.rst.roles import set_classes
from sphinx.ext.autodoc import ClassDocumenter, Documenter, MethodDocumenter, bool_option
from sphinx.util.logging import getLogger

log = getLogger(__name__)

if TYPE_CHECKING:
    from docutils.statemachine import StringList
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata


class commandname(nodes.General, nodes.Element):
    pass


def visit_commandname_node(self, node):
    self.body.append(self.starttag(node, "div", CLASS="hello"))


def depart_commandname_node(self, node):
    self.body.append("</div>\n")


# class DetailsDirective(Directive):
#     # final_argument_whitespace = True
#     # optional_arguments = 1

#     # option_spec = {
#     #     "class": directives.class_option,
#     #     "summary-class": directives.class_option,
#     # }

#     has_content = True

#     def run(self):
#         # set_classes(self.options)
#         # self.assert_has_content()

#         log.critical(f"🏠🏠🏠 {self.content} {self.arguments}")

#         text = "\n".join(self.content)
#         # node = commandname(" ".join(self.arguments), **self.options)

#         node = commandname("xd")
#         # if self.arguments:
#         #     summary_node = commandname(" ".join(self.arguments), **self.options)
#         #     summary_node.source, summary_node.line = self.state_machine.get_source_and_line(self.lineno)
#         #     node += summary_node

#         # self.state.nested_parse(self.content, self.content_offset, node)
#         return [node]


class details(nodes.General, nodes.Element):
    pass


class summary(nodes.General, nodes.Element):
    pass


def visit_details_node(self, node):
    self.body.append(self.starttag(node, "details", CLASS=node.attributes.get("class", "")))


def visit_summary_node(self, node):
    self.body.append(self.starttag(node, "h3", CLASS="hello py sig sig-object"))
    self.body.append(node.rawsource)


def depart_details_node(self, node):
    self.body.append("</details>\n")


def depart_summary_node(self, node):
    self.body.append("</h3>")


class DetailsDirective(Directive):
    final_argument_whitespace = True
    optional_arguments = 1

    option_spec = {
        "class": directives.class_option,
        "summary-class": directives.class_option,
    }

    has_content = False

    def run(self):
        set_classes(self.options)
        # self.assert_has_content()

        # text = "\n".join(self.content)
        # node = details(text, **self.options)

        if self.arguments:
            summary_node = summary(self.arguments[0], **self.options)
            summary_node.source, summary_node.line = self.state_machine.get_source_and_line(self.lineno)
            node = summary_node

        # self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


class ChatCommandDocumenter(MethodDocumenter):
    objtype = "chatcommand"
    directivetype = MethodDocumenter.objtype

    def add_directive_header(self, sig: str) -> None:
        # super().add_directive_header(sig)

        source_name = self.get_sourcename()
        obj = self.parent.__dict__.get(self.object_name, self.object)
        # self.add_line(f".. details:: {obj.qualified_name}", source_name)
        self.add_line(f"{obj.qualified_name}", source_name)
        self.add_line("-" * len(obj.qualified_name), source_name)

        # https://stackoverflow.com/a/23096806/19217368
        self.add_line("..", "")
        # self.add_line("x", "x")

    def add_content(
        self,
        more_content: StringList | None,
    ) -> None:

        super().add_content(more_content)
        # self.add_line("xdddddddddddddddddddddd", "xd")

        # source_name = self.get_sourcename()
        # enum_object: IntEnum = self.object
        # use_hex = self.options.hex
        # self.add_line("", source_name)

        # for the_member_name, enum_member in enum_object.__members__.items():  # type: ignore[attr-defined]
        #     the_member_value = enum_member.value
        #     if use_hex:
        #         the_member_value = hex(the_member_value)

        #     self.add_line(f"**{the_member_name}**: {the_member_value}", source_name)
        #     self.add_line("", source_name)


def setup(app: Sphinx) -> ExtensionMetadata:
    app.setup_extension("sphinx.ext.autodoc")  # Require autodoc extension
    app.add_autodocumenter(ChatCommandDocumenter)
    app.add_node(commandname, html=(visit_commandname_node, depart_commandname_node))
    app.add_node(details, html=(visit_details_node, depart_details_node))
    app.add_node(summary, html=(visit_summary_node, depart_summary_node))
    app.add_directive("details", DetailsDirective)
    return {
        "parallel_read_safe": True,
    }
