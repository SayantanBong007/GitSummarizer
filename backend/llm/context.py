from __future__ import annotations

from backend.agents.state import ParsedFile

# ── Tunable limits ────────────────────────────────────────────────────────────
# Groq free tier: 12k TPM per request. Each agent sends (input + output) tokens.
# With 2k max_tokens output reserved, input budget = ~10k tokens ≈ 28k chars.
# We cap at 16k chars (~4k tokens) to leave a wide safety margin.
MAX_CHARS_PER_FILE = 800     # raw code chars sent per file
MAX_TOTAL_CHARS   = 6_000    # hard cap on total context sent to any agent
MAX_FILES         = 10       # max files included in context


def build_context(
    parsed_files: list[ParsedFile],
    *,
    keywords: set[str] | None = None,
    extensions: set[str] | None = None,
    max_files: int = MAX_FILES,
    max_chars_per_file: int = MAX_CHARS_PER_FILE,
    max_total_chars: int = MAX_TOTAL_CHARS,
) -> str:
    """
    Build a rich, symbol-aware context string from parsed files.

    Each file block contains:
      • path + language header
      • symbol summary  (classes / functions extracted by Tree-sitter)
      • import list
      • raw code snippet (up to max_chars_per_file)

    Files are ranked: exact extension match first, then keyword match in path,
    then all remaining files.
    """
    ranked = _rank_files(parsed_files, keywords=keywords, extensions=extensions)

    parts: list[str] = []
    total = 0

    for pf in ranked[:max_files]:
        block = _format_file(pf, max_chars_per_file)
        if total + len(block) > max_total_chars:
            # still include a stub so the LLM knows the file exists
            parts.append(f"### {pf['path']}\n[truncated — context limit reached]")
            break
        parts.append(block)
        total += len(block)

    return "\n\n---\n\n".join(parts)


def build_file_tree_summary(file_tree: dict, max_entries: int = 200) -> str:
    """Return the repository file tree as a compact text block."""
    lines = sorted(file_tree.keys())[:max_entries]
    return "\n".join(lines)


def build_symbol_index(parsed_files: list[ParsedFile], max_files: int = 80) -> str:
    """
    Return a compact symbol index: one line per file listing its classes/functions.
    Useful for architecture-level prompts that need breadth, not depth.
    """
    lines: list[str] = []
    for pf in parsed_files[:max_files]:
        symbols = pf.get("symbols", [])
        classes   = [s["name"] for s in symbols if s["kind"] == "class"]
        functions = [s["name"] for s in symbols if s["kind"] in ("function", "method")]
        parts: list[str] = []
        if classes:
            parts.append("classes: " + ", ".join(classes[:8]))
        if functions:
            parts.append("fns: " + ", ".join(functions[:10]))
        if parts:
            lines.append(f"{pf['path']}  →  {' | '.join(parts)}")
    return "\n".join(lines)


# ── Internals ─────────────────────────────────────────────────────────────────

def _rank_files(
    parsed_files: list[ParsedFile],
    *,
    keywords: set[str] | None,
    extensions: set[str] | None,
) -> list[ParsedFile]:
    """Sort files so the most relevant ones come first."""
    def score(pf: ParsedFile) -> int:
        path = pf["path"].lower()
        ext  = "." + path.rsplit(".", 1)[-1] if "." in path else ""
        s = 0
        if extensions and ext in extensions:
            s += 10
        if keywords:
            s += sum(2 for kw in keywords if kw in path)
        return s

    return sorted(parsed_files, key=score, reverse=True)


def _format_file(pf: ParsedFile, max_chars: int) -> str:
    """Format a single file into a rich context block."""
    path  = pf["path"]
    lang  = pf.get("language", "unknown")
    lines: list[str] = [f"### {path}  [{lang}]"]

    # Symbol summary
    symbols = pf.get("symbols", [])
    classes   = [s["name"] for s in symbols if s["kind"] == "class"]
    functions = [s["name"] for s in symbols if s["kind"] in ("function", "method")]
    if classes:
        lines.append("# Classes: " + ", ".join(classes[:12]))
    if functions:
        lines.append("# Functions: " + ", ".join(functions[:15]))

    # Imports (top 10)
    imports = pf.get("imports", [])[:10]
    if imports:
        lines.append("# Imports: " + " | ".join(imports))

    # Raw code (trimmed to budget)
    snippet = pf.get("raw_snippet", "")[:max_chars]
    if snippet:
        lines.append(snippet)

    return "\n".join(lines)
