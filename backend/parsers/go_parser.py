import tree_sitter_go as tsgo
from tree_sitter import Language, Node

from backend.agents.state import ParsedSymbol
from backend.parsers.base import BaseParser


class GoParser(BaseParser):
    language_name = "go"
    extensions = frozenset({".go"})

    def _build_language(self) -> Language:
        return Language(tsgo.language())

    def _extract_symbols(self, root: Node, source: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        for node in root.children:
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, source) if name_node else "<func>"
                symbols.append(ParsedSymbol(
                    kind="function", name=name,
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    docstring=None, parent=None,
                ))
            elif node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                receiver = node.child_by_field_name("receiver")
                rec_text = self._node_text(receiver, source).strip("()") if receiver else None
                name = self._node_text(name_node, source) if name_node else "<method>"
                symbols.append(ParsedSymbol(
                    kind="method", name=name,
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    docstring=None, parent=rec_text,
                ))
            elif node.type == "type_declaration":
                for spec in node.children:
                    if spec.type == "type_spec":
                        name_node = spec.child_by_field_name("name")
                        type_node = spec.child_by_field_name("type")
                        if type_node and type_node.type == "struct_type":
                            name = self._node_text(name_node, source) if name_node else "unknown"
                            symbols.append(ParsedSymbol(
                                kind="class", name=f"struct:{name}",
                                start_line=spec.start_point[0] + 1, end_line=spec.end_point[0] + 1,
                                docstring=None, parent=None,
                            ))
        return symbols

    def _extract_imports(self, root: Node, source: str) -> list[str]:
        imports: list[str] = []
        for node in root.children:
            if node.type == "import_declaration":
                imports.append(self._node_text(node, source).strip())
        return imports
