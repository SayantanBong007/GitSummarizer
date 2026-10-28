import tree_sitter_rust as tsrust
from tree_sitter import Language, Node

from backend.agents.state import ParsedSymbol
from backend.parsers.base import BaseParser


class RustParser(BaseParser):
    language_name = "rust"
    extensions = frozenset({".rs"})

    def _build_language(self) -> Language:
        return Language(tsrust.language())

    def _extract_symbols(self, root: Node, source: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(root, source, symbols, parent_class=None)
        return symbols

    def _walk(
        self, node: Node, source: str, symbols: list[ParsedSymbol], parent_class: str | None
    ) -> None:
        if node.type == "function_item":
            name_node = node.child_by_field_name("name")
            name = self._node_text(name_node, source) if name_node else "<fn>"
            symbols.append(ParsedSymbol(
                kind="method" if parent_class else "function",
                name=name,
                start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                docstring=None, parent=parent_class,
            ))
        elif node.type in ("struct_item", "enum_item", "trait_item", "impl_item"):
            name_node = node.child_by_field_name("name")
            name = self._node_text(name_node, source) if name_node else "unknown"
            kind_label = node.type.replace("_item", "")
            symbols.append(ParsedSymbol(
                kind="class", name=f"{kind_label}:{name}",
                start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                docstring=None, parent=None,
            ))
            for child in node.children:
                self._walk(child, source, symbols, parent_class=name)
            return
        for child in node.children:
            self._walk(child, source, symbols, parent_class)

    def _extract_imports(self, root: Node, source: str) -> list[str]:
        return [
            self._node_text(child, source).strip()
            for child in root.children
            if child.type == "use_declaration"
        ]
