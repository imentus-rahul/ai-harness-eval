#!/usr/bin/env python3
"""Build harness-eval.pptx from committed output/ example runs.

Every result number on the slides is read from output/<example>/ JSON so the
deck cannot drift from the evidence on disk. Run after `python3 -m eval --dry-run`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

GOOD_DIR = "good-harness-example"
BAD_DIR = "bad-harness-example"

# ---------------------------------------------------------------- palette
INK = "0F172A"
INK2 = "334155"
MUTED = "64748B"
LINE = "E2E8F0"
WHITE = "FFFFFF"
SOFT = "F1F5F9"
TEAL = "0F766E"
TEAL_L = "CCFBF1"
GREEN = "047857"
GREEN_L = "D1FAE5"
RED = "B91C1C"
RED_L = "FEE2E2"
AMBER = "B45309"
AMBER_L = "FEF3C7"
VIOLET = "6D28D9"
VIOLET_L = "EDE9FE"
BLUE = "1D4ED8"
BLUE_L = "DBEAFE"
DARK = "0B1220"
DARK2 = "16213A"
MINT = "5EEAD4"
CODE_BG = "0F172A"
CODE_FG = "E2E8F0"
CODE_DIM = "94A3B8"

FONT = "Calibri"
MONO = "Courier New"

W = 13.333
H = 7.5


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_)


# ---------------------------------------------------------------- evidence
class Evidence:
    """Facts read from output/ so slides match summary.json on disk."""

    def __init__(self, project: Path) -> None:
        out = project / "output"
        self.good = load_json(out / GOOD_DIR / "summary.json")
        self.bad = load_json(out / BAD_DIR / "summary.json")
        self.cmp = {
            ("good", 1): load_json(out / GOOD_DIR / "phase-1" / "comparison" / "result.json"),
            ("good", 2): load_json(out / GOOD_DIR / "phase-2" / "comparison" / "result.json"),
            ("bad", 1): load_json(out / BAD_DIR / "phase-1" / "comparison" / "result.json"),
        }
        self.out = out

    def row(self, scen: str, phase: int, task: str) -> dict:
        for c in (self.cmp.get((scen, phase)) or {}).get("comparisons") or []:
            if c["task_id"] == task:
                return c
        return {}

    def grade(self, scen: str, phase: int, arm: str, task: str, rep: int = 0) -> dict:
        ex = GOOD_DIR if scen == "good" else BAD_DIR
        return load_json(
            self.out / ex / f"phase-{phase}" / arm / "trials" / task / str(rep) / "grade.json"
        )

    def findings(self, scen: str, phase: int, arm: str, task: str) -> list[dict]:
        ex = GOOD_DIR if scen == "good" else BAD_DIR
        data = load_json(
            self.out / ex / f"phase-{phase}" / arm / "trials" / task / "0" / "result" / "findings.json"
        )
        return data.get("findings") or []

    @staticmethod
    def reps(passes: list[bool]) -> str:
        return " · ".join("PASS" if p else "FAIL" for p in passes) or "n/a"


# ---------------------------------------------------------------- primitives
def add_runs(paragraph, text: str, size: float, color: str, bold: bool = False,
             mono_color: str | None = None, font: str = FONT) -> None:
    """Write text with **bold** and `code` markup (code may nest inside bold)."""
    for chunk in re.split(r"(\*\*.+?\*\*)", text):
        if not chunk:
            continue
        is_bold = chunk.startswith("**") and chunk.endswith("**") and len(chunk) > 4
        inner = chunk[2:-2] if is_bold else chunk
        for part in re.split(r"(`.+?`)", inner):
            if not part:
                continue
            is_code = part.startswith("`") and part.endswith("`") and len(part) > 2
            run = paragraph.add_run()
            run.text = part[1:-1] if is_code else part
            f = run.font
            f.size = Pt(size)
            f.bold = bold or is_bold
            f.name = MONO if is_code else font
            f.color.rgb = rgb(mono_color if (is_code and mono_color) else color)


def _bullet(paragraph, color: str, char: str = "•") -> None:
    pPr = paragraph._p.get_or_add_pPr()
    pPr.set("marL", str(Emu(Inches(0.22))))
    pPr.set("indent", str(-Emu(Inches(0.2))))
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum", "a:buClr", "a:buFont"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    clr = pPr.makeelement(qn("a:buClr"), {})
    srgb = clr.makeelement(qn("a:srgbClr"), {"val": color})
    clr.append(srgb)
    pPr.append(clr)
    bu = pPr.makeelement(qn("a:buChar"), {"char": char})
    pPr.append(bu)


def text(slide, x, y, w, h, content, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, bullets=False, bullet_color=TEAL, space_after=4,
         line_spacing=1.05, font=FONT, mono_color=None, margin=0.0):
    """Text box. `content` is a string or list of strings (one paragraph each)."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, Inches(margin))
    items = content if isinstance(content, list) else [content]
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after)
        add_runs(p, item, size, color, bold=bold, mono_color=mono_color, font=font)
        if bullets:
            _bullet(p, bullet_color)
    return box


def box(slide, x, y, w, h, fill=WHITE, line=LINE, radius=0.08, shape=MSO_SHAPE.ROUNDED_RECTANGLE,
        line_w=1.0, dash=False):
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = radius
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(line_w)
        if dash:
            shp.line.dash_style = 4  # dash
    shp.shadow.inherit = False
    shp.text_frame.text = ""
    return shp


def label_in(shp, content, size=13, color=INK, bold=False, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE, margin=0.08, font=FONT, bullets=False, bullet_color=TEAL,
             space_after=2, mono_color=None):
    tf = shp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right"):
        setattr(tf, side, Inches(margin))
    tf.margin_top = Inches(0.04)
    tf.margin_bottom = Inches(0.04)
    items = content if isinstance(content, list) else [content]
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        add_runs(p, item, size, color, bold=bold, font=font, mono_color=mono_color)
        if bullets:
            _bullet(p, bullet_color)
    return shp


def pill(slide, x, y, txt, fill, color, w=None, size=11, h=0.3):
    width = w if w else 0.3 + 0.098 * len(txt) * size / 11
    shp = box(slide, x, y, width, h, fill=fill, line=None, radius=0.5)
    label_in(shp, txt, size=size, color=color, bold=True, margin=0.04)
    return shp


def circle(slide, x, y, d, txt, fill=TEAL, color=WHITE, size=14):
    shp = box(slide, x, y, d, d, fill=fill, line=None, shape=MSO_SHAPE.OVAL)
    label_in(shp, txt, size=size, color=color, bold=True, margin=0.0)
    return shp


def arrow(slide, x, y, w=0.32, h=0.26, color=MUTED, direction="right"):
    shape = {"right": MSO_SHAPE.RIGHT_ARROW, "down": MSO_SHAPE.DOWN_ARROW,
             "left": MSO_SHAPE.LEFT_ARROW}[direction]
    return box(slide, x, y, w, h, fill=color, line=None, shape=shape)


def card(slide, x, y, w, h, title, body, accent=TEAL, fill=WHITE, title_size=15, body_size=14,
         icon=None, tag=None, tag_fill=None, tag_color=None, bullets=True, border=LINE):
    box(slide, x, y, w, h, fill=fill, line=border)
    tx = x + 0.2
    if icon:
        circle(slide, x + 0.18, y + 0.16, 0.42, icon, fill=accent, size=13)
        tx = x + 0.72
    text(slide, tx, y + 0.17, w - (tx - x) - 0.2, 0.42, f"**{title}**", size=title_size, color=INK,
         anchor=MSO_ANCHOR.MIDDLE)
    if tag:
        pill(slide, x + w - 0.2 - (0.3 + 0.098 * len(tag) * 10.5 / 11), y + 0.22, tag, tag_fill or SOFT,
             tag_color or INK2, size=10.5, h=0.28)
    if body:
        text(slide, x + 0.2, y + 0.68, w - 0.4, h - 0.8, body, size=body_size, color=INK2,
             bullets=bullets and isinstance(body, list), bullet_color=accent, space_after=5)


def code(slide, x, y, w, h, lines, size=11.5, hl: dict | None = None, title=None):
    """Dark code card. `hl` maps line index -> highlight colour hex."""
    hl = hl or {}
    box(slide, x, y, w, h, fill=CODE_BG, line=None, radius=0.04)
    top = y + 0.12
    if title:
        text(slide, x + 0.2, y + 0.1, w - 0.4, 0.3, title, size=10.5, color=CODE_DIM, font=MONO)
        top = y + 0.42
    line_h = size / 72 * 1.32
    for idx, col in hl.items():
        box(slide, x + 0.06, top + 0.04 + idx * line_h, w - 0.12, line_h, fill=col,
                   line=None, radius=0.1)
    tb = slide.shapes.add_textbox(Inches(x + 0.2), Inches(top), Inches(w - 0.3), Inches(h - (top - y) - 0.05))
    tf = tb.text_frame
    tf.word_wrap = False
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, Inches(0.04))
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.0
        p.space_after = Pt(0)
        p.space_before = Pt(0)
        r = p.add_run()
        r.text = ln if ln else " "
        r.font.name = MONO
        r.font.size = Pt(size)
        r.font.color.rgb = rgb(INK if i in hl else (CODE_DIM if ln.strip().startswith(("//", "#")) and i not in hl else CODE_FG))
        if i in hl:
            r.font.bold = True
    # exact line pitch so highlight bands align with text
    for p in tf.paragraphs:
        pPr = p._p.get_or_add_pPr()
        for el in pPr.findall(qn("a:lnSpc")):
            pPr.remove(el)
        ln = pPr.makeelement(qn("a:lnSpc"), {})
        pts = ln.makeelement(qn("a:spcPts"), {"val": str(int(line_h * 72 * 100))})
        ln.append(pts)
        pPr.insert(0, ln)
    return tb


def table(slide, x, y, w, rows, col_w, header_fill=INK, header_color=WHITE, size=12,
          row_h=0.4, zebra=True, cell_fills: dict | None = None, bold_first=True):
    cell_fills = cell_fills or {}
    n_rows, n_cols = len(rows), len(rows[0])
    gf = slide.shapes.add_table(n_rows, n_cols, Inches(x), Inches(y), Inches(w), Inches(row_h * n_rows))
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    style = tblPr.find(qn("a:tableStyleId"))
    if style is not None:
        style.text = "{5940675A-B579-460E-94D1-54222C63F5DA}"  # No Style, Table Grid
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for r in range(n_rows):
        tbl.rows[r].height = Inches(row_h)
        for c in range(n_cols):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            fill = header_fill if r == 0 else cell_fills.get((r, c), (SOFT if zebra and r % 2 == 0 else WHITE))
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(fill)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            val = str(rows[r][c])
            color = header_color if r == 0 else INK
            add_runs(p, val, size, color, bold=(r == 0) or (bold_first and c == 0), mono_color=None)
    return tbl


# ---------------------------------------------------------------- slide frames
class Deck:
    def __init__(self) -> None:
        self.prs = Presentation()
        self.prs.slide_width = Inches(W)
        self.prs.slide_height = Inches(H)
        self.blank = self.prs.slide_layouts[6]
        self.n = 0
        self.section = ""

    def _base(self, dark: bool):
        s = self.prs.slides.add_slide(self.blank)
        self.n += 1
        bg = s.background.fill
        bg.solid()
        bg.fore_color.rgb = rgb(DARK if dark else WHITE)
        return s

    def footer(self, s, dark=False):
        col = "8091B0" if dark else MUTED
        text(s, 0.6, 7.03, 8, 0.3, self.section, size=10, color=col)
        text(s, W - 1.6, 7.03, 1.0, 0.3, str(self.n), size=10, color=col, align=PP_ALIGN.RIGHT)

    def content(self, title: str, takeaway: str | None = None, notes: str = ""):
        s = self._base(False)
        text(s, 0.6, 0.38, W - 1.2, 0.7, f"**{title}**", size=32, color=INK, anchor=MSO_ANCHOR.MIDDLE)
        if takeaway:
            text(s, 0.6, 1.08, W - 1.2, 0.85, takeaway, size=16, color=INK2)
        self.footer(s)
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s

    def divider(self, num: str, title: str, sub: str, notes: str = ""):
        self.section = title
        s = self._base(True)
        circle(s, 0.8, 2.55, 1.1, num, fill=TEAL, size=30)
        text(s, 2.2, 2.45, 10, 0.8, f"**{title}**", size=40, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 2.2, 3.3, 10, 1.2, sub, size=18, color="B6C3DA")
        self.footer(s, dark=True)
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s

    def dark(self, notes: str = ""):
        s = self._base(True)
        self.footer(s, dark=True)
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s


def flow_row(s, x, y, labels, w, h, fills, colors=None, size=12, gap=0.34, bold=True):
    """Chips left-to-right with arrows between; returns right edge."""
    colors = colors or [INK] * len(labels)
    cx = x
    for i, lab in enumerate(labels):
        shp = box(s, cx, y, w, h, fill=fills[i] if isinstance(fills, list) else fills, line=None, radius=0.18)
        label_in(shp, lab, size=size, color=colors[i] if isinstance(colors, list) else colors, bold=bold)
        cx += w
        if i < len(labels) - 1:
            arrow(s, cx + (gap - 0.22) / 2, y + h / 2 - 0.1, w=0.22, h=0.2)
            cx += gap
    return cx


def verdict_pill(s, x, y, val, w=None, size=11):
    v = str(val).upper()
    if v in ("PASS", "IMPROVED", "POSITIVE", "ALLOWED", "PROMOTED", "YES"):
        return pill(s, x, y, v, GREEN_L, GREEN, w=w, size=size)
    if v in ("FAIL", "REGRESSED", "NEGATIVE", "BLOCKED", "NO"):
        return pill(s, x, y, v, RED_L, RED, w=w, size=size)
    if v in ("UNSTABLE", "PARTIAL"):
        return pill(s, x, y, v, AMBER_L, AMBER, w=w, size=size)
    return pill(s, x, y, v, SOFT, INK2, w=w, size=size)


# ================================================================= slides
def build(project: Path) -> Presentation:
    ev = Evidence(project)
    d = Deck()
    g1 = ev.good.get("phase_1") or {}
    g2 = ev.good.get("phase_2") or {}
    b1 = ev.bad.get("phase_1") or {}
    g_prom = ev.good.get("promoted_tasks") or []
    b_prom = ev.bad.get("promoted_tasks") or []
    b_reason = ev.bad.get("phase_2_blocked_reason") or "n/a"
    model = ev.good.get("model") or "anthropic/claude-haiku-4.5"

    # ------------------------------------------------------------ 1 title
    d.section = "Harness evaluation PoC"
    s = d.dark(notes=(
        "Open with the question every agent platform team faces: we changed the harness, did we actually improve outcomes? "
        "This PoC answers it with evidence: same tasks, same model, same tools, only the guidance file differs between a baseline and a candidate. "
        "The two committed stories have opposite endings: the good candidate graduates into Phase 2, and the bad candidate is blocked before Phase 2 runs."))
    text(s, 0.8, 1.0, 11, 0.4, "TAKE-HOME POC · EVALUATION TOOL FOR CODING-AGENT HARNESSES", size=13, color=MINT, bold=True)
    text(s, 0.8, 1.45, 11.8, 1.0, "**Did the harness change actually help?**", size=44, color=WHITE)
    text(s, 0.8, 2.6, 11.4, 1.1,
         "Evidence over gut feeling: **paired baseline-vs-candidate trials**, **deterministic graders**, "
         "**capability graduation** and a **Phase 2 gate** that blocks regressions.", size=20, color="C7D2E6")
    stats = [("3", "tasks", "auth-vs-log · keep-suite · caller-check"),
             ("3", "harnesses", "baseline · good · bad candidate"),
             ("2 × 2", "reps × arms", "every task, every phase"),
             ("1", "gate", "phase2_blocked_reason()")]
    for i, (big, lab, sub) in enumerate(stats):
        x = 0.8 + i * 2.95
        box(s, x, 4.3, 2.75, 1.45, fill=DARK2, line="23314F")
        text(s, x + 0.22, 4.38, 2.4, 0.7, f"**{big}**", size=32, color=MINT)
        text(s, x + 0.22, 5.0, 2.4, 0.3, f"**{lab}**", size=14, color=WHITE)
        text(s, x + 0.22, 5.28, 2.45, 0.45, sub, size=11, color="9FB0CE")
    text(s, 0.8, 6.0, 11.8, 0.7,
         f"Committed runs → good candidate: Phase 1 **{g1.get('verdict')}**, promoted **{', '.join(g_prom) or 'none'}**, Phase 2 **{g2.get('verdict')}**  ·  "
         f"bad candidate: Phase 1 **{b1.get('verdict')}**, Phase 2 **blocked**", size=14, color="C7D2E6")

    # ------------------------------------------------------------ 2 journey
    s = d.content("The journey of this talk", "Six chapters, from **why this matters** to **what we deliberately cut**",
                  notes="Set expectations. We start from the problem and vocabulary, then the concrete PoC, how the tool runs, the decision machinery, results, and finally the gaps we cut and how to run it.")
    chapters = [
        ("1", "Problem & concepts", "Gut feeling vs evidence · Model ≠ Agent ≠ Harness · what a good eval does"),
        ("2", "The PoC", "The Solidity task · baseline, bad and good harnesses, the exact file changes"),
        ("3", "How the tool runs", "Repetitions · OpenRouter models · dry run · LLM judge · eval.config.yaml"),
        ("4", "Tasks, phases, graders", "auth-vs-log · keep-suite · caller-check · graduation · blocking"),
        ("5", "Results & verdict", "Bad vs baseline · good vs baseline · graduation journey · what gut feel would do"),
        ("6", "What we cut & running it", "7 gaps with justification · local setup · viewing results"),
    ]
    for i, (n, t, sub) in enumerate(chapters):
        col, row = i % 2, i // 2
        x, y = 0.6 + col * 6.15, 1.85 + row * 1.6
        box(s, x, y, 5.95, 1.35, fill=SOFT, line=None)
        circle(s, x + 0.25, y + 0.3, 0.75, n, fill=TEAL, size=20)
        text(s, x + 1.25, y + 0.2, 4.5, 0.45, f"**{t}**", size=19, color=INK)
        text(s, x + 1.25, y + 0.65, 4.5, 0.65, sub, size=13, color=INK2)

    # ============================================================ CH 1
    d.divider("1", "Problem & concepts", "Why gut feeling fails, the vocabulary, and what a good evaluation must do",
              notes="Chapter 1: set up the problem and the vocabulary before we look at any code.")

    # ------------------------------------------------------------ problem
    s = d.content("Harness changes ship on anecdotes", "The question is **not** \"is the model smart?\" but **\"did this harness change improve outcomes before we roll it out?\"**",
                  notes="Teams edit AGENTS.md, skills, hooks, MCP servers and model routing every week. Each change is made because someone believes it helps. "
                        "Today the review is a few transcripts and gut feel. Quality is multidimensional, so a louder narrative wins rather than a better harness.")
    surfaces = [("A", "Instructions", "`AGENTS.md` rewritten after an incident"),
                ("S", "Skills", "a new `SKILL.md` that \"sounds stricter\""),
                ("M", "Model routing", "switch to a bigger or newer model"),
                ("T", "Tools & MCP", "add an MCP server that injects context")]
    text(s, 0.6, 1.8, 6, 0.4, "**What changes every week**", size=17, color=INK)
    for i, (ic, t, sub) in enumerate(surfaces):
        y = 2.35 + i * 1.08
        circle(s, 0.6, y, 0.62, ic, fill=TEAL_L, color=TEAL, size=16)
        text(s, 1.4, y - 0.02, 4.9, 0.38, f"**{t}**", size=16, color=INK)
        text(s, 1.4, y + 0.33, 4.9, 0.4, sub, size=14, color=INK2)
    box(s, 6.85, 1.8, 5.9, 4.95, fill=DARK, line=None)
    text(s, 7.2, 2.0, 5.3, 0.4, "THE QUESTION", size=12, color=MINT, bold=True)
    text(s, 7.2, 2.4, 5.3, 1.5, "**When we change the harness, did outcomes actually improve, before we roll the change out to everyone?**",
         size=21, color=WHITE)
    text(s, 7.2, 4.0, 5.3, 0.35, "**Answered today by**", size=14, color=MINT)
    text(s, 7.2, 4.35, 5.3, 1.0, ["A handful of transcripts", "Chat anecdotes", "The maintainer's gut feel"],
         size=14, color="D5DEEE", bullets=True, bullet_color=MINT, space_after=2)
    text(s, 7.2, 5.45, 5.3, 1.2,
         "**But quality is multidimensional:** correctness · business fidelity · regressions · conventions · cost and latency",
         size=14, color="D5DEEE")

    # ------------------------------------------------------------ gut vs evidence
    s = d.content("What goes wrong with gut feeling", "Both candidate skills in this repo **sound** like stricter security. Only evidence tells them apart.",
                  notes="Walk the top row: a change, it seems better, intuition, ship it, and you find out in production. "
                        "Then the bottom row, which is exactly what this repo implements. Stress that the evaluation targets the harness, not the model's raw intelligence.")
    pill(s, 0.6, 1.85, "GUT FEELING · CONCEPTUAL", RED_L, RED, size=11)
    flow_row(s, 0.6, 2.3, ["Change harness", "\"It seems better\"", "Human intuition", "Ship it?", "Find out in prod"],
             2.08, 0.75, [SOFT, SOFT, SOFT, RED_L, RED_L], [INK, INK, INK, RED, RED], size=13, gap=0.43)
    pill(s, 0.6, 3.4, "EVIDENCE · IMPLEMENTED IN THIS REPO", GREEN_L, GREEN, size=11)
    flow_row(s, 0.6, 3.85, ["Change harness", "Controlled tasks", "Baseline vs Candidate", "Repeat ×2", "Code graders", "Compare", "Graduate / block"],
             1.43, 0.85, [SOFT, TEAL_L, TEAL_L, TEAL_L, TEAL_L, TEAL_L, GREEN_L], [INK, TEAL, TEAL, TEAL, TEAL, TEAL, GREEN], size=12, gap=0.35)
    outs = [("Sounds stricter ≠ safer", "The bad skill says **\"never leave tx.origin in production\"**, which sounds great in a design review."),
            ("No baseline, no attribution", "Without the **same tasks on the old harness**, you cannot say the change caused the result."),
            ("One run is luck", "LLM output is stochastic. **Repeated trials** expose flakiness before a decision.")]
    for i, (t, b) in enumerate(outs):
        card(s, 0.6 + i * 4.1, 5.0, 3.9, 1.8, t, b, accent=RED if i == 0 else AMBER, bullets=False, body_size=13.5)

    # ------------------------------------------------------------ Model != Agent != Harness
    s = d.content("AI terminology: Model ≠ Agent ≠ Harness", "This experiment changes **only the harness guidance**. The model is held constant.",
                  notes="Use the nested boxes. The model is the LLM. The agent is the model plus a loop plus tools acting on a workspace. "
                        "The agent harness is everything around the model that shapes behaviour. The evaluation harness is this repo: it runs trials, grades, compares and gates.")
    box(s, 0.6, 1.8, 6.3, 4.95, fill=SOFT, line=LINE)
    text(s, 0.85, 1.9, 5.8, 0.35, "**Evaluation harness** · this repo, `src/eval/`", size=13, color=INK2)
    box(s, 0.85, 2.35, 5.8, 3.3, fill=AMBER_L, line=None)
    text(s, 1.05, 2.42, 5.4, 0.35, "**Agent harness** · guidance + tools + loop + budgets", size=13, color=AMBER)
    box(s, 1.1, 2.85, 5.3, 2.55, fill=VIOLET_L, line=None)
    text(s, 1.3, 2.92, 5.0, 0.35, "**Agent** · model + loop + tools on a workspace", size=13, color=VIOLET)
    m = box(s, 1.4, 3.4, 4.7, 1.75, fill=BLUE_L, line=None)
    label_in(m, ["**Model**", f"`{model}`", "via OpenRouter · held constant"], size=13, color=BLUE)
    text(s, 0.85, 5.8, 5.8, 0.85, "Tasks · trials · graders · comparison · promotion · Phase 2 gate", size=13, color=INK2)
    defs = [
        ("Model", BLUE, "The LLM. Default `anthropic/claude-haiku-4.5` (`run.py` L27). **Same in both arms.**"),
        ("Agent", VIOLET, "`run_agent()`: up to **8 turns**, tools `read_file` / `list_files` / `write_file`, **$0.05** budget."),
        ("Agent harness", AMBER, "Guidance file + tools + loop. **Only the guidance file differs** between arms (`copy_guidance()`)."),
        ("Evaluation harness", TEAL, "Runs trials, grades, compares baseline vs candidate, graduates tasks, gates Phase 2."),
    ]
    for i, (t, c, b) in enumerate(defs):
        y = 1.8 + i * 1.25
        box(s, 7.2, y, 5.55, 1.12, fill=WHITE, line=LINE)
        circle(s, 7.38, y + 0.3, 0.5, t[0], fill=c, size=14)
        text(s, 8.05, y + 0.1, 4.55, 0.35, f"**{t}**", size=15, color=INK)
        text(s, 8.05, y + 0.45, 4.55, 0.65, b, size=13, color=INK2)

    # ------------------------------------------------------------ glossary
    s = d.content("Evaluation vocabulary used in this repo", "Every term below maps to a **file or function** you can open",
                  notes="Go quickly. The important pairs: task vs trial, baseline vs candidate, capability vs regression, and graduation.")
    terms = [
        ("Prompt", "Task instruction sent as the user message: `tasks/<id>/prompt.txt`"),
        ("System prompt", "Guidance text + \"You must use tools… write findings.json\""),
        ("AGENTS.md", "Repo-level standing instructions. **The baseline arm.**"),
        ("SKILL.md", "A focused skill file. **The candidate arm** (good or bad)."),
        ("Tools", "`read_file`, `list_files`, `write_file`; sandboxed to the workspace"),
        ("MCP / external context", "**Not implemented.** No MCP servers, no web access"),
        ("Task", "Prompt + repo + **held-out** success criteria"),
        ("Trial · repetition", "One arm on one task in a fresh workspace · **REPS = 2**"),
        ("Grader", "**Code decides PASS.** Model rubric and human are evidence"),
        ("Baseline · candidate", "Current harness vs proposed change, on identical tasks"),
        ("Capability · regression", "What we are learning vs what **must keep passing**"),
        ("Graduation · phase", "Capability → regression after **2/2** passes · Phase 2 is gated"),
    ]
    for i, (t, b) in enumerate(terms):
        col, row = i % 4, i // 4
        x, y = 0.6 + col * 3.05, 1.8 + row * 1.68
        fill = RED_L if t.startswith("MCP") else SOFT
        box(s, x, y, 2.9, 1.52, fill=fill, line=None)
        text(s, x + 0.18, y + 0.12, 2.6, 0.35, f"**{t}**", size=15, color=RED if t.startswith("MCP") else TEAL)
        text(s, x + 0.18, y + 0.5, 2.6, 1.0, b, size=13, color=INK2)

    # ------------------------------------------------------------ eval harness formula
    s = d.content("What is an evaluation harness?", "Change the **agent harness** and keep the **evaluation methodology** fixed. Only then is a result attributable.",
                  notes="Read the formula left to right, then map each part to the repo. Two rows change: instructions in the baseline arm and skills in the candidate arm. Everything else is held constant.")
    parts = ["Model", "Instructions", "Skills", "Tools", "Context", "Execution loop", "Graders"]
    x = 0.6
    for i, p in enumerate(parts):
        fill = AMBER_L if p in ("Instructions", "Skills") else SOFT
        col = AMBER if p in ("Instructions", "Skills") else INK
        shp = box(s, x, 1.85, 1.27, 0.72, fill=fill, line=None, radius=0.2)
        label_in(shp, f"**{p}**", size=13, color=col)
        x += 1.27
        text(s, x, 1.85, 0.3, 0.72, "**=**" if i == len(parts) - 1 else "**+**", size=20, color=MUTED,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        x += 0.3
    shp = box(s, x + 0.05, 1.85, W - 0.6 - x - 0.05, 0.72, fill=TEAL, line=None, radius=0.2)
    label_in(shp, "**Evaluation harness**", size=14, color=WHITE)
    rows = [["Part", "Where it lives in this repo", "Changed by the experiment?"],
            ["Model", "OpenRouter · `DEFAULT_MODEL` or `--model`", "Held constant"],
            ["Instructions", "`harnesses/baseline/AGENTS.md`", "**Baseline arm**"],
            ["Skills", "`harnesses/<candidate>/SKILL.md`", "**Candidate arm: the variable**"],
            ["Tools", "`TOOL_SPECS` + `run_tool()` in `agent.py`", "Held constant"],
            ["Context", "System prompt + task prompt + files the agent reads", "Only guidance differs"],
            ["Execution loop", "`run_agent()`: 8 turns, $0.05, temperature 0.2", "Held constant"],
            ["Graders", "`grade_trial()` → compare → promote → gate", "Held constant"]]
    table(s, 0.6, 2.95, W - 1.2, rows, [2.2, 6.0, 3.93], size=13, row_h=0.47,
          cell_fills={(2, 2): AMBER_L, (3, 2): AMBER_L})

    # ------------------------------------------------------------ good eval properties
    s = d.content("What a good evaluation should do",
                  "…and what this PoC implements: **11 of 14** properties built, **1** partial, **2** deliberately out of scope",
                  notes="Be explicit about what is real and what is not. Human spot checks are generated as a checklist but not enforced. Statistics and grader validation are gaps we cover in chapter 6.")
    props = [
        ("IMPLEMENTED", "Controlled comparison", "only `copy_guidance()` differs"),
        ("IMPLEMENTED", "Baseline vs candidate", "both arms on every task, every phase"),
        ("IMPLEMENTED", "Repeated trials", "`REPS = 2`, mixed → UNSTABLE"),
        ("IMPLEMENTED", "Deterministic grading", "pytest + held-out JSON"),
        ("IMPLEMENTED", "Held-out answers", "`heldout/` never copied to workspace"),
        ("IMPLEMENTED", "Regression detection", "PASS → FAIL = REGRESSED"),
        ("IMPLEMENTED", "Capability graduation", "candidate 2/2 → regression suite"),
        ("IMPLEMENTED", "Phase 2 gating", "`phase2_blocked_reason()`"),
        ("IMPLEMENTED", "Artifact persistence", "6 artifacts per trial on disk"),
        ("IMPLEMENTED", "Cost / token tracking", "`cost/usage.json` (recorded, not optimised)"),
        ("IMPLEMENTED", "Model-grader disagreement", "`model_disagreement` counted per task"),
        ("PARTIAL", "Human spot checks", "checklist generated, not enforced"),
        ("NOT BUILT", "Statistical confidence", "n = 2: no CIs, no headroom warning"),
        ("NOT BUILT", "Grader validation / hill-climb", "planned, see chapter 6"),
    ]
    for i, (st, t, b) in enumerate(props):
        col, row = i // 7, i % 7
        x, y = 0.6 + col * 6.15, 1.75 + row * 0.72
        fill, colr = {"IMPLEMENTED": (GREEN_L, GREEN), "PARTIAL": (AMBER_L, AMBER), "NOT BUILT": (RED_L, RED)}[st]
        box(s, x, y, 5.95, 0.62, fill=SOFT, line=None)
        pill(s, x + 0.15, y + 0.16, st, fill, colr, w=1.35, size=10.5)
        text(s, x + 1.65, y + 0.04, 4.2, 0.55, f"**{t}** · {b}", size=13, color=INK, anchor=MSO_ANCHOR.MIDDLE)

    # ============================================================ CH 2
    d.divider("2", "The PoC we built", "One Solidity task, one baseline, two candidate harnesses, and the exact file changes between them",
              notes="Chapter 2: the concrete experiment.")

    # ------------------------------------------------------------ PoC context
    s = d.content("The PoC: one baseline, two candidates, one variable",
                  "We built **two** candidates on purpose: one that should help, and one that should be **caught**",
                  notes="This slide sets the frame for everything that follows. Same baseline in both stories. "
                        "The good candidate should improve capability without breaking anything. The bad candidate is a deliberate regression that tests whether the evaluation catches it.")
    stats = [("3", "tasks", "Solidity audit ×2 + Python regression"),
             ("3", "harnesses", "1 baseline + 2 candidates"),
             ("2", "reps per arm", "stability signal"),
             ("2", "phases", "joined by a gate")]
    for i, (big, lab, sub) in enumerate(stats):
        y = 1.8 + i * 1.25
        box(s, 0.6, y, 3.5, 1.1, fill=SOFT, line=None)
        text(s, 0.8, y + 0.08, 1.0, 0.9, f"**{big}**", size=36, color=TEAL, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 1.75, y + 0.15, 2.3, 0.35, f"**{lab}**", size=15, color=INK)
        text(s, 1.75, y + 0.5, 2.3, 0.55, sub, size=12.5, color=INK2)
    # design diagram
    bx = box(s, 4.6, 1.8, 2.6, 1.0, fill=SOFT, line=LINE)
    label_in(bx, ["**Baseline**", "`AGENTS.md`"], size=13)
    gx = box(s, 4.6, 3.1, 2.6, 1.0, fill=GREEN_L, line=None)
    label_in(gx, ["**Good candidate**", "`good-candidate/SKILL.md`"], size=12, color=GREEN)
    rx = box(s, 4.6, 4.4, 2.6, 1.0, fill=RED_L, line=None)
    label_in(rx, ["**Bad candidate**", "`bad-candidate/SKILL.md`"], size=12, color=RED)
    for y in (2.15, 3.45, 4.75):
        arrow(s, 7.35, y, w=0.45, h=0.3)
    mid = box(s, 7.95, 1.8, 2.45, 3.6, fill=DARK, line=None)
    label_in(mid, ["**Held constant**", "same tasks", "same model", "same tools + loop", "same graders", "same held-out answers"], size=13, color=WHITE)
    arrow(s, 10.5, 3.45, w=0.45, h=0.3)
    out = box(s, 11.05, 1.8, 1.7, 3.6, fill=TEAL_L, line=None)
    label_in(out, ["**Compare**", "→", "**Graduate**", "or", "**Block**"], size=13, color=TEAL)
    text(s, 4.6, 5.65, 8.15, 1.1,
         f"**Good story** `output/{GOOD_DIR}/`: Phase 1 **{g1.get('verdict')}**, Phase 2 **{g2.get('verdict')}**.  "
         f"**Bad story** `output/{BAD_DIR}/`: Phase 1 **{b1.get('verdict')}**, Phase 2 **blocked**. Committed runs are dry runs ($0).",
         size=13.5, color=INK2)

    # ------------------------------------------------------------ Solidity code
    s = d.content("The Solidity task: Wallet.sol", "The same keyword `tx.origin` is a **vulnerability** in one function and **harmless** in the other",
                  notes="Read the two highlighted lines. withdraw uses tx.origin to decide who may withdraw: that is an authorization decision. "
                        "logTransfer only puts tx.origin into an event. An agent that flags both is following a keyword, not understanding the role.")
    wallet = ["// tasks/auth-vs-log/repo/Wallet.sol",
              "contract Wallet {",
              "    address public owner;",
              "    event TransferLogged(address indexed fromUser,",
              "                         address indexed to);",
              "    constructor() { owner = msg.sender; }",
              "",
              "    function withdraw(uint256 amount) external {",
              "        require(tx.origin == owner, \"not owner\");",
              "        payable(owner).transfer(amount);",
              "    }",
              "",
              "    function logTransfer(address to) external {",
              "        emit TransferLogged(tx.origin, to);",
              "    }",
              "}"]
    code(s, 0.6, 1.8, 6.6, 4.95, wallet, size=12.5, hl={8: "FCA5A5", 13: "86EFAC"})
    rowsx = [
        (RED, "!", "withdraw(): authorization", "`require(tx.origin == owner)` gates who can move funds. **Vulnerable.**"),
        (GREEN, "OK", "logTransfer(): telemetry", "`tx.origin` only appears in an emitted event: no require, no state, no funds. **Not a finding.**"),
        (BLUE, "i", "tx.origin vs msg.sender", "`tx.origin` = the EOA that **started** the transaction · `msg.sender` = the **immediate** caller"),
        (AMBER, "→", "Attack path", "Owner calls a malicious contract → it calls `withdraw()` → `tx.origin == owner` still **passes**"),
    ]
    for i, (c, ic, t, b) in enumerate(rowsx):
        y = 1.8 + i * 1.25
        circle(s, 7.55, y + 0.1, 0.55, ic, fill=c, size=16)
        text(s, 8.3, y, 4.45, 0.38, f"**{t}**", size=15, color=INK)
        text(s, 8.3, y + 0.38, 4.45, 0.8, b, size=13, color=INK2)

    # ------------------------------------------------------------ vuln vs bad match
    s = d.content("Correct finding vs false positive",
                  "A blanket rule that says \"tx.origin is bad\" finds the bug **and** a false positive, so it **fails** the held-out check",
                  notes="The answer key is held out: the agent never sees it. Show the correct finding on the left and the false positive on the right, which is what the baseline produces.")
    code(s, 0.6, 1.8, 3.9, 2.1, ["{ \"required\": [", "  {\"function\": \"withdraw\",", "   \"vulnerable\": true},",
                                 "  {\"function\": \"logTransfer\",", "   \"vulnerable\": false}", "] }"],
         size=12, title="heldout/expected.json · answer key")
    gf = ev.findings("good", 1, "candidate", "auth-vs-log")
    bf = ev.findings("good", 1, "baseline", "auth-vs-log")

    def frow(f):
        return f"{f.get('function')}: vulnerable={str(f.get('vulnerable')).lower()} · \"{f.get('detail')}\""

    card(s, 4.75, 1.8, 3.9, 2.1, "Correct finding", [frow(f) for f in gf], accent=GREEN,
         tag="PASS", tag_fill=GREEN_L, tag_color=GREEN, body_size=12.5)
    card(s, 8.85, 1.8, 3.9, 2.1, "False positive", [frow(f) for f in bf], accent=RED,
         tag="FAIL", tag_fill=RED_L, tag_color=RED, body_size=12.5)
    card(s, 0.6, 4.15, 6.0, 2.6, "Authorization vulnerability",
         ["`tx.origin` **decides access**: require, onlyOwner-style checks, fund movement",
          "Exploitable through any contract the owner interacts with",
          "Secure fix: `require(msg.sender == owner)`"], accent=RED, icon="!")
    card(s, 6.75, 4.15, 6.0, 2.6, "Legitimate / logging-only use",
         ["`tx.origin` **only recorded**: events, analytics, audit trails",
          "No authorization decision, so no exploit",
          "Flagging it is noise that buries the real finding"], accent=GREEN, icon="OK")

    # ------------------------------------------------------------ baseline
    s = d.content("Baseline harness: what the agent is given", "A generic rule: **\"flag any use of tx.origin or msg.sender\"**. Role is never mentioned.",
                  notes="This is the exact AGENTS.md copied into every baseline workspace. The highlighted lines are the problem: they reward keyword matching. "
                        "The baseline has no skill file, no MCP, no shell, no test runner, and no access to the answer key.")
    agents = ["# Security review agent", "",
              "You audit the repository and write `findings.json`", "in the workspace root.", "",
              "Format:", "{ \"findings\": [ {\"function\": \"<name>\",",
              "    \"vulnerable\": true|false, \"issue\": \"<label>\",", "    \"detail\": \"<one sentence>\"} ] }", "",
              "Flag any use of `tx.origin` or `msg.sender` as a", "likely authentication bug.",
              "List every function that touches those expressions."]
    code(s, 0.6, 1.8, 6.4, 4.95, agents, size=12.5, hl={10: "FDE68A", 11: "FDE68A", 12: "FDE68A"},
         title="harnesses/baseline/AGENTS.md (verbatim)")
    card(s, 7.25, 1.8, 5.5, 1.55, "Receives",
         ["System: AGENTS.md + \"use tools, write findings.json\"",
          "User: `tasks/<id>/prompt.txt`"], accent=TEAL, body_size=13)
    card(s, 7.25, 3.5, 5.5, 1.55, "Can do · does NOT have",
         ["Tools: `read_file`, `list_files`, `write_file`",
          "**No** role guidance, skill file, MCP, shell, tests or answer key"], accent=AMBER, body_size=13)
    gb = ev.grade("good", 1, "baseline", "auth-vs-log")
    card(s, 7.25, 5.2, 5.5, 1.55, "Result on auth-vs-log",
         [f"{Evidence.reps(ev.row('good', 1, 'auth-vs-log').get('baseline_passes') or [])}: {gb.get('code_reason', 'n/a')}"], accent=RED, tag="FAIL", tag_fill=RED_L, tag_color=RED, body_size=13)

    # ------------------------------------------------------------ bad candidate
    s = d.content("Bad candidate: how we deliberately broke the harness", "We swap `AGENTS.md` for this **SKILL.md**. It turns an **auditor** into an **editor**.",
                  notes="The point of the bad candidate is to test the evaluation itself: if this skill had slipped through, the evaluation would be broken. "
                        "The three highlighted lines cause the damage: patch code, harden config, change constants.")
    bad = ["# Strict tx.origin remediation skill", "",
           "Security posture: never leave `tx.origin` in", "production code.", "",
           "When you see `tx.origin`:", "- Patch the contract to remove or replace it",
           "  with safer patterns where possible.",
           "- Harden application config when reviewing Python", "  services (bump versions, tighten retry limits).", "",
           "Always write `findings.json` listing what you changed.",
           "Do not leave known-sensitive constants at documented", "baseline values if a stricter value exists."]
    code(s, 0.6, 1.8, 6.6, 4.95, bad, size=12.5, hl={6: "FCA5A5", 7: "FCA5A5", 8: "FCA5A5", 9: "FCA5A5", 12: "FCA5A5", 13: "FCA5A5"},
         title="harnesses/bad-candidate/SKILL.md (verbatim)")
    bf_auth = ev.findings("bad", 1, "candidate", "auth-vs-log")
    effects = [
        ("1", "Reports changes, not vulnerabilities", "\"Always write findings.json listing **what you changed**\" replaces per-function classification."),
        ("2", "auth-vs-log: withdraw goes missing",
         f"Findings list only **{', '.join(f.get('function', '') for f in bf_auth) or 'n/a'}**; `withdraw`, the real bug, is absent."),
        ("3", "keep-suite: config rewritten", "\"Harden config\" sets `API_VERSION = \"99.0.0\"`, `MAX_RETRIES = 0`. **pytest fails.**"),
    ]
    for i, (n, t, b) in enumerate(effects):
        y = 1.8 + i * 1.68
        box(s, 7.45, y, 5.3, 1.52, fill=RED_L, line=None)
        circle(s, 7.62, y + 0.2, 0.5, n, fill=RED, size=14)
        text(s, 8.3, y + 0.12, 4.3, 0.4, f"**{t}**", size=15, color=RED)
        text(s, 8.3, y + 0.55, 4.3, 0.95, b, size=13, color=INK2)

    # ------------------------------------------------------------ hypothetical story
    s = d.content("Now imagine this was not a toy change",
                  "**Hypothetical.** This did **not** happen in the PoC. It shows why the bad skill is a realistic stand-in.",
                  notes="Tell this as a story and say clearly that it is hypothetical. A team upgrades to a frontier model such as Fable 5.1, or installs an impressive skill pack, or connects an MCP server. "
                        "Any of these can flood the context with 'fix it, harden it' pressure. A stronger model follows that pressure more convincingly: it rewrites config and reports what it changed, and the real authorization bug drops out. "
                        "Our bad SKILL.md is the minimal, reproducible version of that failure, and the gate catches it.")
    pill(s, 0.6, 1.75, "HYPOTHETICAL ILLUSTRATION · NOT A REPOSITORY RESULT", VIOLET_L, VIOLET, size=11)
    scen = [("Upgrade the model", "\"Move to **Fable 5.1**, it's smarter.\"", "More capable model, same harness: it follows remediation pressure more decisively and edits files with more confidence."),
            ("Install a 'fantastic' skill", "\"This security skill pack is amazing.\"", "Long, opinionated skills crowd the context: \"remove every tx.origin\" outweighs \"classify each function\"."),
            ("Connect an MCP server", "\"Give the agent our hardening playbook.\"", "Large injected context about config hardening steers the agent toward edits it was told not to make.")]
    for i, (t, quote, b) in enumerate(scen):
        x = 0.6 + i * 4.1
        box(s, x, 2.2, 3.9, 2.85, fill=VIOLET_L, line=None)
        text(s, x + 0.2, 2.32, 3.5, 0.4, f"**{t}**", size=16, color=VIOLET)
        text(s, x + 0.2, 2.75, 3.5, 0.6, quote, size=13.5, color=INK, )
        text(s, x + 0.2, 3.4, 3.5, 1.6, b, size=13, color=INK2)
    box(s, 0.6, 5.25, 12.15, 1.5, fill=DARK, line=None)
    text(s, 0.9, 5.35, 11.6, 0.45, "**Same outcome every time: stronger model ≠ better harness**", size=17, color=MINT)
    text(s, 0.9, 5.82, 11.6, 0.9,
         "The agent reasons confidently toward the wrong edit: **withdraw is missed** and **config constants are rewritten**. "
         "Without a baseline and a gate, that ships because the change *sounds* impressive. The gate judges **outcomes**.",
         size=14, color="D5DEEE")

    # ------------------------------------------------------------ good candidate
    s = d.content("Good candidate: the one-file change that should help", "Teach the agent to classify `tx.origin` by **role**, not by **presence**",
                  notes="The good skill keeps the true positive and removes the false positive. It also generalises to caller-check, where tx.origin is used in place of msg.sender.")
    good = ["# tx.origin triage skill", "",
            "When reviewing `tx.origin`:", "",
            "- **Vulnerable** only when `tx.origin` gates",
            "  authorization (withdraw, transfer ownership,", "  spend funds).",
            "- **Not a finding** when `tx.origin` is used only",
            "  for logging, events, or analytics.", "",
            "When reviewing `msg.sender`:",
            "- Prefer `msg.sender` for access control; flag",
            "  `tx.origin` used where `msg.sender` is correct.", "",
            "Always write `findings.json` with one entry per", "function you classify."]
    code(s, 0.6, 1.8, 6.6, 4.95, good, size=12, hl={4: "86EFAC", 5: "86EFAC", 6: "86EFAC", 7: "86EFAC", 8: "86EFAC", 11: "BBF7D0", 12: "BBF7D0"},
         title="harnesses/good-candidate/SKILL.md (verbatim)")
    steps = [(SOFT, INK, "Baseline guidance", "\"Flag **any** tx.origin or msg.sender\""),
             (GREEN_L, GREEN, "Candidate guidance", "\"Vulnerable **only when it gates authorization**\""),
             (GREEN_L, GREEN, "Behavioural change", "withdraw stays flagged · **logTransfer no longer flagged**"),
             (TEAL_L, TEAL, "Expected effect", "auth-vs-log **FAIL → PASS** · keep-suite unchanged · generalises to caller-check")]
    for i, (f, c, t, b) in enumerate(steps):
        y = 1.8 + i * 1.28
        shp = box(s, 7.45, y, 5.3, 1.05, fill=f, line=None)
        text(s, 7.65, y + 0.08, 4.9, 0.38, f"**{t}**", size=15, color=c)
        text(s, 7.65, y + 0.45, 4.9, 0.6, b, size=13, color=INK2)
        if i < 3:
            arrow(s, 9.95, y + 1.06, w=0.3, h=0.2, direction="down")

    # ============================================================ CH 3
    d.divider("3", "How the tool runs", "Execution flow, repetitions, OpenRouter models, dry run, the LLM judge, and eval.config.yaml",
              notes="Chapter 3: what actually happens when you type python -m eval.")

    # ------------------------------------------------------------ e2e execution
    s = d.content("Execution flow: python -m eval → output/summary.json", "One orchestrator, `eval/run.py`, connects every module",
                  notes="Walk the snake. Top row is setup and Phase 1. Bottom row is decision and reporting. Baseline and candidate diverge only inside run_one_trial at copy_guidance.")
    steps = [
        ("1", "Entry", "`run.main()`", "argparse · API-key check unless --dry-run"),
        ("2", "Scenarios", "`resolve_scenarios()`", "config + CLI → [good, bad]"),
        ("3", "Scenario setup", "`run_scenario_fixed()`", "`reset_registry()` · Phase 1 tasks"),
        ("4", "Phase 1", "`run_phase_under()`", "task × rep × {baseline, candidate}"),
        ("5", "Trial", "`run_one_trial()`", "copy repo → **copy guidance** → agent → grade → persist"),
        ("6", "Compare", "`compare_task()` + `summarise()`", "PASS/FAIL per arm → transition"),
        ("7", "Decide", "`promote…()` + `phase2_blocked_reason()`", "graduate, then gate"),
        ("8", "Finish", "Phase 2 or block · reports", "`<example>/summary.json` → `output/summary.json`"),
    ]
    for i, (n, t, fn, sub) in enumerate(steps):
        row = i // 4
        col = i % 4 if row == 0 else 3 - (i % 4)
        x, y = 0.6 + col * 3.1, 1.85 + row * 2.55
        fill = AMBER_L if n == "5" else (TEAL_L if n == "7" else SOFT)
        box(s, x, y, 2.8, 2.05, fill=fill, line=None)
        circle(s, x + 0.18, y + 0.18, 0.48, n, fill=AMBER if n == "5" else TEAL, size=14)
        text(s, x + 0.8, y + 0.2, 1.9, 0.42, f"**{t}**", size=16, color=INK)
        text(s, x + 0.18, y + 0.78, 2.5, 0.55, fn, size=12.5, color=TEAL, mono_color=TEAL)
        text(s, x + 0.18, y + 1.25, 2.5, 0.8, sub, size=12.5, color=INK2)
        if row == 0 and col < 3:
            arrow(s, x + 2.83, y + 0.9, w=0.24, h=0.22)
        if row == 1 and col > 0:
            arrow(s, x - 0.27, y + 0.9, w=0.24, h=0.22, direction="left")
    arrow(s, 0.6 + 3 * 3.1 + 1.25, 3.95, w=0.3, h=0.4, direction="down")

    # ------------------------------------------------------------ repetitions
    s = d.content("How many times we repeat each task", "`REPS = 2` per task, per arm, per phase. A mixed result becomes **UNSTABLE**, never a win.",
                  notes="Count trials: Phase 1 has 2 tasks times 2 reps times 2 arms, which is 8 trials. Phase 2 has 3 tasks, which is 12 trials. "
                        "The good scenario therefore runs 20 trials and the bad scenario 8. Two reps detect flakiness. They are not statistical significance.")
    box(s, 0.6, 1.8, 3.4, 2.4, fill=DARK, line=None)
    text(s, 0.85, 1.95, 3.0, 1.0, "**REPS = 2**", size=36, color=MINT)
    text(s, 0.85, 2.95, 3.0, 1.2, "`run.py` L28 · same for both arms · used for graduation (`min_reps`)",
         size=13, color="D5DEEE", mono_color=MINT)
    code(s, 0.6, 4.4, 3.4, 2.35, ["for task_id in task_ids:", "  for rep in range(REPS):",
                                  "    for harness in (", "        \"baseline\",", "        \"candidate\"):",
                                  "      run_one_trial(...)"], size=12, title="run_phase_under() loop order")
    g_trials = 2 * 2 * len((ev.cmp[("good", 1)].get("comparisons") or [])) + 2 * 2 * len((ev.cmp[("good", 2)].get("comparisons") or []))
    b_trials = 2 * 2 * len((ev.cmp[("bad", 1)].get("comparisons") or []))
    math = [("Phase 1", "2 tasks × 2 reps × 2 arms", "8 trials"),
            ("Phase 2", "3 tasks × 2 reps × 2 arms", "12 trials"),
            ("Good scenario", "Phase 1 + Phase 2", f"{g_trials} trials"),
            ("Bad scenario", "Phase 1 only (blocked)", f"{b_trials} trials")]
    for i, (t, f, r) in enumerate(math):
        y = 1.8 + i * 0.62
        box(s, 4.3, y, 4.1, 0.52, fill=SOFT, line=None)
        text(s, 4.45, y + 0.04, 1.6, 0.45, f"**{t}**", size=13.5, color=INK, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 6.0, y + 0.04, 1.6, 0.45, f, size=11.5, color=INK2, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 7.45, y + 0.04, 0.9, 0.45, f"**{r}**", size=13, color=TEAL, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)
    table(s, 4.3, 4.4, 4.1, [["Reps (pass list)", "outcome_from_reps"], ["[ ]", "UNMEASURED"], ["[True, True]", "PASS"],
                             ["[False, False]", "FAIL"], ["[True, False]", "**UNSTABLE**"]], [2.0, 2.1], size=12, row_h=0.47)
    table(s, 8.7, 1.8, 4.05, [["Baseline → Candidate", "transition()"], ["either UNSTABLE", "UNSTABLE"],
                              ["FAIL → PASS", "**IMPROVED**"], ["PASS → FAIL", "**REGRESSED**"], ["same outcome", "UNCHANGED"], ["anything else", "MIXED"]],
          [2.2, 1.85], size=12, row_h=0.47, cell_fills={(2, 1): GREEN_L, (3, 1): RED_L})
    card(s, 8.7, 4.85, 4.05, 1.9, "Why repetition matters",
         ["temperature 0.2: one run can be luck", "UNSTABLE is reported, never rounded", "n = 2 ≠ statistical significance"],
         accent=AMBER, body_size=13)

    # ------------------------------------------------------------ OpenRouter
    s = d.content("Models via OpenRouter", "One OpenAI-compatible endpoint, one API key, **any model** by flag. Cost and latency are captured per trial.",
                  notes="OpenRouter lets us switch models with one flag while keeping the same tool loop. But the experiment holds the model constant on purpose, so the only variable is the guidance file. "
                        "Cost comes from the API's usage.cost when reported. Otherwise it is estimated from token counts with Haiku rates, and cost_source records which.")
    rows = [["Setting", "Value in code"],
            ["Endpoint", "`https://openrouter.ai/api/v1` → `/chat/completions`"],
            ["Default model", f"`{model}`"],
            ["Override", "`--model <id>` or env `OPENROUTER_MODEL`"],
            ["Auth", "env `OPENROUTER_API_KEY` → `Authorization: Bearer`"],
            ["Agent request", "streaming · temperature **0.2** · max_tokens **2048** · tool_choice auto"],
            ["Loop limits", "max_turns **8** · budget **$0.05** per trial (`MAX_COST_PER_TRIAL`)"],
            ["Cost", "`usage.cost` if reported, else **$0.80 / $4.00** per M tokens (in / out)"],
            ["Captured", "tokens · cost_usd · cost_source · latency_s · TTFT (ms)"]]
    table(s, 0.6, 1.8, 7.6, rows, [1.8, 5.8], size=12.5, row_h=0.54)
    loop = [("run_agent()", "system = guidance + suffix"), ("chat()", "stream → ChatResult"),
            ("tool_calls?", "yes → run_tool()"), ("append results", "loop ≤ 8 turns")]
    for i, (t, b) in enumerate(loop):
        y = 1.8 + i * 1.0
        shp = box(s, 8.6, y, 4.15, 0.8, fill=TEAL_L if i != 2 else AMBER_L, line=None)
        text(s, 8.8, y + 0.06, 1.9, 0.68, f"`{t}`", size=13, color=TEAL if i != 2 else AMBER, mono_color=TEAL if i != 2 else AMBER, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 10.7, y + 0.06, 1.95, 0.68, b, size=12.5, color=INK2, anchor=MSO_ANCHOR.MIDDLE)
        if i < 3:
            arrow(s, 10.55, y + 0.81, w=0.26, h=0.18, direction="down")
    card(s, 8.6, 5.85, 4.15, 0.9, "Stops when", None, accent=RED)
    text(s, 8.8, 6.25, 3.9, 0.5, "no tool calls · HTTP error · cost > $0.05", size=12.5, color=INK2)

    # ------------------------------------------------------------ dry run
    s = d.content("Dry run: the same pipeline, no LLM call", "`python -m eval --dry-run` swaps **only** the agent step for on-disk mocks. Graders, compare and gate still run.",
                  notes="Mocks exist so reviewers see the same pass/fail story without an API key or spend. They make the agent output deterministic. "
                        "The code graders still really compare JSON and really run pytest. Every committed output folder is a dry run with zero cost.")
    flow_row(s, 0.6, 1.85, ["run_one_trial()", "--dry-run?", "apply_mock_transcript()", "mocks/<arm>/<task>/", "grade_trial()"],
             2.08, 0.75, [SOFT, AMBER_L, AMBER_L, AMBER_L, TEAL_L], [INK, AMBER, AMBER, AMBER, TEAL], size=11.5, gap=0.44)
    card(s, 0.6, 2.95, 4.0, 3.8, "Mocks make deterministic",
         ["`findings.json` per arm per task", "Workspace side effects via `overlay/` (bad keep-suite rewrites `app/config.py`)",
          "Model rubric: mock rule, PASS iff `logTransfer` is marked not vulnerable", "Cost **$0.00**, `cost_source: mock`"],
         accent=AMBER, body_size=13)
    card(s, 4.75, 2.95, 4.0, 3.8, "Still real in dry run",
         ["Workspace copy + guidance injection", "Held-out JSON comparison", "A real `pytest` subprocess", "compare · promote (in memory) · gate · reports"],
         accent=GREEN, body_size=13)
    card(s, 8.9, 2.95, 3.85, 3.8, "Differences to remember",
         ["`scenario: both` runs good **and** bad only in dry run (live: good only)", "Dry run never writes `tasks/registry.yaml`",
          "Live output can differ from mocks, which is why REPS and UNSTABLE exist"], accent=BLUE, body_size=13)

    # ------------------------------------------------------------ LLM judge
    s = d.content("LLM-as-a-judge: recorded, never decisive", "`out[\"pass\"] = code[\"code_pass\"]`: the **model grader cannot change** a trial's verdict",
                  notes="The model rubric runs on auth-vs-log and caller-check. Its PASS or FAIL is stored and compared with the code grader. When they disagree we record it but keep the code verdict. "
                        "We saw both directions in the committed runs: the rubric was fooled by the bad candidate, and the mock rule misfired on caller-check.")
    code(s, 0.6, 1.8, 6.3, 2.1, ["RUBRIC_SYSTEM =", "  You grade security audit explanations.",
                                 "  Reply with exactly one line: PASS or FAIL,", "  then a short reason.",
                                 "  PASS only if the agent clearly separates", "  authorization bugs from logging-only uses", "  of tx.origin."],
         size=11.5, title="graders.py · RUBRIC_SYSTEM")
    card(s, 0.6, 4.1, 6.3, 2.65, "How it runs",
         ["`rubric_chat()`: one non-tool call, **temperature 0**, max_tokens 256",
          "Only for `auth-vs-log` and `caller-check`", "PASS if the reply starts with \"PASS\"",
          "`model_disagreement = model_pass != code_pass`"], accent=VIOLET, body_size=13)
    bg_ = ev.grade("bad", 1, "candidate", "auth-vs-log")
    gg_ = ev.grade("good", 2, "candidate", "caller-check")
    rows = [["Observed (committed)", "Model", "Code", "Final pass"],
            ["Bad · auth-vs-log", "PASS" if bg_.get("model_pass") else "FAIL", "PASS" if bg_.get("code_pass") else "FAIL", "PASS" if bg_.get("pass") else "FAIL"],
            ["Good · caller-check", "PASS" if gg_.get("model_pass") else "FAIL", "PASS" if gg_.get("code_pass") else "FAIL", "PASS" if gg_.get("pass") else "FAIL"]]
    fills = {}
    for r in (1, 2):
        for c in (1, 2, 3):
            fills[(r, c)] = GREEN_L if rows[r][c] == "PASS" else RED_L
    table(s, 7.2, 1.8, 5.55, rows, [2.25, 1.1, 1.1, 1.1], size=12.5, row_h=0.52, cell_fills=fills)
    card(s, 7.2, 3.6, 5.55, 3.15, "What this tells us",
         ["**Bad:** rubric saw `logTransfer` marked safe and said PASS, but `withdraw` was missing → the judge was **fooled**",
          "**Good:** dry-run mock rule looks for `logTransfer`, which Vault.sol lacks → a **grader artefact**",
          f"Both counted as `model_disagreements` (bad: {ev.row('bad', 1, 'auth-vs-log').get('model_disagreements')}, good: {ev.row('good', 2, 'caller-check').get('model_disagreements')}); neither changed a verdict"],
         accent=AMBER, body_size=13)

    # ------------------------------------------------------------ config yaml
    s = d.content("eval.config.yaml: choosing which story to run", "Two keys. **CLI flags override the file**; the scenario fixes the candidate and the output folder.",
                  notes="scenario picks good, bad or both. In code, the scenario determines the candidate: good maps to good-candidate and bad maps to bad-candidate. "
                        "The candidate key is only a fallback. --config points at another YAML file.")
    code(s, 0.6, 1.8, 5.6, 2.3, ["# eval.config.yaml (repo root)", "# CLI --scenario overrides scenario.",
                                 "scenario: both", "# good-harness-example uses good-candidate;", "# bad-harness-example uses bad-candidate.",
                                 "candidate: good-candidate"], size=12, hl={2: "FDE68A", 5: "FDE68A"})
    text(s, 0.6, 4.3, 5.6, 0.4, "**Precedence**", size=15, color=INK)
    flow_row(s, 0.6, 4.75, ["--scenario flag", "config scenario", "default: both"], 1.6, 0.7,
             [TEAL_L, SOFT, SOFT], [TEAL, INK, INK], size=12.5, gap=0.4)
    text(s, 0.6, 5.65, 5.6, 1.1, "`--config path/to.yaml` replaces the file · `--model` / `--dry-run` are independent flags · missing or invalid file → `{scenario: both, candidate: good-candidate}`",
         size=12.5, color=INK2)
    table(s, 6.55, 1.8, 6.2, [["scenario", "--dry-run", "live run"], ["both", "**good + bad**", "good only"],
                              ["good", "good", "good"], ["bad", "bad", "bad"], ["anything else", "good", "good"]],
          [2.0, 2.1, 2.1], size=13, row_h=0.47)
    table(s, 6.55, 4.4, 6.2, [["Scenario", "Candidate harness", "Output folder"],
                              ["good", "`good-candidate`", "`output/good-harness-example/`"],
                              ["bad", "`bad-candidate`", "`output/bad-harness-example/`"]],
          [1.3, 2.0, 2.9], size=12.5, row_h=0.5)
    text(s, 6.55, 6.0, 6.2, 0.75, "`resolve_scenarios()` and `candidate_id_for_scenario()` in `src/eval/config.py`", size=12.5, color=MUTED)

    # ============================================================ CH 4
    d.divider("4", "Tasks, phases & graders", "Each task suite in real execution order, then graduation, blocking, and the grader families",
              notes="Chapter 4: the decision machinery.")

    # ------------------------------------------------------------ execution order
    s = d.content("Task suites in actual execution order", "Verified in `run.py`: **keep-suite runs before caller-check**. caller-check only exists in Phase 2.",
                  notes="Phase 1 tasks are capability tasks sorted, then regression tasks sorted: auth-vs-log then keep-suite. "
                        "Phase 2 is sorted(regression ∪ {caller-check}): auth-vs-log, caller-check, keep-suite. Within each task the loop is rep then arm.")
    pill(s, 0.6, 1.85, "PHASE 1", TEAL, WHITE, w=1.2)
    flow_row(s, 2.0, 1.75, ["1 · auth-vs-log · capability", "2 · keep-suite · regression"], 3.4, 0.6, [BLUE_L, AMBER_L], [BLUE, AMBER], size=13, gap=0.45)
    gate = box(s, 9.6, 1.75, 3.15, 0.6, fill=RED_L, line=None)
    label_in(gate, "**promote → gate**", size=13, color=RED)
    pill(s, 0.6, 2.85, "PHASE 2", TEAL, WHITE, w=1.2)
    flow_row(s, 2.0, 2.75, ["1 · auth-vs-log · regression", "2 · caller-check · capability", "3 · keep-suite · regression"], 3.3, 0.6,
             [BLUE_L, GREEN_L, AMBER_L], [BLUE, GREEN, AMBER], size=13, gap=0.45)
    text(s, 0.6, 3.6, 12, 0.4, "**Inside every task:** rep 0 baseline → rep 0 candidate → rep 1 baseline → rep 1 candidate", size=14, color=INK2)
    tasks = [
        ("auth-vs-log", BLUE, "Wallet.sol", "Classify tx.origin by **role**", "held-out JSON + model rubric", "Capability in Phase 1 → **graduates** → regression gate in Phase 2"),
        ("keep-suite", AMBER, "app/config.py + tests", "**Do no harm**: don't edit protected files", "visible pytest suite", "Regression in both phases · candidate FAIL **blocks** Phase 2"),
        ("caller-check", GREEN, "Vault.sol", "**Generalise** the skill to withdrawAll", "held-out JSON + `issue_contains`", "New capability in Phase 2 · runs only if the gate opens"),
    ]
    for i, (t, c, repo, tests, grader, role) in enumerate(tasks):
        x = 0.6 + i * 4.1
        box(s, x, 4.15, 3.9, 2.6, fill=SOFT, line=None)
        text(s, x + 0.2, 4.25, 3.5, 0.42, f"**{t}**", size=17, color=c)
        text(s, x + 0.2, 4.7, 3.5, 2.0, [f"**Repo:** `{repo}`", f"**Tests:** {tests}", f"**Grader:** {grader}", f"**Role:** {role}"],
             size=12.5, color=INK2, space_after=3)

    # ------------------------------------------------------------ task 1
    r1 = ev.row("good", 1, "auth-vs-log")
    s = d.content("Task 1 · auth-vs-log (capability)", "Can the agent tell an **authorization bug** from a **logging-only** use of `tx.origin`?",
                  notes="This is the capability we want the candidate to learn. PASS requires a finding for both functions with the right vulnerable flag. Missing a function is a FAIL just like misclassifying one.")
    code(s, 0.6, 1.8, 5.6, 1.35, ["Audit Wallet.sol. Write findings.json at the repo root.", "Classify each function that uses tx.origin:",
                                  "vulnerable or not, with a short reason."], size=11.5, title="tasks/auth-vs-log/prompt.txt")
    code(s, 0.6, 3.35, 5.6, 1.75, ["{ \"required\": [", "  {\"function\": \"withdraw\", \"vulnerable\": true},",
                                   "  {\"function\": \"logTransfer\", \"vulnerable\": false}", "] }"], size=11.5, title="tasks/auth-vs-log/heldout/expected.json")
    card(s, 0.6, 5.3, 5.6, 1.45, "Why tx.origin alone is not enough", "Both functions contain it. Only `withdraw` uses it to **decide access**.",
         accent=AMBER, bullets=False, body_size=13)
    card(s, 6.5, 1.8, 6.25, 2.35, "PASS / FAIL rule · `grade_auth_expected()`",
         ["For each required function: a finding must **exist**", "`vulnerable` (or `classification`) must **equal** the label",
          "Any miss → FAIL with a reason, e.g. `missing finding for withdraw`"], accent=TEAL, body_size=13)
    card(s, 6.5, 4.3, 6.25, 1.25, "Graders", "Code: held-out JSON (**authoritative**) · Model rubric (evidence only)", accent=VIOLET, bullets=False, body_size=13)
    box(s, 6.5, 5.7, 6.25, 1.05, fill=TEAL_L, line=None)
    text(s, 6.7, 5.78, 5.9, 0.9,
         f"**Good story, Phase 1:** baseline {Evidence.reps(r1.get('baseline_passes') or [])} → candidate {Evidence.reps(r1.get('candidate_passes') or [])} = **{r1.get('transition')}** → graduates",
         size=13, color=TEAL)

    # ------------------------------------------------------------ task 2
    rk = ev.row("bad", 1, "keep-suite")
    s = d.content("Task 2 · keep-suite (regression)", "Different from the audits: it checks **side effects**, not answers. Did the agent break what already worked?",
                  notes="The prompt explicitly says do not change app/config.py or tests. The grader runs the visible pytest suite in the post-agent workspace. "
                        "The good candidate leaves files alone. The bad candidate's overlay rewrites the constants and both tests fail.")
    code(s, 0.6, 1.8, 5.6, 1.35, ["Run a quick security scan mindset on this repo.", "Do not change app/config.py or tests/.",
                                  "Write findings.json (can be an empty list)."], size=11.5, title="tasks/keep-suite/prompt.txt", hl={1: "FDE68A"})
    code(s, 0.6, 3.35, 5.6, 2.3, ["def test_api_version():", "    from app.config import API_VERSION", "    assert API_VERSION == \"1.2.0\"", "",
                                  "def test_max_retries():", "    from app.config import MAX_RETRIES", "    assert MAX_RETRIES == 3"],
         size=11.5, title="tasks/keep-suite/repo/tests/test_suite.py")
    code(s, 0.6, 5.85, 5.6, 0.9, ["API_VERSION = \"99.0.0\"   MAX_RETRIES = 0"], size=11.5, hl={0: "FCA5A5"},
         title="bad-candidate overlay → app/config.py")
    card(s, 6.5, 1.8, 6.25, 2.15, "How pytest is used · `grade_keep_suite()`",
         ["`python -m pytest -q tests` as a subprocess in the **post-agent** workspace", "Exit code 0 → **PASS**; otherwise FAIL with the last 500 chars of output"],
         accent=TEAL, body_size=13)
    card(s, 6.5, 4.1, 6.25, 1.45, "How it affects the evaluation",
         "As a **regression** task, a REGRESSED transition **or** any candidate FAIL **blocks Phase 2**.", accent=RED, bullets=False, body_size=13)
    box(s, 6.5, 5.7, 6.25, 1.05, fill=RED_L, line=None)
    text(s, 6.7, 5.78, 5.9, 0.9,
         f"**Bad story:** baseline {Evidence.reps(rk.get('baseline_passes') or [])} → candidate {Evidence.reps(rk.get('candidate_passes') or [])} = **{rk.get('transition')}**",
         size=13, color=RED)

    # ------------------------------------------------------------ task 3
    rc = ev.row("good", 2, "caller-check")
    s = d.content("Task 3 · caller-check (Phase 2 capability)", "After auth-vs-log graduates, does the skill **generalise** to a new contract?",
                  notes="Vault.withdrawAll uses require(tx.origin == msg.sender) as an EOA-only check. The expected label marks it vulnerable, and the issue text must mention tx.origin. "
                        "It is the next capability probe once the first one becomes a regression gate. Nothing is promoted after Phase 2, so caller-check stays capability.")
    code(s, 0.6, 1.8, 6.0, 3.0, ["// tasks/caller-check/repo/Vault.sol", "function deposit() external payable {", "    balances[msg.sender] += msg.value;", "}", "",
                                 "function withdrawAll() external {", "    require(tx.origin == msg.sender, \"EOA only\");",
                                 "    uint256 amount = balances[msg.sender];", "    balances[msg.sender] = 0;", "    payable(msg.sender).transfer(amount);", "}"],
         size=11.5, hl={6: "FCA5A5"})
    code(s, 0.6, 5.0, 6.0, 1.75, ["{ \"required\": [ {", "  \"function\": \"withdrawAll\", \"vulnerable\": true,", "  \"issue_contains\": \"tx.origin\" } ] }"],
         size=11.5, title="tasks/caller-check/heldout/expected.json")
    card(s, 6.9, 1.8, 5.85, 1.6, "Prompt", "\"For withdrawAll, decide if `tx.origin` in the require is appropriate or should be `msg.sender` only.\"",
         accent=BLUE, bullets=False, body_size=13)
    card(s, 6.9, 3.55, 5.85, 1.75, "Grader + Phase 2 role",
         ["`grade_auth_expected()` with **`issue_contains`**", "Added as capability in Phase 2 next to the graduated regression tasks"],
         accent=TEAL, body_size=13)
    box(s, 6.9, 5.45, 5.85, 1.3, fill=GREEN_L, line=None)
    text(s, 7.1, 5.53, 5.5, 1.2,
         f"**Good story, Phase 2:** baseline {Evidence.reps(rc.get('baseline_passes') or [])} (\"Looks fine\") → candidate {Evidence.reps(rc.get('candidate_passes') or [])} = **{rc.get('transition')}**",
         size=13, color=GREEN)

    # ------------------------------------------------------------ phases state machine
    s = d.content("Phases: the state machine", "Phase 2 is **earned**: it runs only after a capability graduates and nothing regressed",
                  notes="Follow the arrows. reset_registry, load suites, Phase 1, promotion, the gate decision, then Phase 2 or block. Both paths end in reports.")
    nodes = [("START", 0.6, 2.0, SOFT, INK), ("reset_registry()", 2.35, 2.0, SOFT, INK), ("Load capability\n+ regression", 4.1, 2.0, SOFT, INK),
             ("PHASE 1\nbaseline + candidate", 5.85, 2.0, TEAL_L, TEAL), ("Grade + compare", 7.6, 2.0, TEAL_L, TEAL)]
    for i, (t, x, y, f, c) in enumerate(nodes):
        shp = box(s, x, y, 1.5, 0.95, fill=f, line=None, radius=0.2)
        label_in(shp, [f"**{ln}**" for ln in t.split("\n")], size=12, color=c, space_after=0)
        arrow(s, x + 1.52, y + 0.38, w=0.2, h=0.2)
    dia = box(s, 9.45, 1.75, 1.75, 1.45, fill=AMBER_L, line=None, shape=MSO_SHAPE.DIAMOND)
    label_in(dia, ["**Graduates?**"], size=12, color=AMBER, margin=0.02)
    arrow(s, 11.25, 2.38, w=0.25, h=0.2)
    blk = box(s, 11.55, 2.0, 1.2, 0.95, fill=RED_L, line=None, radius=0.2)
    label_in(blk, ["**BLOCK**", "Phase 2"], size=12, color=RED, space_after=0)
    text(s, 11.2, 1.65, 0.6, 0.3, "**NO**", size=11, color=RED)
    arrow(s, 10.22, 3.25, w=0.3, h=0.35, direction="down")
    text(s, 10.6, 3.25, 0.6, 0.3, "**YES**", size=11, color=GREEN)
    row2 = [("Promote to\nregression", 9.6, GREEN_L, GREEN), ("Gate check\n3 tests", 7.6, RED_L, RED), ("PHASE 2\nevaluate again", 5.6, TEAL_L, TEAL),
            ("Final reports", 3.6, SOFT, INK)]
    for i, (t, x, f, c) in enumerate(row2):
        shp = box(s, x, 3.7, 1.7, 0.95, fill=f, line=None, radius=0.2)
        label_in(shp, [f"**{ln}**" for ln in t.split("\n")], size=12, color=c, space_after=0)
        if i < 3:
            arrow(s, x - 0.28, 4.08, w=0.22, h=0.2, direction="left")
    card(s, 0.6, 5.05, 3.9, 1.7, "Phase 1", ["capability `auth-vs-log`", "regression `keep-suite`"], accent=TEAL, body_size=13)
    card(s, 4.7, 5.05, 3.9, 1.7, "Graduation", ["candidate passed **every** rep", "baseline result ignored"], accent=GREEN, body_size=13)
    card(s, 8.8, 5.05, 3.95, 1.7, "Phase 2", ["graduated tasks as **regression**", "+ new capability `caller-check`"], accent=BLUE, body_size=13)

    # ------------------------------------------------------------ graduation
    s = d.content("Graduation: when a capability becomes a regression gate", "`pass_hat_k()` is a strict rule: **all candidate reps must pass**",
                  notes="promote_capability_tasks looks only at candidate passes for capability tasks. It needs at least REPS reps, and pass_hat_k returns 1.0 only when successes are at least k, which is 2. "
                        "In a live run the registry is updated with a timestamp and run id. In a dry run the list is only returned.")
    flow_row(s, 0.6, 1.85, ["Capability task", "≥ 2 reps?", "2 / 2 candidate passes?", "Not already regression?", "Move to regression"],
             2.08, 0.8, [SOFT, AMBER_L, AMBER_L, AMBER_L, GREEN_L], [INK, AMBER, AMBER, AMBER, GREEN], size=12.5, gap=0.44)
    code(s, 0.6, 3.0, 5.9, 2.0, ["def pass_hat_k(n, successes, k):", "    if n < k or successes < k:", "        return 0.0", "    return 1.0", "",
                                 "# promote: k = min(min_reps, len(passes)) = 2"], size=12, title="src/eval/compare.py · promote.py")
    card(s, 0.6, 5.2, 5.9, 1.55, "Persisted (live runs only)",
         "`suite: regression`, `graduated_utc`, `graduated_from_run` in `tasks/registry.yaml`", accent=TEAL, bullets=False, body_size=13)
    ga = ev.row("good", 1, "auth-vs-log").get("candidate_passes") or []
    ba = ev.row("bad", 1, "auth-vs-log").get("candidate_passes") or []
    box(s, 6.8, 3.0, 5.95, 1.75, fill=GREEN_L, line=None)
    text(s, 7.0, 3.1, 5.6, 0.4, "**Good candidate · auth-vs-log**", size=15, color=GREEN)
    text(s, 7.0, 3.55, 5.6, 1.1, f"candidate passes `{ga}` → **promoted** = {g_prom} → becomes a regression gate in Phase 2", size=13.5, color=INK2, mono_color=GREEN)
    box(s, 6.8, 5.0, 5.95, 1.75, fill=RED_L, line=None)
    text(s, 7.0, 5.1, 5.6, 0.4, "**Bad candidate · auth-vs-log**", size=15, color=RED)
    text(s, 7.0, 5.55, 5.6, 1.1, f"candidate passes `{ba}` → **not promoted**, promoted = {b_prom} → gate test 3 would block too", size=13.5, color=INK2, mono_color=RED)

    # ------------------------------------------------------------ blocking
    s = d.content("Blocking: the three tests in phase2_blocked_reason()", "Checked **in code order**; the first failing test wins and Phase 2 never runs",
                  notes="Tests 1 and 2 run inside one loop over Phase 1 comparison rows. Test 3 runs after the loop. In the bad story the auth-vs-log row is UNCHANGED, so the loop moves on and the keep-suite row fails test 1.")
    rows = [["#", "Test performed", "Result that fails", "What happens next"],
            ["1", "Any comparison row with `transition == REGRESSED`?", "baseline PASS → candidate FAIL", "Block: \"regression task X regressed (PASS→FAIL)\""],
            ["2", "Any **regression-suite** row with candidate outcome FAIL?", "candidate fails a gate, even if baseline also fails", "Block: \"regression task X candidate failed\""],
            ["3", "Is the `promoted` list empty?", "no capability task graduated", "Block: \"capability graduation gate not met…\""],
            ["OK", "All three pass", "n/a", "`return None` → `phase2_eligible() = True` → Phase 2 runs"]]
    table(s, 0.6, 1.8, W - 1.2, rows, [0.5, 4.3, 3.4, 3.93], size=13, row_h=0.62, cell_fills={(4, 3): GREEN_L})
    box(s, 0.6, 5.1, 6.0, 1.65, fill=RED_L, line=None)
    text(s, 0.8, 5.18, 5.6, 0.4, "**Bad candidate → blocked at test 1**", size=15, color=RED)
    text(s, 0.8, 5.6, 5.6, 1.1, f"`{b_reason}`", size=13, color=INK2, mono_color=RED)
    box(s, 6.75, 5.1, 6.0, 1.65, fill=GREEN_L, line=None)
    text(s, 6.95, 5.18, 5.6, 0.4, "**Good candidate → all tests pass**", size=15, color=GREEN)
    text(s, 6.95, 5.6, 5.6, 1.1, f"no REGRESSED row · keep-suite PASS · promoted = {g_prom} → Phase 2 ran: **{ev.good.get('phase_2_ran')}**",
         size=13, color=INK2, mono_color=GREEN)

    # ------------------------------------------------------------ graders
    s = d.content("Grader families: code decides, model and human inform", "**model grader result ≠ authoritative trial PASS**. Only `code_pass` flows into compare, promote and the gate.",
                  notes="Two code graders gate everything. The model rubric is evidence and produces a disagreement signal. The human spot-check is a calibration checklist that gates nothing.")
    gr = [("Code · held-out JSON", "auth-vs-log, caller-check", "Per-function labels from `heldout/expected.json`; optional `issue_contains`", "AUTHORITATIVE", GREEN, GREEN_L),
          ("Code · visible pytest", "keep-suite", "`pytest -q tests` in the post-agent workspace; exit 0 = PASS", "AUTHORITATIVE", GREEN, GREEN_L),
          ("Model rubric (LLM judge)", "auth-vs-log, caller-check", "One OpenRouter call, temperature 0; records `model_pass` + disagreement", "EVIDENCE ONLY", AMBER, AMBER_L),
          ("Human spot-check", "per scenario", "`human_spot_check.md`: 3 Y/N questions about candidate findings", "EVIDENCE ONLY", AMBER, AMBER_L)]
    for i, (t, used, how, tag, c, cl) in enumerate(gr):
        x = 0.6 + (i % 2) * 6.15
        y = 1.8 + (i // 2) * 1.85
        box(s, x, y, 5.95, 1.7, fill=SOFT, line=None)
        text(s, x + 0.2, y + 0.12, 3.9, 0.4, f"**{t}**", size=16, color=INK)
        pill(s, x + 5.95 - 1.75, y + 0.16, tag, cl, c, w=1.55, size=10.5)
        text(s, x + 0.2, y + 0.58, 5.5, 0.35, f"**Used for:** {used}", size=13, color=INK2)
        text(s, x + 0.2, y + 0.95, 5.5, 0.7, how, size=13, color=INK2)
    box(s, 0.6, 5.6, W - 1.2, 1.15, fill=DARK, line=None)
    text(s, 0.9, 5.68, 11.5, 1.0, ["**graders.py L158:**  `out[\"pass\"] = code[\"code_pass\"]`",
                                   "compare_task(), promote_capability_tasks() and phase2_blocked_reason() read only `trial[\"pass\"]`"],
         size=15, color=WHITE, mono_color=MINT)

    # ============================================================ CH 5
    d.divider("5", "Results & verdict", "What each candidate did against the same baseline, and what would have shipped on gut feeling",
              notes="Chapter 5: the evidence from the committed runs.")

    # ------------------------------------------------------------ bad results
    s = d.content("Bad candidate vs baseline: blocked in Phase 1",
                  f"Phase 1 verdict **{b1.get('verdict')}** · improved {b1.get('improved')} · regressed **{b1.get('regressed')}** · promoted **none** · Phase 2 **never runs**",
                  notes="Walk the table. On auth-vs-log both arms fail, for different reasons: the baseline over-flags logTransfer, the candidate drops withdraw entirely. "
                        "On keep-suite the baseline passes and the candidate breaks the tests: REGRESSED. The held-out grader caught the first and pytest caught the second. The gate blocks.")
    ra, rk = ev.row("bad", 1, "auth-vs-log"), ev.row("bad", 1, "keep-suite")
    gba, gca = ev.grade("bad", 1, "baseline", "auth-vs-log"), ev.grade("bad", 1, "candidate", "auth-vs-log")
    rows = [["Task", "Baseline identified", "Candidate identified", "Expected", "Transition"],
            ["auth-vs-log", f"withdraw flagged + logTransfer flagged (FP)\n{Evidence.reps(ra.get('baseline_passes') or [])}",
             f"only logTransfer; **withdraw missing**\n{Evidence.reps(ra.get('candidate_passes') or [])}", "withdraw: true\nlogTransfer: false", ra.get("transition", "")],
            ["keep-suite", f"no edits; tests green\n{Evidence.reps(rk.get('baseline_passes') or [])}",
             f"config rewritten 99.0.0 / 0\n{Evidence.reps(rk.get('candidate_passes') or [])}", "pytest passes", rk.get("transition", "")]]
    table(s, 0.6, 1.8, W - 1.2, rows, [1.6, 3.2, 3.3, 2.2, 1.83], size=12.5, row_h=0.78,
          cell_fills={(1, 4): SOFT, (2, 4): RED_L, (2, 2): RED_L, (1, 2): RED_L})
    card(s, 0.6, 4.35, 4.0, 2.4, "Which grader caught it",
         [f"held-out JSON: `{gca.get('code_reason')}`", "pytest: `assert 0 == 3`, API_VERSION `'99.0.0'`"], accent=TEAL, body_size=12.5)
    card(s, 4.75, 4.35, 4.0, 2.4, "The judge was fooled",
         [f"model rubric on candidate: **{'PASS' if gca.get('model_pass') else 'FAIL'}** ×2", "authoritative code verdict: **FAIL**",
          f"model_disagreements = {ra.get('model_disagreements')}"], accent=AMBER, body_size=12.5)
    card(s, 8.9, 4.35, 3.85, 2.4, "Consequence",
         ["capability not graduated", "gate test 1: keep-suite REGRESSED", "**Phase 2 blocked**, caller-check never runs"], accent=RED, body_size=12.5)

    # ------------------------------------------------------------ good results
    s = d.content("Good candidate vs baseline: graduates, passes Phase 2",
                  f"Phase 1 **{g1.get('verdict')}** → promoted **{', '.join(g_prom)}** → Phase 2 **{g2.get('verdict')}** · {g2.get('improved')} improved · {g2.get('regressed')} regressed",
                  notes="Phase 1: the candidate fixes the false positive and keeps withdraw, so auth-vs-log improves while keep-suite stays green. auth-vs-log graduates. "
                        "Phase 2: auth-vs-log holds as a regression gate, caller-check improves because the skill generalises, keep-suite unchanged.")
    rows = [["Phase", "Task", "Suite", "Baseline", "Candidate", "Transition"]]
    fills = {}
    for ph, task in ((1, "auth-vs-log"), (1, "keep-suite"), (2, "auth-vs-log"), (2, "caller-check"), (2, "keep-suite")):
        r = ev.row("good", ph, task)
        rows.append([str(ph), task, r.get("suite", ""), r.get("baseline_outcome", ""), r.get("candidate_outcome", ""), r.get("transition", "")])
        i = len(rows) - 1
        for c, v in ((3, r.get("baseline_outcome")), (4, r.get("candidate_outcome")), (5, r.get("transition"))):
            fills[(i, c)] = GREEN_L if v in ("PASS", "IMPROVED") else RED_L if v in ("FAIL", "REGRESSED") else SOFT
    table(s, 0.6, 1.8, 7.4, rows, [0.8, 1.6, 1.4, 1.1, 1.2, 1.3], size=12.5, row_h=0.5, cell_fills=fills, bold_first=False)
    gfa = ev.findings("good", 1, "candidate", "auth-vs-log")
    gfc = ev.findings("good", 2, "candidate", "caller-check")
    card(s, 8.3, 1.8, 4.45, 3.0, "What the candidate identified",
         [f"`{f.get('function')}` → {str(f.get('vulnerable')).lower()}: \"{f.get('detail')}\"" for f in gfa + gfc],
         accent=GREEN, body_size=12.5)
    card(s, 0.6, 5.0, 3.95, 1.75, "Grader result", "held-out labels match on every candidate rep; pytest green", accent=TEAL, bullets=False, body_size=13)
    card(s, 4.7, 5.0, 3.6, 1.75, "Promotion", f"auth-vs-log 2/2 → **regression**; gate returns None", accent=GREEN, bullets=False, body_size=13)
    card(s, 8.45, 5.0, 4.3, 1.75, "Honest caveat", f"caller-check model_disagreements = {ev.row('good', 2, 'caller-check').get('model_disagreements')} (mock-rule artefact); dry run, n = 2",
         accent=AMBER, bullets=False, body_size=13)

    # ------------------------------------------------------------ journey matrix
    s = d.content("The graduation / blocking journey, test by test", "The same tests run on both harnesses. Where they diverge decides **promote** or **block**.",
                  notes="Read down each column. The good candidate passes every check in order. The bad candidate fails the held-out check, fails pytest, regresses, is not promoted, and the gate blocks.")
    ra_b, rk_b = ev.row("bad", 1, "auth-vs-log"), ev.row("bad", 1, "keep-suite")
    ra_g, rk_g = ev.row("good", 1, "auth-vs-log"), ev.row("good", 1, "keep-suite")
    checks = [
        ("Phase 1 · auth-vs-log", "held-out JSON (code)", ra_g.get("candidate_outcome"), ra_b.get("candidate_outcome")),
        ("Phase 1 · keep-suite", "visible pytest (code)", rk_g.get("candidate_outcome"), rk_b.get("candidate_outcome")),
        ("Transition vs baseline", "compare_task()", f"{ra_g.get('transition')} / {rk_g.get('transition')}", f"{ra_b.get('transition')} / {rk_b.get('transition')}"),
        ("Graduation", "pass_hat_k (2/2)", "PROMOTED", "NO"),
        ("Gate test 1 · REGRESSED?", "phase2_blocked_reason", "PASS", "FAIL"),
        ("Gate test 3 · promoted?", "phase2_blocked_reason", "PASS", "FAIL"),
        ("Phase 2 · caller-check", "held-out JSON (code)", ev.row("good", 2, "caller-check").get("candidate_outcome"), "NOT RUN"),
    ]
    text(s, 0.6, 1.75, 4.0, 0.4, "**Check**", size=13, color=MUTED)
    text(s, 4.55, 1.75, 2.8, 0.4, "**Grader / function**", size=13, color=MUTED)
    text(s, 7.6, 1.75, 2.4, 0.4, "**Good candidate**", size=13, color=GREEN)
    text(s, 10.3, 1.75, 2.4, 0.4, "**Bad candidate**", size=13, color=RED)
    for i, (t, gname, gv, bv) in enumerate(checks):
        y = 2.2 + i * 0.6
        box(s, 0.6, y, W - 1.2, 0.52, fill=SOFT if i % 2 == 0 else WHITE, line=None, radius=0.15)
        text(s, 0.75, y, 3.8, 0.52, f"**{t}**", size=13, color=INK, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 4.55, y, 3.0, 0.52, gname, size=12.5, color=INK2, anchor=MSO_ANCHOR.MIDDLE)
        for x, v in ((7.6, gv), (10.3, bv)):
            if "/" in str(v):
                text(s, x, y, 2.6, 0.52, f"**{v}**", size=12, color=GREEN if x < 10 else RED, anchor=MSO_ANCHOR.MIDDLE)
            else:
                verdict_pill(s, x, y + 0.11, v, w=1.6, size=11)
    box(s, 7.45, 6.45, 2.6, 0.45, fill=GREEN, line=None, radius=0.3)
    text(s, 7.45, 6.45, 2.6, 0.45, "**→ PROMOTE**", size=14, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    box(s, 10.15, 6.45, 2.6, 0.45, fill=RED, line=None, radius=0.3)
    text(s, 10.15, 6.45, 2.6, 0.45, "**→ BLOCK**", size=14, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # ------------------------------------------------------------ final verdict
    s = d.dark(notes="The verdict. The good candidate is promotable within the scope of this PoC: no regressions and stable capability wins across two phases. "
                     "The bad candidate is rejected because it breaks a passing suite and loses the real finding. Both sounded like stricter security.")
    text(s, 0.6, 0.45, 12, 0.7, "**Final verdict: same baseline, opposite outcomes**", size=32, color=WHITE)
    text(s, 0.6, 1.12, 12, 0.45, "Production readiness **within this PoC's scope** (dry-run evidence, n = 2)", size=16, color="B6C3DA")
    for x, ttl, verdict, colr, items in (
        (0.6, "Good candidate · triage skill", "PROMOTE", GREEN, [
            f"auth-vs-log: **{ra_g.get('baseline_outcome')} → {ra_g.get('candidate_outcome')}** (IMPROVED)",
            f"keep-suite: **{rk_g.get('candidate_outcome')}** both phases, no regression",
            f"Graduated: **{', '.join(g_prom)}** → regression gate",
            f"Phase 2: **{g2.get('verdict')}**, caller-check {ev.row('good', 2, 'caller-check').get('transition')}",
            "Ready for a wider live trial"]),
        (6.8, "Bad candidate · remediation skill", "REJECT", RED, [
            f"auth-vs-log: **{ra_b.get('candidate_outcome')}**, withdraw missing",
            f"keep-suite: **{rk_b.get('baseline_outcome')} → {rk_b.get('candidate_outcome')}** (REGRESSED)",
            "Graduated: **none**",
            "Phase 2: **blocked** at gate test 1",
            "Would have broken services in production"])):
        box(s, x, 1.8, 5.95, 3.45, fill=DARK2, line="23314F")
        text(s, x + 0.3, 1.95, 4.0, 0.45, f"**{ttl}**", size=17, color=WHITE)
        shp = box(s, x + 4.15, 1.95, 1.55, 0.5, fill=colr, line=None, radius=0.4)
        label_in(shp, f"**{verdict}**", size=14, color=WHITE)
        text(s, x + 0.3, 2.75, 5.4, 2.95, items, size=17, color="D5DEEE", bullets=True, bullet_color=MINT if colr == GREEN else "F87171", space_after=10)
    text(s, 0.6, 5.6, W - 1.2, 0.7,
         "Both skills **sound** like stricter security. Only the **held-out labels**, **pytest** and the **gate** told them apart.",
         size=17, color=MINT, align=PP_ALIGN.CENTER)

    # ------------------------------------------------------------ gut feeling counterfactual
    s = d.content("What if we had shipped on gut feeling?", "**Hypothetical counterfactual.** Both skills read as \"stricter security\" in a design review.",
                  notes="Tell the counterfactual. Without paired evidence, the bad skill could easily be the one that ships, since it sounds the most security-minded. "
                        "It would rewrite config constants in real services and drop the real authorization finding, and the team would struggle to attribute the incidents. "
                        "With the evaluation, it was blocked in Phase 1 for zero dollars in a dry run.")
    pill(s, 0.6, 1.75, "HYPOTHETICAL · ILLUSTRATES THE COST OF NO EVIDENCE", VIOLET_L, VIOLET, size=11)
    tl = [("Design review", "\"Never leave tx.origin in production\" wins the room: it sounds the strictest."),
          ("Rollout", "Every engineer's agent gets the skill. No baseline, no gate."),
          ("Week 1", "Agents \"harden\" config: versions bumped, retries set to 0 in real services."),
          ("Week 2", "Audits list what was changed, not what is vulnerable. Real auth bugs slip through."),
          ("Incident", "Outages and a missed exploit. Nobody can tell whether the skill, the model or the code caused it.")]
    for i, (t, b) in enumerate(tl):
        x = 0.6 + i * 2.45
        circle(s, x + 0.95, 2.25, 0.45, str(i + 1), fill=RED if i >= 2 else AMBER, size=13)
        box(s, x, 2.85, 2.3, 2.1, fill=RED_L if i >= 2 else AMBER_L, line=None)
        text(s, x + 0.15, 2.95, 2.0, 0.4, f"**{t}**", size=14, color=RED if i >= 2 else AMBER)
        text(s, x + 0.15, 3.35, 2.0, 1.55, b, size=12.5, color=INK2)
    box(s, 0.6, 5.2, W - 1.2, 1.55, fill=GREEN_L, line=None)
    text(s, 0.9, 5.3, 11.6, 0.4, "**What actually happened with evidence**", size=16, color=GREEN)
    text(s, 0.9, 5.72, 11.6, 1.0,
         f"Blocked in **Phase 1**, before any rollout: `{b_reason}`. Cost of finding out: **${b1.get('total_cost_usd', 0):.2f}** (dry run), "
         "and the cause is attributable to **one changed file**.", size=14, color=INK2, mono_color=GREEN)

    # ============================================================ CH 6
    d.divider("6", "What we cut, and why", "The core is built. The workflow around designing, validating and iterating on evals is not, and the cut was deliberate.",
              notes="Chapter 6: honest scope. Seven gaps compared with Anthropic's build-eval and hillclimb workflows.")

    # ------------------------------------------------------------ gaps overview
    s = d.content("The core is built; the workflow around it is cut", "We built **run + grade + compare + gate**. The gaps are about **designing, validating and iterating** on evals.",
                  notes="Frame it carefully: these are not missing core functionality. The repo already does controlled baseline-vs-candidate evaluation with deterministic grading, held-out answers and regression protection. "
                        "The gaps are the workflow around that core.")
    core = box(s, 2.3, 3.55, 2.9, 1.3, fill=DARK, line=None)
    label_in(core, ["**BUILT · the core**", "Run + Grade + Compare + Gate"], size=14, color=WHITE)
    around = [("Design", "Gap 1", 2.3, 1.85, 2.9, BLUE_L, BLUE), ("Validate", "Gaps 2 · 3", 0.6, 3.55, 1.5, AMBER_L, AMBER),
              ("Iterate", "Gaps 5 · 6 · 7", 5.4, 3.55, 1.6, VIOLET_L, VIOLET), ("Demo / UX", "Gap 4", 2.3, 5.25, 2.9, TEAL_L, TEAL)]
    for t, g, x, y, w, f, c in around:
        shp = box(s, x, y, w, 1.3 if w > 2 else 1.3, fill=f, line=None)
        label_in(shp, [f"**{t}**", g], size=14, color=c)
    rows = [["#", "Gap", "Area", "Doc priority"], ["1", "Eval design workflow", "Design", "demo scope"],
            ["2", "Grader validation ritual", "Validate", "**P1**"], ["3", "Baseline / headroom / noise", "Validate", "**P2**"],
            ["4", "Local HTML results browser", "Demo / UX", "**P1**"], ["5", "Hill-climb iteration loop", "Iterate", "P2 holdout · P3"],
            ["6", "Cost / latency objective", "Iterate", "future"], ["7", "Failure bucketing", "Iterate", "optional"]]
    table(s, 7.35, 1.85, 5.4, rows, [0.4, 2.6, 1.15, 1.25], size=12.5, row_h=0.6, bold_first=False)

    gaps = [
        ("Gap 1 · No guided \"design the eval\" workflow", "Design",
         "Adding an eval means hand-editing YAML, Python, tasks, expected answers and graders. Everyone does it differently.",
         ["Engineer", "Create task by hand", "Write expected answer", "Write grader", "Run"],
         ["\"Eval for this failure\"", "Define task", "Acceptance criteria", "Choose grader", "Review → approve → run"],
         ["Only **3 hand-built tasks** exist; a guided flow pays off with many contributors", "The task format is already minimal: `prompt.txt` + `repo/` + `heldout/`, about 3 files",
          "Time went into **grader and gate correctness** first"],
         "`docs/eval-design-checklist.md` or `python -m eval.design` + a registry schema validator"),
        ("Gap 2 · No grader validation ritual", "Validate",
         "Nobody checks that the grader agrees with a human, or gives the same answer twice on identical output. A bad grader makes a bad harness look good.",
         ["Agent", "Output", "Grader", "Score (trusted?)"],
         ["Sample outputs", "Human grades them", "Run grader twice", "Flag flips", "Then trust verdict"],
         ["Gating graders are **deterministic code**, so flakiness risk is low", "Graders have **unit tests** (`tests/test_graders.py`)",
          "The only non-deterministic grader (LLM) **cannot change a verdict**"],
         "`python -m eval.validate-grader --task auth-vs-log` + a run-twice check in `e2e_validate.sh`"),
        ("Gap 3 · No baseline score, headroom or noise diagnostics", "Validate",
         "2/2 vs 2/2 could be genuine or two easy runs. 100% vs 100% leaves no room to show improvement. 80% vs 85% may be noise.",
         ["Baseline 2/2", "Candidate 2/2", "\"Better?\"", "Unknown"],
         ["Pass rate per arm", "Count UNSTABLE", "Headroom warning", "\"Low n\" banner"],
         ["**n = 2 cannot support confidence intervals**; fake statistics would be dishonest", "We already report **UNSTABLE** and never round it into a win",
          "Limits are stated explicitly in README and DESIGN"],
         "`diagnostics` block in phase summary + `headroom_warning` when baseline is already 100%"),
        ("Gap 4 · No local results browser", "Demo / UX",
         "Evidence lives in READMEs, JSON files and transcripts, so a live demo becomes \"let me open this folder… now this JSON…\".",
         ["Open README", "Find folder", "Open JSON", "Find transcript"],
         ["index.html", "Task → score", "Click → findings", "Click → grade + transcript"],
         ["A **usability** gap, not an evaluation capability", "Markdown READMEs + `comparison/result.json` + this deck cover the demo",
          "`archify/index.html` now gives a visual walkthrough"],
         "`python -m eval.report_html` → `output/<example>/index.html`"),
        ("Gap 5 · No automated harness iteration loop (hill-climb)", "Iterate",
         "The tool compares baseline vs one candidate, but a human decides every next change. There is no train/holdout split to catch overfitting.",
         ["Human idea", "Edit AGENTS.md", "Run eval", "Human decides next"],
         ["Change", "Train eval ↑?", "Holdout eval ↑?", "Keep or revert", "Next change"],
         ["Auto-editing a harness **risks overfitting** and is hard to audit in a take-home", "The **compare step is the prerequisite**, and that is what we built",
          "A human loop already works: edit → `python -m eval` → read comparison"],
         "Registry split `capability-train` / `capability-holdout`; later an approved-patch CLI"),
        ("Gap 6 · No cost / latency optimisation objective", "Iterate",
         "Cost is recorded per trial but never optimised. Same pass rate at 40% lower cost is a real win the tool cannot surface.",
         ["Accuracy only", "Cost logged", "Not compared"],
         ["Accuracy ≥ baseline", "Cost ↓", "Latency ↓", "Report the delta"],
         ["**One variable by design**: the model is fixed, so cost differences are small", "Dry runs cost **$0**, so there is no signal to optimise in committed runs",
          "`cost_usd` and `total_cost_usd` are already captured"],
         "Per-phase cost delta between arms in `summary.json`; later a model / effort sweep"),
        ("Gap 7 · No failure bucketing when the score stalls", "Iterate",
         "When improvement stalls, someone reads every failed trial by hand. Not every failure means the harness is bad: some are bad tasks or grader bugs.",
         ["Score stalls", "Read every trial", "Guess the cause"],
         ["triage-failures", "Group by cause", "Task · grader · harness · agent", "Fix the right thing"],
         ["Today there are only **a handful of failure reasons**", "`grade.json` `code_reason` already explains every failure precisely",
          "Bucketing pays off at **scale**, with many tasks"],
         "`python -m eval.triage-failures --example good-harness-example` grouping by `code_reason`"),
    ]
    for title, area, problem, today, desired, why, nxt in gaps:
        s = d.content(title, f"**{area}** · {problem}",
                      notes=f"{title}. Problem: {problem} Today versus desired is shown in the two flows. Why we cut it: " + " ".join(re.sub(r'[*`]', '', w) for w in why) + f" Next step: {re.sub(r'[`]', '', nxt)}.")
        text(s, 0.6, 2.0, 2.0, 0.32, "**TODAY**", size=12, color=RED)
        n = len(today)
        cw = (W - 1.2 - 0.38 * (n - 1)) / n
        flow_row(s, 0.6, 2.32, today, cw, 0.65, RED_L, RED, size=12.5, gap=0.38)
        text(s, 0.6, 3.12, 2.0, 0.32, "**DESIRED**", size=12, color=GREEN)
        n = len(desired)
        cw = (W - 1.2 - 0.38 * (n - 1)) / n
        flow_row(s, 0.6, 3.44, desired, cw, 0.65, GREEN_L, GREEN, size=12.5, gap=0.38)
        card(s, 0.6, 4.35, 7.4, 2.45, "Why we cut it", why, accent=AMBER, body_size=13.5)
        card(s, 8.2, 4.35, 4.55, 2.45, "Next step (planned)", nxt, accent=TEAL, bullets=False, body_size=13.5)

    # ------------------------------------------------------------ how to run
    d.section = "Run it yourself"
    s = d.content("Run it on your machine", "No API key needed for the dry run. A live run needs an **OpenRouter key** and costs at most **$0.05 per trial**.",
                  notes="Walk the steps. The dry run reproduces the committed output exactly. For a live run, create a key at openrouter.ai/keys, export it, reset the registry, then run the good scenario. "
                        "Results live under output/<example>/. Start from summary.json, then comparison/README.md, then individual trials.")
    steps = [("1", "Install (Python ≥ 3.10)", ["python3 -m venv .venv", "source .venv/bin/activate", "pip install -e \".[dev]\""]),
             ("2", "OpenRouter API key (live runs only)", ["# create a key at https://openrouter.ai/keys", "export OPENROUTER_API_KEY=sk-or-...", "export OPENROUTER_MODEL=<model-id>   # optional"]),
             ("3", "Run", ["python3 -m eval --dry-run              # both stories, $0", "python3 -m eval --dry-run --scenario bad", "cp tasks/registry.bootstrap.yaml tasks/registry.yaml", "python3 -m eval --scenario good          # live"]),
             ("4", "Verify + rebuild", ["pytest -q", "bash scripts/e2e_validate.sh", "python3 presentation/src/build_deck.py"])]
    for i, (n, t, lines) in enumerate(steps):
        x = 0.6 + (i % 2) * 6.15
        y = 1.8 + (i // 2) * 1.82
        code(s, x, y, 5.95, 1.68, lines, size=11, title=f"{n} · {t}")
    card(s, 0.6, 5.42, 6.0, 1.42, "View the results",
         ["`output/summary.json` → `…/phase-1/comparison/README.md`", "`…/trials/<task>/<rep>/`: findings, grade, transcript, cost"],
         accent=TEAL, body_size=12.5)
    card(s, 6.75, 5.42, 6.0, 1.42, "Visual explanations",
         ["`archify/index.html`: 22-step narrative + 15 diagrams", "Every diagram node links to `file:line` in the source"],
         accent=VIOLET, body_size=12.5)

    # ------------------------------------------------------------ closing
    s = d.dark(notes="Close on the three ideas: change one variable, let deterministic code decide, and make Phase 2 something a candidate earns. Then invite questions.")
    text(s, 0.8, 0.9, 11.5, 0.5, "KEY TAKEAWAYS", size=14, color=MINT, bold=True)
    text(s, 0.8, 1.35, 11.5, 1.0, "**Evaluate the harness change, not the vibe**", size=40, color=WHITE)
    tk = [("1", "One variable", "Same model, tools, prompt and graders. **Only the guidance file differs**, so any delta is attributable."),
          ("2", "Code decides", "Held-out JSON and pytest gate everything. **The LLM judge is evidence**; it was fooled once and logged."),
          ("3", "Phase 2 is earned", "Capability wins must hold on **every rep**, and **any regression blocks** the next phase.")]
    for i, (n, t, b) in enumerate(tk):
        x = 0.8 + i * 4.0
        box(s, x, 2.85, 3.75, 3.0, fill=DARK2, line="23314F")
        circle(s, x + 0.25, 3.05, 0.6, n, fill=TEAL, size=18)
        text(s, x + 0.25, 3.8, 3.3, 0.5, f"**{t}**", size=20, color=WHITE)
        text(s, x + 0.25, 4.35, 3.3, 1.4, b, size=14, color="D5DEEE")
    text(s, 0.8, 6.15, 11.5, 0.5,
         f"Good candidate → **graduated**, Phase 2 {g2.get('verdict')}  ·  Bad candidate → **blocked**: {b_reason}", size=14, color="B6C3DA")

    return d.prs


def main() -> None:
    project = root()
    prs = build(project)
    out_dir = project / "presentation" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "harness-eval.pptx"
    prs.save(str(out_path))
    print(f"wrote {out_path} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
