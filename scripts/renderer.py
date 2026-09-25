#!/usr/bin/env python3
"""
renderer.py — Job Application Document Renderer

Renders the final application artifacts from a matched JD + user CV:
  - CV_<Name>_<Role>_<Company>.docx  (tailored CV)
  - CoverLetter_<Company>_<Role>.docx (tailored cover letter)
  - README.md                         (role summary, fit, interview prep)
  - jd.xlsx                           (extracted JD archive)

Usage:
  python renderer.py \
    --cv-base /path/to/base_cv.docx \
    --jd-json /path/to/jd.json \
    --output-dir /path/to/company_folder \
    --company G42 \
    --role "AI Engineer" \
    --name "Your Name"

Returns JSON with paths to all generated files.
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import openpyxl
from openpyxl.styles import Font, PatternFill

# ── Load candidate config ────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    config = {}
    for config_name in (".app_config.json", "config_template.json"):
        config_path = os.path.join(SCRIPT_DIR, config_name)
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    config = json.load(f)
                if "candidate" in config:
                    return config["candidate"]
            except (json.JSONDecodeError, KeyError):
                pass
    return {
        "name": "Your Name",
        "email": "your.email@example.com",
        "phone": "+971****XXXX",
        "location": "City, Country",
        "linkedin": "linkedin.com/in/yourprofile",
        "github": "github.com/yourhandle",
    }


CANDIDATE = load_config()
NAME = CANDIDATE.get("name", "Your Name")
EMAIL = CANDIDATE.get("email", "your.email@example.com")
PHONE = CANDIDATE.get("phone", "+971****XXXX")
LOCATION = CANDIDATE.get("location", "City, Country")
LINKEDIN = CANDIDATE.get("linkedin", "linkedin.com/in/yourprofile")
GITHUB = CANDIDATE.get("github", "github.com/yourhandle")
TODAY = date.today().isoformat()
MARGIN_MM = 15.88
MARGIN_INCHES = MARGIN_MM / 25.4


# ── Helpers ──────────────────────────────────────────────────────────────────

def set_run_font(run, size_pt=11, bold=False, color_hex=None, name="Calibri"):
    run.font.size = Pt(size_pt)
    run.font.name = name
    run.bold = bold
    if color_hex:
        run.font.color.rgb = RGBColor.from_string(color_hex)


def fix_bullet_fonts(doc, size_pt=11):
    try:
        doc.styles["List Bullet"].font.size = Pt(size_pt)
    except KeyError:
        pass
    for p in doc.paragraphs:
        pPr = p._element.find(qn("w:pPr"))
        if pPr is not None and pPr.find(qn("w:numPr")) is not None:
            for r in p.runs:
                r.font.size = Pt(size_pt)
                r.font.name = "Calibri"


def _xml_index(elem):
    """Return the 0-based index of an XML element in its parent's children."""
    parent = elem.getparent()
    if parent is None:
        return -1
    for i, child in enumerate(parent):
        if child is elem:
            return i
    return -1


# ── CV Renderer ──────────────────────────────────────────────────────────────

def render_cv(base_cv_path, jd, output_path, company, role):
    """
    Tailor a base CV for a specific company + role.

    Strategy:
    1. Load base CV docx.
    2. Rewrite summary paragraph to reference target company + role.
    3. Reorder experience bullets: JD-matched achievements first (XML surgery).
       Must run BEFORE skills injection because body.clear() + rebuild would
       wipe any injected paragraphs.
    4. Inject a TECHNICAL SKILLS section before ENGINEERING DECISIONS.
       Uses doc.add_paragraph() for native registration, then addprevious()
       to move paragraphs into position.
    5. Fix fonts, margins, save.
    """
    doc = Document(base_cv_path)

    jd_company = jd.get("company", company)
    jd_role = jd.get("title", role)
    jd_key_skill = jd.get("primary_skill", "")
    jd_required = jd.get("required_skills", [])
    jd_secondary = jd.get("secondary_skills", [])

    # ── 1. Rewrite contact header block ──────────────────────────────────────
    # Rewrite the first paragraphs (NAME, summary, contact line) of the base
    # CV with a clean, well-formatted contact header:
    #   NAME (large bold, Title Case) 
    #   single-line contact row (phone | email | location | LinkedIn | GitHub)
    #   summary paragraph (body text size, on its own line)
    #
    # Find the contact line (contains email), NAME line, and summary paragraph.
    name_p = None
    contact_p = None
    summary_p = None
    for p in doc.paragraphs:
        t = p.text.strip()
        if t and "@" in t and ("gmail" in t or "hotmail" in t or "outlook" in t):
            contact_p = p
        elif t and t.upper() == t and len(t) < 40 and not "://" in t:
            if name_p is None:
                name_p = p
        elif summary_p is None and t and ("Applied AI Engineer" in t 
                or "specialising" in t or "specializing" in t
                or "AI/ML systems" in t):
            summary_p = p

    phone = CANDIDATE.get("phone", "").strip()
    email_addr = CANDIDATE.get("email", "").strip()
    location = CANDIDATE.get("location", "").strip()
    linkedin = CANDIDATE.get("linkedin", "").strip()
    github = CANDIDATE.get("github", "").strip()

    contact_parts = []
    if phone:
        contact_parts.append(phone)
    if email_addr:
        contact_parts.append(email_addr)
    if location:
        contact_parts.append(location)
    if linkedin:
        contact_parts.append(linkedin)
    if github:
        contact_parts.append(github)

    contact_line = "  |  ".join(contact_parts)

    name_size = float(CANDIDATE.get("name_size", 24))
    contact_size = float(CANDIDATE.get("contact_size", 10))
    body_size = 10.5

    if name_p is not None:
        # Rewrite NAME paragraph — Title Case, not ALL CAPS
        name_display = NAME.strip().title() if NAME.strip().isupper() else NAME.strip()
        for r in name_p.runs:
            r.text = ""
        if name_p.runs:
            name_p.runs[0].text = name_display
        else:
            name_p.add_run(name_display)
        for r in name_p.runs:
            r.bold = True
            r.font.size = Pt(name_size)
            r.font.name = "Calibri"
        name_p.paragraph_format.space_after = Pt(4)
        name_p.paragraph_format.space_before = Pt(0)

    if contact_p is not None and contact_line:
        # Rewrite contact line paragraph
        for r in contact_p.runs:
            r.text = ""
        if contact_p.runs:
            contact_p.runs[0].text = contact_line
        else:
            contact_p.add_run(contact_line)
        for r in contact_p.runs:
            r.font.size = Pt(contact_size)
            r.font.name = "Calibri"
        contact_p.paragraph_format.space_after = Pt(6)
        contact_p.paragraph_format.space_before = Pt(0)

    if summary_p is not None:
        # Ensure summary paragraph uses body text size, not heading size
        for r in summary_p.runs:
            r.font.size = Pt(body_size)
            r.font.name = "Calibri"
        summary_p.paragraph_format.space_after = Pt(8)
        summary_p.paragraph_format.space_before = Pt(0)

    # ── 2. Reorder experience bullets FIRST ──────────────────────────────────
    _reorder_experience_bullets(doc, jd_required)

    # ── 3. Inject TECHNICAL SKILLS section (after reorder, before save) ─────
    _inject_skills_section(doc, jd_required, jd_secondary)

    # ── 4. Fix fonts and section headers ─────────────────────────────────────
    header_sizes = {0: 24, 1: 14, 2: 11, 3: 10}
    for i, p in enumerate(doc.paragraphs):
        for r in p.runs:
            if i in header_sizes:
                set_run_font(r, size_pt=header_sizes[i], bold=(i == 0))
            else:
                set_run_font(r, size_pt=10.5)

    for p in doc.paragraphs:
        t = p.text.strip()
        if t and len(t) < 60 and t == t.upper() and not t.startswith("http") and "://" not in t:
            if p.alignment != WD_ALIGN_PARAGRAPH.CENTER:
                for r in p.runs:
                    r.bold = True

    fix_bullet_fonts(doc, size_pt=11)

    # ── 5. Fix margins ───────────────────────────────────────────────────────
    for section in doc.sections:
        section.left_margin = Inches(MARGIN_INCHES)
        section.right_margin = Inches(MARGIN_INCHES)
        section.top_margin = Inches(MARGIN_INCHES)
        section.bottom_margin = Inches(MARGIN_INCHES)

    # ── 6. Save ──────────────────────────────────────────────────────────────
    doc.save(output_path)
    return output_path


def _inject_skills_section(doc, required_skills, secondary_skills):
    """Insert a TECHNICAL SKILLS section before ENGINEERING DECISIONS.

    Uses doc.add_paragraph() (python-docx-native) so paragraphs are properly
    registered in doc.paragraphs, then moves them to the correct position
    via lxml's addprevious() on the target paragraph's XML element.
    """
    # Known skills from the CV — sourced from CV_HOLISTIC_MASTER.md "Core
    # Competencies" section (all categories) so tailored CVs can surface the
    # full depth of the real ATS keyword bank, not just a ~70-term subset.
    all_skills = [
        # Gen-AI & LLM Systems
        "RAG", "Hybrid Retrieval", "BM25", "BGE-M3", "SPLADE", "RRF",
        "Cross-Encoder Reranking", "Contextual Retrieval", "Agentic AI",
        "LLM-as-Judge", "Multi-Provider LLM Routing", "Prompt Engineering",
        "LangChain", "LangGraph", "LlamaIndex", "CrewAI", "AutoGen",
        "Hugging Face", "Pydantic", "Pydantic v2", "LiteLLM",
        "Model Routing", "LLM Governance", "Structured Outputs",
        "Context Engineering", "Token Optimization", "Embeddings",
        "Local LLM Deployment", "Prompt Caching",
        # Voice & Conversational AI
        "ASR", "Whisper", "faster-whisper", "CTranslate2", "AssemblyAI",
        "Deepgram", "NVIDIA NeMo", "Parakeet", "WER", "jiwer",
        "Speaker Diarization", "Pyannote", "VAD", "Silero VAD",
        "Semantic Endpoint", "BART-NLI", "BART-MNLI", "Transcript Enrichment",
        "GoEmotions", "EmoBERTa", "emotion2vec", "j-hartmann",
        "MiniLM", "MIDLM", "LARA Intent", "Predicted CSAT", "FCR",
        "Streaming pCSAT", "Mamba", "Mamba-2", "SSM", "Peak-End Pooling",
        "Conformal Prediction", "Arabic NLP", "Sentiment Analysis",
        "WebRTC", "Voice APIs", "Bayesian ASR Rescoring",
        "Dialogue State Tracking", "Audio Preprocessing",
        # Data & Pipelines
        "Databricks", "Delta Live Tables", "Delta Lake", "Change Data Feed",
        "Unity Catalog", "PySpark", "Spark SQL", "Manifest-Driven Orchestration",
        "Incremental Refresh", "Watermarks", "SQL Code Generation",
        "Feature Engineering", "KPI Pipelines", "Snapshot History",
        "Kimball", "SCD1", "SCD2", "Hevo", "Silver/Gold Architecture",
        "Zendesk API", "Survicate", "Channel Taxonomy", "SQL Testing",
        "Infrastructure-as-Code",
        # Vector / Graph DBs
        "ChromaDB", "Pinecone", "FAISS", "Neo4j", "Weaviate", "Qdrant",
        "pgvector", "Vector Database", "Vector Search",
        # Backend & APIs
        "Python", "SQL", "Flask", "FastAPI", "MS SQL", "MySQL",
        "PostgreSQL", "TypeScript", "Node.js", "Go", "REST APIs",
        "WebSockets", "SDK Development", "Async Python",
        "Amazon Connect CTR", "Contact Lens", "Cross-Modal Validation",
        "Async Merge Buffers", "Content Hash Dedup", "Edit Distance Clustering",
        "Parser Confidence Modeling", "Thompson Sampling",
        # MLOps / CI-CD
        "Databricks Asset Bundles", "GitHub Actions", "Docker", "Kubernetes",
        "pytest", "MLflow", "CI/CD", "Model Logging", "Experiment Management",
        "HuggingFace Model Caching", "Lazy Model Loading",
        "Golden Dataset", "Evaluation Framework Design",
        # Cloud
        "AWS", "Google Cloud Platform", "GCP", "Azure",
        # BI & Analytics
        "Tableau", "BI Dashboard Design", "KPI Definition", "Time-Series",
        "Operational Analytics",
        # QC & Evaluation
        "17-Dimension Rubric", "Bayesian Aggregation", "Human-in-the-Loop",
        "ASR Evaluation", "Call Quality Scoring", "Intent Classification",
        "Prompt Injection Detection", "PII Detection",
        "Deterministic Scoring", "Pre-Batch Cost Estimation",
        # General / framework terms retained for backward-compat matching
        "PyTorch", "TensorFlow", "JAX", "scikit-learn", "Transformers",
        "Snowflake", "pandas", "NumPy", "Diarization", "TTS",
        "Emotion Detection", "Multi-Agent Systems", "Git", "GitHub",
        "GraphQL", "Unit Testing", "Software Engineering",
    ]

    # Match JD skills
    required_set = {s.lower() for s in required_skills}
    secondary_set = {s.lower() for s in secondary_skills}

    matched_required = []
    matched_secondary = []
    unmatched = []

    for skill in all_skills:
        skill_lower = skill.lower()
        matched = False
        for req in required_set:
            if req in skill_lower or skill_lower in req:
                matched_required.append(skill)
                matched = True
                break
        if matched:
            continue
        for sec in secondary_set:
            if sec in skill_lower or skill_lower in sec:
                matched_secondary.append(skill)
                matched = True
                break
        if matched:
            continue
        unmatched.append(skill)

    # Build ordered skill groups
    skills_lines = []
    if matched_required:
        skills_lines.append(("JD-Matched Skills (Bold)", matched_required, True))
    if matched_secondary:
        skills_lines.append(("JD-Secondary Skills", matched_secondary, False))
    if unmatched:
        cat_lang = [s for s in unmatched if any(kw in s.lower() for kw in ["python", "sql", "pytorch", "tensorflow", "flask", "fastapi"])]
        cat_data = [s for s in unmatched if any(kw in s.lower() for kw in ["databricks", "aws", "gcp", "azure", "snowflake", "delta", "docker", "github"])]
        cat_ai = [s for s in unmatched if any(kw in s.lower() for kw in ["rag", "llm", "vector", "faiss", "langchain", "speech", "asr", "emotion", "sentiment", "intent", "agentic", "agent"])]
        cat_other = [s for s in unmatched if s not in cat_lang and s not in cat_data and s not in cat_ai]
        for cat_name, cat_skills in [("Languages & Frameworks", cat_lang), ("Data & Cloud", cat_data), ("AI/ML & NLP", cat_ai), ("Other", cat_other)]:
            if cat_skills:
                skills_lines.append((cat_name, cat_skills, False))
    if not skills_lines:
        skills_lines.append(("Technical Skills", all_skills[:20], False))

    # ── Create paragraphs using doc.add_paragraph() so python-docx tracks them ──
    created_paras = []  # list of docx Paragraph objects, in order

    # Heading: TECHNICAL SKILLS
    heading_p = doc.add_paragraph("TECHNICAL SKILLS")
    heading_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for r in heading_p.runs:
        r.bold = True
        r.font.size = Pt(11)
        r.font.name = "Calibri"
    heading_p.paragraph_format.space_before = Pt(12)
    heading_p.paragraph_format.space_after = Pt(4)
    created_paras.append(heading_p)

    for section_label, skills, bold_first in skills_lines:
        if section_label != "Technical Skills":
            sub_p = doc.add_paragraph(section_label + ":")
            for r in sub_p.runs:
                r.bold = True
                r.font.size = Pt(10)
                r.font.name = "Calibri"
            sub_p.paragraph_format.space_before = Pt(6)
            sub_p.paragraph_format.space_after = Pt(2)
            created_paras.append(sub_p)

        # Batch skills into lines of 5
        line_skills = []
        for skill in skills:
            line_skills.append(skill)
            if len(line_skills) >= 5:
                bullet_text = ", ".join(line_skills)
                bullet_p = doc.add_paragraph(bullet_text, style="List Bullet")
                for r in bullet_p.runs:
                    r.font.size = Pt(11)
                    r.font.name = "Calibri"
                    if bold_first:
                        r.bold = True
                bullet_p.paragraph_format.space_after = Pt(0)
                created_paras.append(bullet_p)
                line_skills = []
        if line_skills:
            bullet_text = ", ".join(line_skills)
            bullet_p = doc.add_paragraph(bullet_text, style="List Bullet")
            for r in bullet_p.runs:
                r.font.size = Pt(11)
                r.font.name = "Calibri"
                if bold_first:
                    r.bold = True
            bullet_p.paragraph_format.space_after = Pt(0)
            created_paras.append(bullet_p)

    # ── Find insertion point and move paragraphs into position ────────────────
    # Look for ENGINEERING DECISIONS or EDUCATION in doc.paragraphs
    target_para = None
    for p in doc.paragraphs:
        t = p.text.strip()
        if t == "ENGINEERING DECISIONS":
            target_para = p
            break

    if target_para is None:
        for p in doc.paragraphs:
            t = p.text.strip()
            if t == "EDUCATION":
                target_para = p
                break

    if target_para is not None:
        # Move each created paragraph to just before target_para.
        # We insert one at a time, each time placing the new paragraph
        # before the paragraph we just inserted (or before target for the
        # first one). This preserves created_paras order with heading first.
        target_elem = target_para._element
        prev_inserted = target_elem
        for cp in created_paras:
            prev_inserted.addprevious(cp._element)
            prev_inserted = cp._element
    # If no target found, paragraphs remain at end (acceptable fallback)


def _reorder_experience_bullets(doc, jd_required):
    """Reorder experience section: JD-matched paragraphs first (via XML surgery).

    Only reorders paragraphs that are part of the EXPERIENCE section (between
    the EXPERIENCE heading and the next ALL-CAPS heading like ENGINEERING DECISIONS).

    The operation is: clear body, re-append pre-exp + reordered exp + post-exp.
    This must run BEFORE _inject_skills_section because body.clear() would
    remove any paragraphs injected earlier.

    After clearing/rebuilding, collapses duplicate w:t text nodes that the
    source CV sometimes contains (e.g. "ENGINEERING DECISIONS" stored in 3
    separate runs, which itertext() would read as triplicated).
    """
    if not jd_required:
        return

    # Collect JD keywords
    jd_keywords = set()
    for skill in jd_required:
        for w in skill.lower().split():
            if len(w) > 3:
                jd_keywords.add(w)

    def match_score(text):
        text_lower = text.lower()
        score = 0
        for kw in jd_keywords:
            if kw in text_lower:
                score += 1
        for skill in jd_required:
            if skill.lower() in text_lower:
                score += 3
        return score

    # ── Find EXPERIENCE section boundaries via doc.paragraphs ────────────────
    exp_start = -1
    exp_end = -1
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        if t != t.upper():
            continue
        if "://" in t:
            continue
        if len(t) >= 60:
            continue
        if "EXPERIENCE" in t:
            exp_start = i
        elif exp_start >= 0 and exp_end == -1:
            exp_end = i
            break

    if exp_start < 0 or exp_end < 0:
        return

    # ── Classify paragraphs within the experience section ─────────────────────
    body = doc.element.body
    paras_xml = [e for e in body if e.tag.endswith('}p')]

    heading_paras = []   # (idx, xml_elem, text) — includes the EXPERIENCE heading
    matched_content = []  # (idx, xml_elem, text, score)
    other_content = []    # (idx, xml_elem, text)

    # Always include the EXPERIENCE heading as the first item
    exp_heading_pe = paras_xml[exp_start]
    exp_heading_p = doc.paragraphs[exp_start]
    heading_paras.append((exp_start, exp_heading_pe, exp_heading_p.text.strip()))

    for i in range(exp_start + 1, exp_end):
        pe = paras_xml[i]
        p = doc.paragraphs[i]
        t = p.text.strip()
        if not t:
            heading_paras.append((i, pe, t))
            continue
        score = match_score(t)
        if score > 0:
            matched_content.append((i, pe, t, score))
        else:
            other_content.append((i, pe, t))

    # Sort: highest score first, then others in original order
    matched_content.sort(key=lambda x: -x[3])
    ordered = heading_paras + matched_content + other_content

    # ── Rebuild the body ─────────────────────────────────────────────────────
    # Capture post-exp XML elements BEFORE clearing
    post_exp = [paras_xml[i] for i in range(exp_end, len(paras_xml))]
    # Capture pre-exp XML elements (everything before exp_start)
    pre_exp = [paras_xml[i] for i in range(exp_start)]

    body.clear()
    for pe in pre_exp:
        body.append(pe)
    for item in ordered:
        # item may be (idx, elem, text) or (idx, elem, text, score) — elem is always index 1
        body.append(item[1])
    for pe in post_exp:
        body.append(pe)

    # ── After rebuild: collapse duplicate text nodes in each paragraph ────────
    # The source CV sometimes stores a heading's text across multiple w:t runs
    # (e.g. "ENGINEERING DECISIONS" in 3 runs → itertext() returns it 3x).
    # Merge all w:t children of each paragraph into the first run.
    for pe in body:
        if not pe.tag.endswith('}p'):
            continue
        t_elems = list(pe.iter(qn('w:t')))
        if len(t_elems) <= 1:
            continue
        # Merge all text into the first w:t, remove the rest
        merged_text = "".join(t.text or "" for t in t_elems)
        t_elems[0].text = merged_text
        for extra_t in t_elems[1:]:
            extra_t.getparent().remove(extra_t)


# ── Cover Letter Renderer ──────────────────────────────────────────────────

def render_cover_letter(jd, cv_evidence, output_path, company, role):
    # If cv_evidence is None or empty, try loading match.json
    if not cv_evidence:
        import os as _os
        match_path = _os.path.join(_os.path.dirname(output_path), "match.json")
        if _os.path.exists(match_path):
            with open(match_path) as _f:
                cv_evidence = json.load(_f)
    
    jd_company = jd.get("company", company)
    jd_role = jd.get("title", role)
    jd_key_req = jd.get("primary_skill") or (jd.get("required_skills") or [role])[0]

    gaps = cv_evidence.get("gaps", [])
    gap_text = ""
    if gaps:
        gap = gaps[0]
        if isinstance(gap, dict):
            gap_skill = gap.get("skill", "a relevant technology")
            # gap dict may use "required" as a boolean (from match_to_cv) — handle both
            gap_required = gap.get("required")
            if isinstance(gap_required, str):
                pass  # use as-is
            elif isinstance(gap_required, bool):
                gap_required = gap_skill  # e.g. "Computer Vision" (the skill itself)
            else:
                gap_required = gap_skill
            gap_actual = gap.get("actual", "production AI systems")
        else:
            gap_skill = str(gap)
            gap_actual = "production AI systems"
            gap_required = str(gap)
        gap_text = (
            f"My {gap_skill} experience has been primarily with {gap_actual} "
            f"rather than {gap_required}, though the underlying concepts "
            f"transfer directly."
        )

    para1 = (
        f"I am writing to apply for the {jd_role} position at {jd_company}. "
        f"Your requirement for {jd_key_req} aligns directly with my recent production work "
        f"building and operating voice AI and conversational AI pipelines — including hybrid "
        f"retrieval systems, LLM-as-judge evaluation, and end-to-end ASR-to-insight pipelines "
        f"serving 140+ agents."
    )

    para2 = (
        f"In my current role I own the full AI stack for a contact-center platform: from faster-whisper "
        f"ASR and Silero VAD through speaker diarization, transcript enrichment (emotion, intent, "
        f"sentiment), hybrid RAG over a policy corpus, and a 17-dimension LLM evaluation scorer with "
        f"quote-grounded structured output. The system serves real calls daily and the metrics feed BI "
        f"dashboards and agent coaching. On the data side I have architected Delta Live Table pipelines "
        f"with CDF incremental refresh, spine replay for accurate state, and a gold KPI layer with 18 "
        f"metrics — all on Databricks with PySpark."
    )

    para3 = (
        f"{gap_text} "
        f"I am based in Dubai, UAE (UAE Resident — no visa sponsorship required) and available to start "
        f"immediately. I would welcome the chance to discuss how this experience maps to {jd_company}'s "
        f"needs."
    )

    doc = Document()
    for section in doc.sections:
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)

    # ── Contact header block (NAME + phone/email/contact + date) ──────────────
    phone = CANDIDATE.get("phone", "").strip()
    email_addr = CANDIDATE.get("email", "").strip()
    location = CANDIDATE.get("location", "").strip()
    linkedin = CANDIDATE.get("linkedin", "").strip()
    github = CANDIDATE.get("github", "").strip()

    contact_parts = []
    if phone:
        contact_parts.append(phone)
    if email_addr:
        contact_parts.append(email_addr)
    if location:
        contact_parts.append(location)
    if linkedin:
        contact_parts.append(linkedin)
    if github:
        contact_parts.append(github)
    contact_line = "  |  ".join(contact_parts)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(f"{NAME}")
    set_run_font(r, size_pt=12, bold=True)
    p.paragraph_format.space_after = Pt(2)

    if contact_line:
        p = doc.add_paragraph()
        r = p.add_run(contact_line)
        set_run_font(r, size_pt=10)
        p.paragraph_format.space_after = Pt(2)

    p = doc.add_paragraph()
    r = p.add_run(TODAY)
    set_run_font(r, size_pt=10)
    p.paragraph_format.space_after = Pt(6)

    p = doc.add_paragraph()
    r = p.add_run(f"Dear {jd_company} Hiring Team,")
    set_run_font(r, size_pt=11)

    for para_text in [para1, para2, para3]:
        p = doc.add_paragraph()
        r = p.add_run(para_text)
        set_run_font(r, size_pt=11)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15

    p = doc.add_paragraph()
    r = p.add_run("Sincerely,")
    set_run_font(r, size_pt=11)
    p.paragraph_format.space_before = Pt(12)

    p = doc.add_paragraph()
    r = p.add_run(NAME)
    set_run_font(r, size_pt=11, bold=True)

    doc.save(output_path)
    return output_path


# ── README Renderer ────────────────────────────────────────────────────────

def render_readme(jd, cv_evidence, output_path, company, role, apply_url):
    # If cv_evidence is None or has no fit_score, try loading from match.json
    if not cv_evidence or not cv_evidence.get("fit_score"):
        import os as _os
        match_path = _os.path.join(_os.path.dirname(output_path), "match.json")
        if _os.path.exists(match_path):
            with open(match_path) as _f:
                cv_evidence = json.load(_f)
    match_details = cv_evidence.get("match_details", [])
    gaps = cv_evidence.get("gaps", [])
    jd_key_skill = jd.get("primary_skill", role)

    readme = f"""# {company} — {role}

**Apply:** [{apply_url}]({apply_url})
**Date:** {TODAY}
**Status:** READY

## Role Summary

{jd.get('full_jd', 'JD extracted — see jd.xlsx for full text.')[:500]}

## Fit Analysis

**Overall Fit:** {cv_evidence.get("fit_score", "UNKNOWN")}

### Matches
"""
    for m in match_details:
        if isinstance(m, dict):
            skill = m.get("skill", "unknown")
            status = m.get("status", "?")
            evidence = m.get("evidence", "CV")
        else:
            skill = str(m)
            status = "?"
            evidence = "CV"
        readme += f"- **{skill}:** {status} — {evidence}\n"

    if gaps:
        readme += "\n### Gaps\n"
        for g in gaps:
            if isinstance(g, dict):
                gskill = g.get("skill", "unknown")
                gnote = g.get("note", "Gap against JD")
            else:
                gskill = str(g)
                gnote = "Gap against JD"
            readme += f"- **{gskill}:** {gnote}\n"

    readme += f"""
## Interview Prep Focus

- {jd_key_skill} depth and production experience
- Architecture decisions: why this stack, what alternatives were considered
- Failure modes and how they were detected/fixed
- Scale and outcomes: numbers, not just technology names

## Follow-Up

- **1 week after apply:** Check application status
- **2 weeks after apply:** If no response, follow up via LinkedIn or email
- **After interview:** Log outcome to tracker within 24 hours

## Files in This Folder

- `cv.docx` — tailored CV for {company}
- `cover_letter.docx` — tailored cover letter
- `jd.xlsx` — extracted job description (immutable archive)
- `README.md` — this file
"""
    with open(output_path, "w") as f:
        f.write(readme)
    return output_path


# ── JD Excel Renderer ──────────────────────────────────────────────────────

def render_jd_excel(jd, output_path, company):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"JD_{company[:31]}"

    header_font = Font(bold=True, size=11)
    label_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    label_font = Font(bold=True)
    jd_font = Font(size=10)

    required_skills = jd.get("required_skills", [])
    if isinstance(required_skills, list):
        skills_str = ", ".join(required_skills)
    else:
        skills_str = str(required_skills)

    fields = [
        ("Title", jd.get("title", "")),
        ("Company", jd.get("company", "")),
        ("Location", jd.get("location", "")),
        ("Apply URL", jd.get("apply_url", "")),
        ("Source URL", jd.get("url", "")),
        ("Platform", jd.get("platform", "")),
        ("Posted Date", jd.get("posted_date", "")),
        ("Employment Type", jd.get("type", "")),
        ("Years Experience", str(jd.get("years_exp", ""))),
        ("Degree Required", jd.get("degree", "")),
        ("Salary Range", jd.get("salary", "")),
        ("Required Skills (raw)", skills_str),
        ("Full JD (below)", ""),
    ]

    for i, (label, value) in enumerate(fields, start=1):
        ws.cell(row=i, column=1, value=label).font = label_font
        ws.cell(row=i, column=1).fill = label_fill
        ws.cell(row=i, column=2, value=value or "")

    raw_jd = jd.get("full_jd", "")
    ws.cell(row=14, column=1, value=raw_jd).font = jd_font

    # Adjust column widths
    for col_cells in ws.columns:
        max_length = 0
        col_letter = None
        for cell in col_cells:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
                col_letter = cell.column_letter
        if col_letter:
            adjusted_width = min(max_length + 2, 100)
            ws.column_dimensions[col_letter].width = max(adjusted_width, 15)

    wb.save(output_path)
    return output_path


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Job Application Document Renderer")
    parser.add_argument("--cv-base", required=True, help="Path to base CV .docx")
    parser.add_argument("--jd-json", required=True, help="Path to JD JSON file")
    parser.add_argument("--output-dir", required=True, help="Company output folder")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--role", required=True, help="Job role title")
    parser.add_argument("--name", default=NAME, help="Candidate name")
    parser.add_argument("--cv-name", default="CV", help="CV file prefix")
    args = parser.parse_args()

    with open(args.jd_json) as f:
        jd = json.load(f)

    os.makedirs(args.output_dir, exist_ok=True)

    # Load match data from match.json if it exists (produced by match_to_cv.py)
    match_path = os.path.join(args.output_dir, "match.json")
    if os.path.exists(match_path):
        with open(match_path) as _f:
            match_data = json.load(_f)
    else:
        match_data = {}
    
    results = {}
    
    safe_company = args.company
    safe_role = re.sub(r"[^a-zA-Z0-9]+", "_", args.role).strip("_")
    MAX_ROLE_LEN = 40
    if len(safe_role) > MAX_ROLE_LEN:
        safe_role = safe_role[:MAX_ROLE_LEN].rstrip("_")
    cv_path = os.path.join(args.output_dir, f"{args.cv_name}_{safe_company}_{safe_role}.docx")
    render_cv(args.cv_base, jd, cv_path, args.company, args.role)
    results["cv"] = cv_path
    
    cv_evidence = match_data or {}
    if not cv_evidence:
        cv_evidence = {
            "gaps": jd.get("gaps", []),
            "fit_score": jd.get("fit_score", "UNKNOWN"),
            "match_details": jd.get("match_details", []),
        }
    cl_path = os.path.join(args.output_dir, f"CoverLetter_{safe_company}_{safe_role}.docx")
    render_cover_letter(jd, cv_evidence, cl_path, args.company, args.role)
    results["cover_letter"] = cl_path
    
    readme_path = os.path.join(args.output_dir, "README.md")
    render_readme(jd, cv_evidence, readme_path, args.company, args.role, jd.get("apply_url", ""))
    results["readme"] = readme_path

    jd_xlsx_path = os.path.join(args.output_dir, "jd.xlsx")
    render_jd_excel(jd, jd_xlsx_path, args.company)
    results["jd_xlsx"] = jd_xlsx_path

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
