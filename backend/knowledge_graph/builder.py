from __future__ import annotations

import hashlib
import re
from pathlib import Path

from backend.agents.state import ParsedFile
from backend.core.logging import get_logger
from backend.database.neo4j import run_query
from backend.knowledge_graph import queries
from backend.knowledge_graph.models import (
    GraphEdge,
    GraphNode,
    NodeType,
    RelationshipType,
)

logger = get_logger(__name__)

# Whitelist of safe relationship type values to prevent injection
_SAFE_REL_TYPES: frozenset[str] = frozenset(r.value for r in RelationshipType)


def _make_id(*parts: str) -> str:
    return hashlib.md5(":".join(parts).encode()).hexdigest()[:16]


class KnowledgeGraphBuilder:
    def __init__(self, repo_id: str) -> None:
        self.repo_id = repo_id
        self._nodes: list[GraphNode] = []
        self._edges: list[GraphEdge] = []

    def build_from_parsed_files(self, parsed_files: list[ParsedFile]) -> None:
        file_id_map: dict[str, str] = {}

        for pf in parsed_files:
            file_id = _make_id(self.repo_id, pf["path"])
            file_id_map[pf["path"]] = file_id
            self._nodes.append(GraphNode(
                id=file_id,
                type=NodeType.FILE,
                name=pf["path"].split("/")[-1],
                repo_id=self.repo_id,
                file_path=pf["path"],
                language=pf["language"],
                metadata={"size_bytes": pf["size_bytes"]},
            ))

            for sym in pf["symbols"]:
                sym_id = _make_id(self.repo_id, pf["path"], sym["name"], str(sym["start_line"]))

                if sym["kind"] == "class":
                    node_type = NodeType.CLASS
                elif sym["kind"] in ("function", "method"):
                    node_type = NodeType.FUNCTION
                else:
                    # variable / import / other — skip
                    continue

                self._nodes.append(GraphNode(
                    id=sym_id,
                    type=node_type,
                    name=sym["name"],
                    repo_id=self.repo_id,
                    file_path=pf["path"],
                    start_line=sym["start_line"],
                    end_line=sym["end_line"],
                ))
                self._edges.append(GraphEdge(
                    source_id=file_id,
                    target_id=sym_id,
                    relationship=RelationshipType.DEFINES,
                ))

                # Detect API endpoints heuristically from function names / decorators
                if self._looks_like_endpoint(sym["name"], pf["language"]):
                    ep_id = _make_id(self.repo_id, pf["path"], sym["name"], "endpoint")
                    self._nodes.append(GraphNode(
                        id=ep_id,
                        type=NodeType.API_ENDPOINT,
                        name=sym["name"],
                        repo_id=self.repo_id,
                        file_path=pf["path"],
                        start_line=sym["start_line"],
                        end_line=sym["end_line"],
                    ))
                    self._edges.append(GraphEdge(
                        source_id=sym_id,
                        target_id=ep_id,
                        relationship=RelationshipType.DEFINES,
                    ))

        # Build IMPORTS edges with per-language resolvers
        for pf in parsed_files:
            src_id = file_id_map.get(pf["path"])
            if not src_id:
                continue
            for imp in pf["imports"]:
                resolved = self._resolve_import(imp, pf["path"], pf["language"], file_id_map)
                if resolved:
                    self._edges.append(GraphEdge(
                        source_id=src_id,
                        target_id=resolved,
                        relationship=RelationshipType.IMPORTS,
                    ))

    # -------------------------------------------------------------------------
    # Import resolution — per-language
    # -------------------------------------------------------------------------

    def _resolve_import(
        self,
        import_str: str,
        current_file: str,
        language: str,
        file_id_map: dict[str, str],
    ) -> str | None:
        """Try to resolve an import string to a file node id.

        Handles:
          Python  — 'import X', 'from X import Y', relative 'from .X import Y'
          TS/JS   — 'import ... from "path"', 'require("path")'
          Java    — 'import com.example.Foo;'
          Go      — 'import "pkg/path"'
          Rust    — 'use crate::module;'
        """
        candidates = self._get_candidates(import_str, current_file, language)
        for candidate in candidates:
            if candidate in file_id_map:
                return file_id_map[candidate]
        return None

    def _get_candidates(
        self,
        import_str: str,
        current_file: str,
        language: str,
    ) -> list[str]:
        s = import_str.strip()
        current_dir = "/".join(current_file.split("/")[:-1])

        if language == "python":
            return self._python_candidates(s, current_dir)
        elif language in ("typescript", "javascript"):
            return self._ts_candidates(s, current_dir)
        elif language == "java":
            return self._java_candidates(s)
        elif language == "go":
            return self._go_candidates(s)
        elif language == "rust":
            return self._rust_candidates(s, current_dir)
        return []

    def _python_candidates(self, s: str, current_dir: str) -> list[str]:
        """Handle all Python import forms."""
        candidates: list[str] = []

        # Relative: 'from .foo import bar' or 'from ..foo import bar'
        rel_match = re.match(r"from\s+(\.+)([^\s]*)\s+import", s)
        if rel_match:
            dots, module_path = rel_match.group(1), rel_match.group(2)
            # Navigate up one directory per extra dot
            base = current_dir
            up_count = len(dots) - 1
            for _ in range(up_count):
                base = "/".join(base.split("/")[:-1]) if "/" in base else ""
            if module_path:
                mod_as_path = module_path.replace(".", "/")
                candidates.append(f"{base}/{mod_as_path}.py".lstrip("/"))
                candidates.append(f"{base}/{mod_as_path}/__init__.py".lstrip("/"))
            else:
                candidates.append(f"{base}/__init__.py".lstrip("/"))
            return candidates

        # Absolute: 'from X.Y.Z import something'
        abs_match = re.match(r"from\s+([^\s]+)\s+import", s)
        if abs_match:
            module = abs_match.group(1)
            mod_as_path = module.replace(".", "/")
            candidates.append(f"{mod_as_path}.py")
            candidates.append(f"{mod_as_path}/__init__.py")
            # Also try relative to current dir
            candidates.append(f"{current_dir}/{mod_as_path}.py".lstrip("/"))

        # Plain import: 'import X' or 'import X as Y'
        plain_match = re.match(r"import\s+([^\s,]+)", s)
        if plain_match:
            module = plain_match.group(1).rstrip(";").split(" as ")[0]
            mod_as_path = module.replace(".", "/")
            candidates.append(f"{mod_as_path}.py")
            candidates.append(f"{mod_as_path}/__init__.py")
            candidates.append(f"{current_dir}/{mod_as_path}.py".lstrip("/"))

        return candidates

    def _ts_candidates(self, s: str, current_dir: str) -> list[str]:
        """Handle TS/JS import statements."""
        candidates: list[str] = []

        # Match: import ... from "path" or import ... from 'path'
        match = re.search(r"""from\s+['"]([^'"]+)['"]""", s)
        if not match:
            # require("path")
            match = re.search(r"""require\(['"]([^'"]+)['"]\)""", s)
        if not match:
            return []

        path = match.group(1)

        if path.startswith("."):
            # Relative import
            base = f"{current_dir}/{path}".replace("//", "/").lstrip("/")
            # Try exact, then with extensions, then as directory index
            for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs"):
                candidates.append(f"{base}{ext}")
            candidates.append(f"{base}/index.ts")
            candidates.append(f"{base}/index.tsx")
            candidates.append(f"{base}/index.js")
        # Absolute/node_modules — can't resolve to repo files, skip

        return candidates

    def _java_candidates(self, s: str) -> list[str]:
        """Handle 'import com.example.Foo;' → try com/example/Foo.java"""
        match = re.match(r"import\s+(static\s+)?([^;*\s]+)", s)
        if not match:
            return []
        fqn = match.group(2)
        # Strip trailing class wildcard
        fqn = re.sub(r"\.[A-Z][^.]*$", "", fqn)
        as_path = fqn.replace(".", "/")
        return [f"{as_path}.java", f"src/main/java/{as_path}.java"]

    def _go_candidates(self, s: str) -> list[str]:
        """Handle 'import "github.com/user/repo/pkg/foo"' → try pkg/foo/*.go"""
        candidates: list[str] = []
        # Multi-import block: not handled per-line (parsers emit raw text)
        matches = re.findall(r'"([^"]+)"', s)
        for pkg in matches:
            # Strip known module prefix heuristically (last 2 segments)
            parts = pkg.split("/")
            for depth in range(min(3, len(parts))):
                sub = "/".join(parts[depth:])
                candidates.append(f"{sub}/__init__.go")
                candidates.append(f"{sub}/main.go")
                # Try matching any .go file in that dir
                candidates.append(f"{sub}.go")
        return candidates

    def _rust_candidates(self, s: str, current_dir: str) -> list[str]:
        """Handle 'use crate::module::item;' → try module.rs or module/mod.rs"""
        candidates: list[str] = []
        match = re.match(r"use\s+(?:crate|self|super)::([^;{]+)", s)
        if match:
            path = match.group(1).split("::")[0].strip()
            candidates.append(f"{path}.rs")
            candidates.append(f"src/{path}.rs")
            candidates.append(f"{current_dir}/{path}.rs".lstrip("/"))
            candidates.append(f"{path}/mod.rs")
        return candidates

    # -------------------------------------------------------------------------
    # Heuristic endpoint detection
    # -------------------------------------------------------------------------

    # Route handler name patterns used by common frameworks
    _ENDPOINT_PATTERNS = re.compile(
        r"^(get|post|put|patch|delete|create|update|list|retrieve|destroy|"
        r"handle|route|endpoint|view|controller|action|resolve)_?",
        re.IGNORECASE,
    )
    _ENDPOINT_SUFFIXES = re.compile(
        r"(Handler|Controller|Route|Endpoint|View|Action|Resolver)$"
    )

    def _looks_like_endpoint(self, name: str, language: str) -> bool:
        return bool(
            self._ENDPOINT_PATTERNS.match(name) or
            self._ENDPOINT_SUFFIXES.search(name)
        )

    # -------------------------------------------------------------------------
    # Serialization / persistence
    # -------------------------------------------------------------------------

    def to_state_dict(self) -> dict:
        return {
            "nodes": [n.model_dump() for n in self._nodes],
            "edges": [e.model_dump() for e in self._edges],
        }

    async def persist_to_neo4j(self) -> None:
        for node in self._nodes:
            if node.type == NodeType.FILE:
                await run_query(queries.CREATE_FILE_NODE, {
                    "id": node.id, "path": node.file_path, "repo_id": node.repo_id,
                    "language": node.language, "size_bytes": node.metadata.get("size_bytes", 0),
                })
            elif node.type == NodeType.FUNCTION:
                await run_query(queries.CREATE_FUNCTION_NODE, {
                    "id": node.id, "name": node.name, "repo_id": node.repo_id,
                    "file_path": node.file_path,
                    "start_line": node.start_line, "end_line": node.end_line,
                })
            elif node.type == NodeType.CLASS:
                await run_query(queries.CREATE_CLASS_NODE, {
                    "id": node.id, "name": node.name, "repo_id": node.repo_id,
                    "file_path": node.file_path,
                    "start_line": node.start_line, "end_line": node.end_line,
                })
            elif node.type == NodeType.API_ENDPOINT:
                await run_query(queries.CREATE_ENDPOINT_NODE, {
                    "id": node.id, "name": node.name, "repo_id": node.repo_id,
                    "file_path": node.file_path,
                    "start_line": node.start_line, "end_line": node.end_line,
                })

        for edge in self._edges:
            rel_type = edge.relationship.value
            if rel_type not in _SAFE_REL_TYPES:
                logger.warning("neo4j_unsafe_rel_type", rel_type=rel_type)
                continue
            cypher = queries.CREATE_RELATIONSHIP.replace("{rel_type}", rel_type)
            try:
                await run_query(cypher, {
                    "source_id": edge.source_id, "target_id": edge.target_id
                })
            except Exception as exc:
                logger.warning("neo4j_edge_error", error=str(exc))

        logger.info(
            "knowledge_graph_persisted",
            repo_id=self.repo_id,
            nodes=len(self._nodes),
            edges=len(self._edges),
        )
