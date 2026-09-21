#!/usr/bin/env python3
"""
CV Generator — produces 4 DOCX variants from CV_HOLISTIC_MASTER.md
Run: python3 generate_cvs.py

Output:
  - CV_Tayyaba_Rizwan_AI_Engineer_Master.docx
  - CV_Tayyaba_Rizwan_ML_Engineer_Master.docx
  - CV_Tayyaba_Rizwan_DataScientist_Master.docx
  - CV_Tayyaba_Rizwan_Holistic_Master.docx (full reference)
"""

import re, os, sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Load and parse master spec ──────────────────────────────────────────────
# Resolve CV_HOLISTIC_MASTER.md relative to this script. The script is
# relocatable: it searches upward from the script dir so it works both
# when installed inside the skill repo (scripts/ subdir) and when run from
# the workspace root. Override with CV_SOURCE_PATH env var if needed.
SCRIPT_DIR = Path(__file__).resolve().parent
_CV_SOURCE_ENV = os.environ.get("CV_SOURCE_PATH")
if _CV_SOURCE_ENV:
    CV_SOURCE = Path(_CV_SOURCE_ENV)
else:
    # Look for CV_HOLISTIC_MASTER.md upward from the script location,
    # then in common workspace locations. Override with CV_SOURCE_PATH.
    CV_SOURCE = None
    # Phase 1: walk up from the script's directory
    for _d in [SCRIPT_DIR] + list(SCRIPT_DIR.parents):
        _candidate = _d / "CV_HOLISTIC_MASTER.md"
        if _candidate.exists():
            CV_SOURCE = _candidate
            break
    # Phase 2: check well-known workspace locations
    if CV_SOURCE is None:
        for _candidate in [
            Path.home() / "vestwell_contact_center" / "CV_HOLISTIC_MASTER.md",
            Path.home() / "vestwell" / "CV_HOLISTIC_MASTER.md",
            Path.home() / "CV_HOLISTIC_MASTER.md",
        ]:
            if _candidate.exists():
                CV_SOURCE = _candidate
                break
    if CV_SOURCE is None:
        raise FileNotFoundError(
            "CV_HOLISTIC_MASTER.md not found. Place it alongside generate_cvs.py, "
            "in ~/vestwell_contact_center/, or set CV_SOURCE_PATH env var."
        )
with open(CV_SOURCE) as f:
    content = f.read()

# Parse sections (## Section headers)
sections = {}
current_section = None
current_lines = []

for line in content.split('\n'):
    if line.startswith('## ') and not line.startswith('### '):
        if current_section:
            sections[current_section] = '\n'.join(current_lines)
        current_section = line[3:].strip()
        current_lines = []
    elif current_section:
        current_lines.append(line)

if current_section:
    sections[current_section] = '\n'.join(current_lines)

# ── Colors ───────────────────────────────────────────────────────────────────
DARK_BLUE = RGBColor(0x1F, 0x4E, 0x79)
MED_BLUE = RGBColor(0x44, 0x72, 0xC4)
LIGHT_BLUE = RGBColor(0x2E, 0x75, 0xB6)
BLACK = RGBColor(0x00, 0x00, 0x00)
DARK_GRAY = RGBColor(0x33, 0x33, 0x33)
ACCENT = RGBColor(0xC0, 0x39, 0x2B)  # red accent for metrics

# ── Markdown stripper ────────────────────────────────────────────────────────
def strip_md(text):
    """Strip all markdown formatting, return clean plain text."""
    # code spans: `code` -> code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # bold: **text** -> text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # italic: *text* -> text
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # horizontal rules: --- or ***
    text = re.sub(r'^[-*]{3,}', '', text)
    # heading markers: #### text -> text (bold)
    text = re.sub(r'^#{4}\s+', '', text)
    text = re.sub(r'^#{3}\s+', '', text)
    text = re.sub(r'^#{2}\s+', '', text)
    # bullet markers: - text or * text
    text = re.sub(r'^[-*]\s+', '', text)
    # trailing whitespace
    text = text.strip()
    return text

def split_md_paragraphs(section_text):
    """Split section text into paragraphs, handling multi-line bullets."""
    paragraphs = []
    current_para = []
    in_bullet = False

    for line in section_text.split('\n'):
        stripped = line.strip()

        if not stripped:
            if current_para:
                paragraphs.append('\n'.join(current_para))
                current_para = []
                in_bullet = False
            continue

        # Detect bullets
        is_bullet = stripped.startswith('- ') or stripped.startswith('* ')
        is_code_block = stripped.startswith('```')

        if is_code_block:
            if current_para:
                paragraphs.append('\n'.join(current_para))
                current_para = []
            continue

        if is_bullet and not in_bullet:
            # New bullet list starts — flush any pending paragraph
            if current_para and not in_bullet:
                paragraphs.append('\n'.join(current_para))
                current_para = []
            in_bullet = True
            current_para.append(strip_md(stripped))
        elif is_bullet and in_bullet:
            # Continuation of bullet
            current_para.append(strip_md(stripped))
        elif not is_bullet and in_bullet:
            # Bullet list ended — flush bullets as a single paragraph block
            paragraphs.append('\n'.join(current_para))
            current_para = []
            in_bullet = False
            current_para.append(strip_md(stripped))
        else:
            current_para.append(strip_md(stripped))

    if current_para:
        paragraphs.append('\n'.join(current_para))

    return [p for p in paragraphs if p.strip()]

def split_bullet_items(section_text):
    """Extract individual bullet items from a section. Only actual '-' or '*' lines become items.
    Non-bullet lines are ignored (they're handled by parse_paragraphs)."""
    items = []
    current_item = []
    in_item = False

    for line in section_text.split('\n'):
        stripped = line.strip()

        if not stripped:
            if current_item:
                items.append(' '.join(current_item))
                current_item = []
                in_item = False
            continue

        is_bullet = stripped.startswith('- ') or stripped.startswith('* ')

        if is_bullet:
            if current_item:
                items.append(' '.join(current_item))
            current_item = [strip_md(stripped)]
            in_item = True
        elif in_item:
            # Continuation line of a bullet (indented or just text)
            current_item.append(strip_md(stripped))
        # else: non-bullet line outside a bullet — IGNORE (handled by parse_paragraphs)

    if current_item:
        items.append(' '.join(current_item))

    return items

# ── DOCX builders ────────────────────────────────────────────────────────────
def md_to_runs(doc, text, size=10, color=BLACK):
    """
    Add a paragraph rendering markdown: **bold** → bold runs, `code` → monospace.
    Plain text stays normal.
    """
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(1)

    # Split into tokens: **bold**, `code`, or plain
    tokens = re.split(r'(\*\*.*?\*\*|\`.*?\`)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith('**') and token.endswith('**'):
            run = p.add_run(token[2:-2])
            run.bold = True
        elif token.startswith('`') and token.endswith('`'):
            run = p.add_run(token[1:-1])
            run.font.name = 'Courier New'
            run.font.size = Pt(size - 1)
            run.font.color.rgb = DARK_GRAY
        else:
            run = p.add_run(token)
        run.font.name = 'Calibri'
        run.font.size = Pt(size)
        run.font.color.rgb = color
    return p

def add_styled_para(doc, text, font_name='Calibri', size=10, bold=False, color=BLACK, italic=False, alignment=None):
    """Add a paragraph with optional alignment. Raw text only — **bold** and `code` are rendered as Word formatting by md_to_runs()."""
    p = doc.add_paragraph()
    if alignment:
        p.alignment = alignment
    run = p.add_run(text)
    run.font.name = font_name
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color
    return p

def add_bullet(doc, text, size=10):
    """Add a bullet that renders **bold** and `code` as Word formatting."""
    p = doc.add_paragraph(style='List Bullet')
    p.clear()
    # Render markdown in the bullet text
    tokens = re.split(r'(\*\*.*?\*\*|\`.*?\`)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith('**') and token.endswith('**'):
            run = p.add_run(token[2:-2])
            run.bold = True
        elif token.startswith('`') and token.endswith('`'):
            run = p.add_run(token[1:-1])
            run.font.name = 'Courier New'
            run.font.size = Pt(size - 1)
            run.font.color.rgb = DARK_GRAY
        else:
            run = p.add_run(token)
        run.font.name = 'Calibri'
        run.font.size = Pt(size)
    return p

def add_header(doc, text, level=1):
    if level == 1:
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(14)
        run.bold = True
        run.font.color.rgb = DARK_BLUE
    elif level == 2:
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(12)
        run.bold = True
        run.font.color.rgb = MED_BLUE
    return p

def add_page_break(doc):
    doc.add_page_break()

def parse_bullet_list(section_text):
    items = []
    in_bullet = False
    for line in section_text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('- '):
            in_bullet = True
            items.append(stripped[2:])
        elif in_bullet and stripped and not stripped.startswith('- '):
            items.append(stripped)
        elif not stripped:
            in_bullet = False
    return items

def parse_paragraphs(section_text):
    paragraphs = []
    for line in section_text.split('\n'):
        s = line.strip()
        if not s:
            continue
        if s.startswith('- ') or s.startswith('* '):
            continue
        if s.startswith('###'):
            continue
        # Strip --- and #### markers
        if s.startswith('---') or s.startswith('***'):
            continue
        if s.startswith('#### '):
            s = s[5:]
        elif s.startswith('### '):
            s = s[4:]
        elif s.startswith('## '):
            s = s[3:]
        # Strip any remaining ** and ` from unbalanced markup
        s = s.replace('**', '').replace('`', '')
        if s:
            paragraphs.append(s)
    return paragraphs

def build_docx(variant_name, section_order, max_bullets_per_section=None):
    """
    Build a DOCX from the master spec.
    """
    doc = Document()
    
    # Page setup
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    
    # Name — loaded from .app_config.json (gitignored) for public-safety.
    # Falls back to env var or placeholder.
    _cfg_path = SCRIPT_DIR / ".app_config.json"
    _name = "TAYYABA RIZWAN"  # default; override via CV_NAME env or .app_config.json
    if _cfg_path.exists():
        try:
            _cfg = _json.loads(_cfg_path.read_text())
            _name = _cfg.get("candidate", {}).get("name", _name)
        except Exception:
            pass
    _name = os.environ.get("CV_NAME", _name)
    md_to_runs(doc, _name, size=22, color=DARK_BLUE)
    for r in doc.paragraphs[-1].runs:
        r.bold = True
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Role-specific subtitle
    role_map = {
        'AI_Engineer': 'Applied AI Engineer — Agentic AI, RAG, LLM Systems, Voice AI',
        'ML_Engineer': 'ML Engineer — Production ML Pipelines, MLOps, Databricks, LLM Engineering',
        'DataScientist': 'Data Scientist (AI/ML) — NLP, Predictive Modeling, KPI Engineering, BI',
        'Holistic': 'Applied AI Engineer — Enterprise AI • Voice AI • LLM Systems • Backend Engineering • Production AI'
    }
    md_to_runs(doc, role_map.get(variant_name, 'Applied AI Engineer'), size=11, color=MED_BLUE)
    doc.paragraphs[-1].runs[0].italic = True
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Contact line — loaded from .app_config.json (gitignored) so the script
    # is safe to publish. Falls back to env vars or a generic placeholder.
    cfg_path = SCRIPT_DIR / ".app_config.json"
    if cfg_path.exists():
        try:
            import json as _json
            _cfg = _json.loads(cfg_path.read_text())
            _c = _cfg.get("candidate", {})
            _loc = _c.get("location", "Dubai, UAE")
            _email = _c.get("email", "")
            _ln = _c.get("linkedin", "")
            _gh = _c.get("github", "")
            _parts = [f"{_loc} (UAE Resident — No Visa Sponsorship Required)"]
            if _email:
                _parts.append(_email)
            if _ln:
                _parts.append(f"LinkedIn: {_ln}")
            if _gh:
                _parts.append(f"GitHub: {_gh}")
            _contact_line = "  |  ".join(_parts)
        except Exception:
            _contact_line = os.environ.get(
                "CV_CONTACT_LINE",
                "Dubai, UAE (UAE Resident — No Visa Sponsorship Required)  |  [contact in .app_config.json]"
            )
    else:
        _contact_line = os.environ.get(
            "CV_CONTACT_LINE",
            "Dubai, UAE (UAE Resident — No Visa Sponsorship Required)  |  [contact in .app_config.json]"
        )
    md_to_runs(doc, _contact_line, size=10, color=LIGHT_BLUE)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    add_page_break(doc)
    
    # Process sections in order
    for section_name, _ in section_order:
        if section_name in sections:
            text = sections[section_name]
            add_header(doc, section_name.upper(), level=1)
            
            # Paragraphs (use md_to_runs for proper **bold**/code rendering)
            paragraphs = parse_paragraphs(text)
            for para in paragraphs:
                md_to_runs(doc, para, size=10)

            # Sub-sections and bullets
            sub_sections = re.split(r'\n### ', text)
            for sub in sub_sections[1:]:
                lines = sub.split('\n')
                sub_title = lines[0].strip()
                if sub_title:
                    add_header(doc, sub_title, level=2)

                    max_b = max_bullets_per_section.get(sub_title) if max_bullets_per_section else None

                    # Use the markdown-aware add_bullet (processes **bold** and `code`)
                    bullets = split_bullet_items('\n'.join(lines[1:]))
                    if max_b:
                        bullets = bullets[:max_b]
                    for b in bullets:
                        add_bullet(doc, b, size=10)
            
            add_page_break(doc)
    
    # Save
    # Determine output dir: env var > CLI arg > script-dir-relative default
    out_dir = Path(os.environ.get(
        "CV_OUTPUT_DIR",
        str(Path.home() / "vestwell_contact_center" / "applications" / "2026-09-18")
    ))
    os.makedirs(out_dir, exist_ok=True)
    filename = f'{out_dir}/CV_Tayyaba_Rizwan_{variant_name}_Master.docx'
    doc.save(filename)
    print(f'OK: {filename}')
    return filename

# ── Define variants ──────────────────────────────────────────────────────────

# 1. AI_Engineer — keep all content (comprehensive for ATS)
ai_order = [
    ('Professional Summary', True),
    ('Experience', True),
    ('Engineering Decisions', True),
    ('Core Competencies', True),
    ('Education', True),
    ('Certifications & Training', True),
    ('Scalable Impact Metrics', True),
    ('References', True),
]

# 2. ML_Engineer — keep all content
ml_order = [
    ('Professional Summary', True),
    ('Experience', True),
    ('Engineering Decisions', True),
    ('Core Competencies', True),
    ('Education', True),
    ('Certifications & Training', True),
    ('Scalable Impact Metrics', True),
    ('References', True),
]

# 3. DataScientist — keep all content
ds_order = [
    ('Professional Summary', True),
    ('Experience', True),
    ('Engineering Decisions', True),
    ('Core Competencies', True),
    ('Education', True),
    ('Certifications & Training', True),
    ('Scalable Impact Metrics', True),
    ('References', True),
]

# 4. Holistic — full reference with all details
holistic_order = [
    ('Professional Summary', True),
    ('Experience', True),
    ('Target Roles & JD Alignment', True),
    ('Engineering Decisions', True),
    ('Core Competencies', True),
    ('Education', True),
    ('Certifications & Training', True),
    ('Scalable Impact Metrics', True),
    ('References', True),
    ('ATS Keywords', True),
]

# Generate all 4
print('Generating CVs...')
build_docx('AI_Engineer', ai_order)
build_docx('ML_Engineer', ml_order)
build_docx('DataScientist', ds_order)
build_docx('Holistic', holistic_order)
print('DONE — 4 CVs generated')
