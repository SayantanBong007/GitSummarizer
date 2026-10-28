import tree_sitter_typescript as tsts
from tree_sitter import Language, Node

from backend.agents.state import ParsedSymbol
from backend.parsers.base import BaseParser


class TypeScriptParser(BaseParser):
    language_name = "typescript"
    extensions = frozenset({".ts", ".tsx"})

    def _build_language(self) -> Language:
        return Language(tsts.language_typescript())

    def _extract_symbols(self, root: Node, source: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(root, source, symbols, parent_class=None)
        return symbols

    def _walk(
        self, node: Node, source: str, symbols: list[ParsedSymbol], parent_class: str | None
    ) -> None:
        if node.type in ("function_declaration", "function"):
            name_node = node.child_by_field_name("name")
            name = self._node_text(name_node, source) if name_node else "<anonymous>"
            symbols.append(ParsedSymbol(
                kind="method" if parent_class else "function",
                name=name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                docstring=None,
                parent=parent_class,
            ))
            for child in node.children:
                self._walk(child, source, symbols, parent_class)

        elif node.type in ("class_declaration", "abstract_class_declaration"):
            name_node = node.child_by_field_name("name")
            class_name = self._node_text(name_node, source) if name_node else "unknown"
            symbols.append(ParsedSymbol(
                kind="class",
                name=class_name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                docstring=None,
                parent=None,
            ))
            for child in node.children:
                self._walk(child, source, symbols, parent_class=class_name)

        elif node.type == "method_definition":
            name_node = node.child_by_field_name("name")
            name = self._node_text(name_node, source) if name_node else "<method>"
            symbols.append(ParsedSymbol(
                kind="method",
                name=name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                docstring=None,
                parent=parent_class,
            ))
        elif node.type in ("arrow_function", "lexical_declaration"):
            for child in node.children:
                self._walk(child, source, symbols, parent_class)
        else:
            for child in node.children:
                self._walk(child, source, symbols, parent_class)

    def _extract_imports(self, root: Node, source: str) -> list[str]:
        imports: list[str] = []
        for node in root.children:
            if node.type == "import_statement":
                imports.append(self._node_text(node, source).strip())
        return imports


class JavaScriptParser(BaseParser):
    language_name = "javascript"
    extensions = frozenset({".js", ".jsx", ".mjs", ".cjs"})

    def _build_language(self) -> Language:
        import tree_sitter_javascript as tsjs
        return Language(tsjs.language())

    def _extract_symbols(self, root: Node, source: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(root, source, symbols, parent_class=None)
        return symbols

    def _walk(
        self, node: Node, source: str, symbols: list[ParsedSymbol], parent_class: str | None
    ) -> None:
        if node.type in ("function_declaration", "function_expression", "arrow_function"):
            name_node = node.child_by_field_name("name")
            name = self._node_text(name_node, source) if name_node else "<anonymous>"
            symbols.append(ParsedSymbol(
                kind="method" if parent_class else "function",
                name=name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                docstring=None,
                parent=parent_class,
            ))
        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            class_name = self._node_text(name_node, source) if name_node else "unknown"
            symbols.append(ParsedSymbol(
                kind="class",
                name=class_name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                docstring=None,
                parent=None,
            ))
            for child in node.children:
                self._walk(child, source, symbols, parent_class=class_name)
            return
        for child in node.children:
            self._walk(child, source, symbols, parent_class)

    def _extract_imports(self, root: Node, source: str) -> list[str]:
        imports: list[str] = []
        for node in root.children:
            if node.type == "import_statement":
                imports.append(self._node_text(node, source).strip())
        return imports
