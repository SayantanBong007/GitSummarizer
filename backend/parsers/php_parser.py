import tree_sitter_php as tsphp
from tree_sitter import Language, Node

from backend.agents.state import ParsedSymbol
from backend.parsers.base import BaseParser


class PHPParser(BaseParser):
    language_name = "php"
    extensions = frozenset({".php"})

    def _build_language(self) -> Language:
        return Language(tsphp.language_php())

    def _extract_symbols(self, root: Node, source: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(root, source, symbols, parent_class=None)
        return symbols

    def _walk(
        self, node: Node, source: str, symbols: list[ParsedSymbol], parent_class: str | None
    ) -> None:
        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            class_name = self._node_text(name_node, source) if name_node else "unknown"
            symbols.append(ParsedSymbol(
                kind="class", name=class_name,
                start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                docstring=None, parent=None,
            ))
            for child in node.children:
                self._walk(child, source, symbols, parent_class=class_name)
            return
        elif node.type in ("function_definition", "method_declaration"):
            name_node = node.child_by_field_name("name")
            name = self._node_text(name_node, source) if name_node else "<fn>"
            symbols.append(ParsedSymbol(
                kind="method" if parent_class else "function",
                name=name,
                start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                docstring=None, parent=parent_class,
            ))
        for child in node.children:
            self._walk(child, source, symbols, parent_class)

    def _extract_imports(self, root: Node, source: str) -> list[str]:
        allowed_types = (
            "namespace_use_declaration",
            "require_expression",
            "include_expression",
        )
        return [
            self._node_text(child, source).strip()
            for child in root.children
            if child.type in allowed_types
        ]
