"""Defines the MarkdownParser class for parsing Markdown documents."""

from markdown_it import MarkdownIt

from engine.extraction.models.doc import Document, Heading, MarkdownElement


class MarkdownParser:
    """
    Parses Markdown content into a Document model.
    """

    def parse(self, content: str) -> Document:
        """
        Parses the given Markdown content and returns a Document model.
        """
        md = MarkdownIt()
        tokens = md.parse(content)

        root = MarkdownElement(type="document", children=[])
        parent_stack = [root]

        for i, token in enumerate(tokens):
            elem = None
            if token.nesting == 1:  # Opening token
                elem = MarkdownElement(
                    type=token.type,
                    start_line=token.map[0] + 1 if token.map else None,
                    level=(
                        int(token.tag[1:])
                        if token.type == "heading_open"
                        and token.tag
                        and token.tag.startswith("h")
                        and token.tag[1:].isdigit()
                        else None
                    ),
                    token_index=i,
                    tag=token.tag,
                )
                parent_stack[-1].children.append(elem)
                parent_stack.append(elem)
            elif token.nesting == -1:
                if len(parent_stack) > 1:
                    parent_stack[-1].end_line = token.map[1] if token.map else None
                    parent_stack.pop()
            elif token.nesting == 0:
                elem = MarkdownElement(
                    type=token.type,
                    content=token.content.strip() if token.content else None,
                    start_line=token.map[0] + 1 if token.map else None,
                    end_line=token.map[1] if token.map else None,
                    token_index=i,
                    tag=token.tag,
                )
                parent_stack[-1].children.append(elem)

        headings = []
        title = "Untitled Document"
        for element in root.children:
            if element.type == "heading_open" and element.level == 1:
                title = element.children[0].content if element.children else "Untitled"
            if element.type == "heading_open":
                headings.append(
                    Heading(
                        level=element.level,
                        text=element.children[0].content if element.children else "",
                        line_number=element.start_line,
                    )
                )

        return Document(
            title=title, content=content, headings=headings, elements=root.children
        )
