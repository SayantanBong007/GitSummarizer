import tree_sitter_python as tspython
from tree_sitter import Language, Node

from backend.agents.state import ParsedSymbol
from backend.parsers.base import BaseParser


class PythonParser(BaseParser):
    language_name = "python"
    extensions = frozenset({".py", ".pyw"})

    def _build_language(self) -> Language:
        return Language(tspython.language())

    def _extract_symbols(self, root: Node, source: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(root, source, symbols, parent_class=None)
        return symbols

    def _walk(
        self,
        node: Node,
        source: str,
        symbols: list[ParsedSymbol],
        parent_class: str | None,
    ) -> None:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            name = self._node_text(name_node, source) if name_node else "unknown"
            kind = "method" if parent_class else "function"
            symbols.append(
                ParsedSymbol(
                    kind=kind,
                    name=name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    docstring=self._get_docstring(node, source),
                    parent=parent_class,
                )
            )
            for child in node.children:
                self._walk(child, source, symbols, parent_class)

        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            class_name = self._node_text(name_node, source) if name_node else "unknown"
            symbols.append(
                ParsedSymbol(
                    kind="class",
                    name=class_name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    docstring=self._get_docstring(node, source),
                    parent=None,
                )
            )
            for child in node.children:
                self._walk(child, source, symbols, parent_class=class_name)
        else:
            for child in node.children:
                self._walk(child, source, symbols, parent_class)

    def _extract_imports(self, root: Node, source: str) -> list[str]:
        imports: list[str] = []
        for node in root.children:
            if node.type == "import_statement" or node.type == "import_from_statement":
                imports.append(self._node_text(node, source).strip())
        return imports
