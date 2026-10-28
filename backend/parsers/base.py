from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from tree_sitter import Language, Node, Parser

from backend.agents.state import ParsedFile, ParsedSymbol
from backend.core.logging import get_logger

logger = get_logger(__name__)

SNIPPET_LINES = 400


class BaseParser(ABC):
    """Abstract base for Tree-sitter language parsers."""

    language_name: str
    extensions: frozenset[str]

    def __init__(self) -> None:
        self._parser = Parser(self._build_language())

    @abstractmethod
    def _build_language(self) -> Language:
        """Return the Tree-sitter Language for this parser."""

    def parse_file(self, file_path: Path) -> ParsedFile | None:
        try:
            code_bytes = file_path.read_bytes()
            tree = self._parser.parse(code_bytes)
            code_str = code_bytes.decode("utf-8", errors="replace")
            symbols = self._extract_symbols(tree.root_node, code_str)
            imports = self._extract_imports(tree.root_node, code_str)
            lines = code_str.splitlines()
            snippet = "\n".join(lines[:SNIPPET_LINES])

            return ParsedFile(
                path=str(file_path),
                language=self.language_name,
                size_bytes=len(code_bytes),
                symbols=symbols,
                imports=imports,
                raw_snippet=snippet,
            )
        except Exception as exc:
            logger.warning("parse_error", path=str(file_path), error=str(exc))
            return None

    @abstractmethod
    def _extract_symbols(self, root: Node, source: str) -> list[ParsedSymbol]:
        """Extract functions, classes, methods from the AST."""

    @abstractmethod
    def _extract_imports(self, root: Node, source: str) -> list[str]:
        """Extract import statements from the AST."""

    def _node_text(self, node: Node, source: str) -> str:
        return source[node.start_byte:node.end_byte]

    def _get_docstring(self, node: Node, source: str) -> str | None:
        """Attempt to extract a docstring from the first child string node."""
        for child in node.children:
            if child.type in ("string", "expression_statement"):
                for sub in child.children:
                    if sub.type == "string":
                        raw = self._node_text(sub, source).strip("'\"` \n")
                        if raw:
                            return raw[:300]
                text = self._node_text(child, source).strip()
                if text.startswith(('"""', "'''", '"', "'")):
                    return text.strip("'\"` \n")[:300]
        return None

    @classmethod
    def supports(cls, extension: str) -> bool:
        return extension.lower() in cls.extensions
