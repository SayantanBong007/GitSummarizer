from __future__ import annotations

import json
import re
import textwrap

from backend.core.logging import get_logger
from backend.models.db.analysis import Analysis

logger = get_logger(__name__)

# FPDF built-in fonts are Latin-1 only — map common Unicode to ASCII equivalents
_CHAR_MAP = str.maketrans({
    "•": "-",   # bullet •
    "—": "--",  # em dash —
    "–": "-",   # en dash –
    "…": "...", # ellipsis …
    "·": "-",   # middle dot ·
    "’": "'",   # right single quote '
    "‘": "'",   # left single quote '
    "“": '"',   # left double quote "
    "”": '"',   # right double quote "
    "‑": "-",   # non-breaking hyphen
    "‒": "-",   # figure dash
    "â": "a",   # â
    "é": "e",   # é
    "è": "e",   # è
    "ê": "e",   # ê
    "ï": "i",   # ï
    "ô": "o",   # ô
    "û": "u",   # û
})

_INDIGO = (99,  102, 241)
_DARK   = (30,   30,  46)
_GRAY   = (110, 110, 130)
_WHITE  = (255, 255, 255)
_LIGHT  = (245, 246, 250)
_RISK   = {
    "critical": (220,  53,  69),
    "high":     (253, 126,  20),
    "medium":   (200, 150,   0),
    "low":      ( 40, 167,  69),
    "unknown":  (150, 150, 150),
}


def _s(text: str) -> str:
    """Coerce text to Latin-1 safe string."""
    return text.translate(_CHAR_MAP).encode("latin-1", errors="replace").decode("latin-1")


def export_to_json(analysis: Analysis) -> str:
    data = {
        "id":                analysis.id,
        "repository_id":     analysis.repository_id,
        "status":            analysis.status,
        "executive_summary": analysis.executive_summary,
        "tech_stack":        analysis.tech_stack,
        "architecture":      analysis.architecture_report,
        "api":               analysis.api_report,
        "database":          analysis.database_report,
        "security":          analysis.security_report,
        "diagrams":          analysis.diagrams,
        "design_patterns":   analysis.design_patterns,
        "generated_at":      analysis.updated_at.isoformat(),
    }
    return json.dumps(data, indent=2, default=str)


def export_to_markdown(analysis: Analysis) -> dict[str, str]:
    docs = dict(analysis.markdown_docs or {})
    if analysis.executive_summary:
        docs["executive_summary.md"] = analysis.executive_summary
    return docs


async def export_to_pdf(analysis: Analysis) -> bytes:
    try:
        from fpdf import FPDF
    except ImportError as err:
        raise RuntimeError("fpdf2 not installed") from err

    class _PDF(FPDF):
        def footer(self) -> None:
            self.set_y(-12)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(*_GRAY)
            self.cell(
                0, 5,
                _s(f"GitSummarize  |  Page {self.page_no()}"),
                align="C",
            )

    FPDF = _PDF  # shadow the name so the rest of the function uses it

    # ── Build ordered content from markdown docs ──────────────────────────────
    # Documentation agent writes rich narrative markdown — use that as the
    # content source, the same way the original WeasyPrint flow did.
    sections: list[tuple[str, str]] = []
    docs = dict(analysis.markdown_docs or {})
    # executive_summary lives on a separate column — inject it as the first doc
    if analysis.executive_summary:
        docs.setdefault("executive_summary.md", analysis.executive_summary)

    # Preferred order
    _ORDER = [
        "executive_summary.md",
        "architecture.md",
        "api.md",
        "database.md",
        "security.md",
        "onboarding.md",
    ]
    for key in _ORDER:
        if key in docs:
            sections.append((key, docs[key]))
    # Catch any extra docs not in the ordered list
    for key, content in docs.items():
        if key not in _ORDER:
            sections.append((key, content))

    # Fall back to executive summary field if no docs
    if not sections and analysis.executive_summary:
        sections.append(("executive_summary.md", analysis.executive_summary))

    # ── PDF setup ─────────────────────────────────────────────────────────────
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    LM = 20    # left margin
    W  = 170   # usable width

    # ── Cover page ────────────────────────────────────────────────────────────
    repo_name = ""
    ts = analysis.tech_stack or {}
    langs = ts.get("languages") or []
    fws   = ts.get("frameworks") or []

    # Try to get repo name from executive summary first line
    if analysis.executive_summary:
        first = analysis.executive_summary.strip().splitlines()[0]
        repo_name = re.sub(r"^#+\s*", "", first)[:60]

    pdf.set_fill_color(*_INDIGO)
    pdf.set_text_color(*_WHITE)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(W, 14, _s("GitSummarize Analysis Report"), new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)

    if repo_name:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*_DARK)
        pdf.cell(W, 8, _s(repo_name), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_GRAY)
    pdf.cell(W, 5, _s(f"Generated: {analysis.updated_at.strftime('%Y-%m-%d %H:%M UTC')}"),
             new_x="LMARGIN", new_y="NEXT")

    if langs:
        lang_str = ", ".join(str(l) for l in (langs if isinstance(langs, list) else [langs])[:6])
        pdf.cell(W, 5, _s(f"Languages: {lang_str}"), new_x="LMARGIN", new_y="NEXT")
    if fws:
        fw_str = ", ".join(str(f) for f in (fws if isinstance(fws, list) else [fws])[:8])
        pdf.cell(W, 5, _s(f"Frameworks: {fw_str}"), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    _rule(pdf, W)

    # ── Render each markdown section ──────────────────────────────────────────
    for _filename, md_content in sections:
        _render_markdown(pdf, md_content, W, LM)
        _rule(pdf, W)

    pdf_bytes = bytes(pdf.output())
    logger.info("pdf_exported", analysis_id=analysis.id, size_bytes=len(pdf_bytes))
    return pdf_bytes


# ── Markdown renderer ─────────────────────────────────────────────────────────

def _rule(pdf: "FPDF", W: int) -> None:
    pdf.set_draw_color(210, 210, 225)
    pdf.line(20, pdf.get_y(), 20 + W, pdf.get_y())
    pdf.ln(4)


def _render_markdown(pdf: "FPDF", md: str, W: int, LM: int) -> None:
    """
    Minimal markdown renderer for fpdf2 using Latin-1 fonts.
    Handles: # headings, **bold**, bullet lists (- / *),
    code fences (```), horizontal rules (---), plain paragraphs.
    """
    lines = md.splitlines()
    i = 0
    in_code_block = False
    code_buf: list[str] = []

    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        # ── Code fence ───────────────────────────────────────────────────────
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_buf = []
            else:
                in_code_block = False
                _render_code_block(pdf, code_buf, W, LM)
                code_buf = []
            i += 1
            continue

        if in_code_block:
            code_buf.append(raw)
            i += 1
            continue

        # ── Horizontal rule ──────────────────────────────────────────────────
        if re.match(r"^[-*_]{3,}$", stripped):
            pdf.ln(2)
            _rule(pdf, W)
            i += 1
            continue

        # ── Headings ─────────────────────────────────────────────────────────
        h_match = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if h_match:
            level = len(h_match.group(1))
            text  = _strip_inline(h_match.group(2))
            _render_heading(pdf, text, level, W, LM)
            i += 1
            continue

        # ── Bullet list ───────────────────────────────────────────────────────
        if re.match(r"^[-*+]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            # Collect consecutive list items
            items: list[str] = []
            while i < len(lines):
                l = lines[i].strip()
                m = re.match(r"^[-*+]\s+(.*)", l) or re.match(r"^\d+\.\s+(.*)", l)
                if m:
                    items.append(_strip_inline(m.group(1)))
                    i += 1
                elif l == "":
                    i += 1
                    break
                else:
                    break
            _render_bullets(pdf, items, W, LM)
            continue

        # ── Table (pipe-delimited) ────────────────────────────────────────────
        if "|" in stripped and stripped.startswith("|"):
            table_rows: list[list[str]] = []
            while i < len(lines):
                l = lines[i].strip()
                if not l or not "|" in l:
                    break
                if re.match(r"^\|[-| :]+\|$", l):
                    i += 1
                    continue
                cells = [c.strip() for c in l.strip("|").split("|")]
                table_rows.append(cells)
                i += 1
            if table_rows:
                _render_table(pdf, table_rows, W, LM)
            continue

        # ── Blank line ────────────────────────────────────────────────────────
        if stripped == "":
            pdf.ln(2)
            i += 1
            continue

        # ── Plain paragraph ───────────────────────────────────────────────────
        # Collect lines until blank/heading/bullet/rule
        para_lines: list[str] = []
        while i < len(lines):
            l = lines[i].strip()
            if (l == ""
                    or l.startswith("#")
                    or re.match(r"^[-*+]\s+", l)
                    or re.match(r"^\d+\.\s+", l)
                    or re.match(r"^[-*_]{3,}$", l)
                    or l.startswith("```")
                    or ("|" in l and l.startswith("|"))):
                break
            para_lines.append(l)
            i += 1
        text = " ".join(para_lines)
        _render_paragraph(pdf, text, W, LM)


def _strip_inline(text: str) -> str:
    """Remove bold/italic markdown markers, leaving plain text."""
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # links
    return text.strip()


def _render_heading(pdf: "FPDF", text: str, level: int, W: int, LM: int) -> None:
    sizes    = {1: 16, 2: 13, 3: 11, 4: 10}
    size     = sizes.get(level, 10)
    pdf.ln(3)
    if level == 1:
        pdf.set_fill_color(*_INDIGO)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", "B", size)
        pdf.set_x(LM)
        pdf.cell(W, 9, _s(text[:100]), new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(2)
    elif level == 2:
        pdf.set_text_color(*_DARK)
        pdf.set_font("Helvetica", "B", size)
        pdf.set_x(LM)
        pdf.cell(W, 7, _s(text[:100]), new_x="LMARGIN", new_y="NEXT")
        # underline
        y = pdf.get_y()
        pdf.set_draw_color(*_INDIGO)
        pdf.line(LM, y, LM + W, y)
        pdf.ln(3)
    elif level == 3:
        pdf.set_text_color(*_INDIGO)
        pdf.set_font("Helvetica", "B", size)
        pdf.set_x(LM)
        pdf.cell(W, 6, _s(text[:100]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    else:
        pdf.set_text_color(*_GRAY)
        pdf.set_font("Helvetica", "B", size)
        pdf.set_x(LM)
        pdf.cell(W, 5, _s(text[:100]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_DARK)


def _render_paragraph(pdf: "FPDF", text: str, W: int, LM: int) -> None:
    if not text.strip():
        return
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_DARK)
    clean = _s(_strip_inline(text))
    for chunk in textwrap.wrap(clean, width=95) or [" "]:
        pdf.set_x(LM)
        pdf.multi_cell(W, 5, chunk)
    pdf.ln(1)


def _render_bullets(pdf: "FPDF", items: list[str], W: int, LM: int) -> None:
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_DARK)
    indent = 6
    for item in items:
        clean = _s(item)
        wrapped = textwrap.wrap(clean, width=88) or [" "]
        for j, chunk in enumerate(wrapped):
            pdf.set_x(LM + indent)
            if j == 0:
                pdf.cell(4, 5, "-", new_x="RIGHT")
                pdf.multi_cell(W - indent - 4, 5, chunk)
            else:
                pdf.cell(4, 5, " ", new_x="RIGHT")
                pdf.multi_cell(W - indent - 4, 5, chunk)
    pdf.ln(1)


def _render_code_block(pdf: "FPDF", lines: list[str], W: int, LM: int) -> None:
    if not lines:
        return
    pdf.set_fill_color(*_LIGHT)
    pdf.set_draw_color(210, 210, 225)
    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(60, 60, 80)
    pdf.ln(1)
    for line in lines[:40]:
        clean = _s(line)
        # Wrap long lines
        for chunk in (textwrap.wrap(clean, width=110) if len(clean) > 110 else [clean or " "]):
            pdf.set_x(LM + 3)
            pdf.multi_cell(W - 6, 4.5, chunk, fill=True)
    pdf.set_text_color(*_DARK)
    pdf.ln(2)


def _render_table(pdf: "FPDF", rows: list[list[str]], W: int, LM: int) -> None:
    if not rows:
        return
    pdf.set_font("Helvetica", "", 8)
    n_cols = max(len(r) for r in rows)
    col_w  = W / n_cols

    for r_idx, row in enumerate(rows[:30]):
        is_header = r_idx == 0
        if is_header:
            pdf.set_fill_color(*_LIGHT)
            pdf.set_font("Helvetica", "B", 8)
        else:
            pdf.set_fill_color(*_WHITE)
            pdf.set_font("Helvetica", "", 8)

        pdf.set_x(LM)
        for c_idx, cell in enumerate(row[:n_cols]):
            text = _s(_strip_inline(cell))[:40]
            pdf.cell(col_w, 5, text, border=1, fill=is_header, new_x="RIGHT")
        # fill missing columns
        for _ in range(n_cols - len(row)):
            pdf.cell(col_w, 5, "", border=1, new_x="RIGHT")
        pdf.ln()

    pdf.ln(2)
