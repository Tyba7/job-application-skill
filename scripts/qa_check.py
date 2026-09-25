#!/usr/bin/env python3
"""
qa_check.py — CV Quality Assurance Tool

Runs keyword coverage + formatting checks on rendered CVs.
Used after document generation to verify the CV is ready to send.

Usage:
  python qa_check.py \
    --cv CV_G42_AI_Engineer.docx \
    --must-keys Python,RAG,LLM,Databricks \
    --expected-links 1 \
    --expected-bullets 10 \
    --output qareport.json

Output qareport.json:
  {
    "file": "CV_G42_AI_Engineer.docx",
    "keyword_check": {"status": "PASS", "missing": []},
    "formatting": {
      "links": 1,
      "bullets": 12,
      "usable_mm": 184.2,
      "paragraphs": 87
    },
    "flags": []
  }
"""

import argparse
import json
import os
import sys
import glob
from docx import Document
from docx.oxml.ns import qn

# Skills commonly used by this pipeline — used when --must-keys not provided
DEFAULT_MUST_KEYS = [
    "Python", "RAG", "LLM", "Databricks", "PySpark",
    "Machine Learning", "Deep Learning", "NLP",
]


def check_keywords(cv_text, must_keys):
    """Case-insensitive keyword presence check."""
    lower = cv_text.lower()
    missing = []
    present = []
    for key in must_keys:
        if key.lower() in lower:
            present.append(key)
        else:
            # Check surface-form variants
            variants = _get_variants(key)
            found_variant = None
            for v in variants:
                if v.lower() in lower:
                    found_variant = v
                    break
            if found_variant:
                present.append(f"{key} (as '{found_variant}')")
            else:
                missing.append(key)
    return present, missing


def _get_variants(skill):
    """Return plausible surface-form variants for a skill name."""
    s = skill.lower()
    variants = [skill]
    if s == "conversational ai":
        variants += ["conversation ai", "chatbot", "conversational"]
    if s == "generative ai":
        variants += ["genai", "gen-ai", "gen ai"]
    if s == "automatic speech recognition":
        variants += ["asr"]
    if s == "retrieval augmented generation":
        variants += ["rag"]
    if s == "vector database":
        variants += ["vector db", "vectorstore"]
    if "pytorch" in s:
        variants += ["torch"]
    if "kubernetes" in s:
        variants += ["k8s", "kubectl"]
    if s == "aws":
        variants += ["amazon web services"]
    if s == "gcp":
        variants += ["google cloud", "google cloud platform"]
    if s == "azure":
        variants += ["microsoft azure"]
    return variants


def check_formatting(cv_path):
    """Check structural formatting properties of a CV."""
    doc = Document(cv_path)

    # Count hyperlinks
    links = sum(
        len(p._element.findall(qn("w:hyperlink")))
        for p in doc.paragraphs
    )

    # Count bullets (paragraphs with numPr — either explicit on the paragraph
    # OR inherited from the paragraph's style, which is where List Bullet style
    # places its numPr reference in python-docx-generated docs).
    bullets = 0
    for p in doc.paragraphs:
        pPr = p._element.find(qn("w:pPr"))
        explicit_numpr = pPr is not None and pPr.find(qn("w:numPr")) is not None
        if explicit_numpr:
            bullets += 1
            continue
        # Check style-inherited numPr: the List Bullet style places numPr in
        # the style definition, not on each paragraph. Count paragraphs whose
        # style references a numId.
        style_id = None
        if pPr is not None:
            pStyle = pPr.find(qn("w:pStyle"))
            if pStyle is not None:
                style_id = pStyle.get(qn("w:val"))
        if style_id:
            # Look up style element by styleId in the styles part XML.
            # get_by_id requires WD_STYLE_TYPE and is awkward; raw XML is direct.
            styles_elem = doc.styles.element
            style_elem = None
            for s in styles_elem.findall(qn("w:style")):
                if s.get(qn("w:styleId")) == style_id:
                    style_elem = s
                    break
            if style_elem is not None:
                style_pPr = style_elem.find(qn("w:pPr"))
                if style_pPr is not None and style_pPr.find(qn("w:numPr")) is not None:
                    bullets += 1

    # Usable width in mm — guard against docs with no explicit section
    sections = doc.sections
    if sections:
        section = sections[0]
        usable_mm = round(
            (section.page_width - section.left_margin - section.right_margin)
            / 36000, 1  # EMU to mm
        )
    else:
        usable_mm = 0.0  # No section defined — can't measure; not a real problem

    # Paragraph count
    para_count = len(doc.paragraphs)

    # Check for common ISSUES
    flags = []

    # Skip $~-prefixed files (Word lock files)
    basename = os.path.basename(cv_path)
    if basename.startswith("~$"):
        flags.append("LOCK_FILE: this is a Word temporary file, not a real document")

    # Tables — ATS-unfriendly
    if doc.tables:
        flags.append(f"TABLES: {len(doc.tables)} table(s) found — may hurt ATS parsing")

    # Headers/footers — ATS-unfriendly only if they contain actual text.
    # Some freshly-rendered docs have 0 sections (no sectPr) — that's fine,
    # skip the check when there are no sections to inspect.
    if sections:
        for section in sections:
            header_has_text = any(p.text.strip() for p in section.header.paragraphs)
            footer_has_text = any(p.text.strip() for p in section.footer.paragraphs)
            if header_has_text or footer_has_text:
                flags.append("HEADER_FOOTER: document has header/footer content")

    # Usable width check — too wide or too narrow.
    # usable_mm == 0.0 means no explicit section (sectPr) in the docx, which is
    # common in python-docx-generated files and not a real formatting problem.
    if usable_mm > 0 and usable_mm < 150:
        flags.append(f"WIDTH: usable width {usable_mm}mm is narrow — check margins")
    elif usable_mm > 200:
        flags.append(f"WIDTH: usable width {usable_mm}mm is wide — check margins")

    return {
        "links": links,
        "bullets": bullets,
        "usable_mm": usable_mm,
        "paragraphs": para_count,
        "flags": flags,
    }


def main():
    parser = argparse.ArgumentParser(description="CV Quality Assurance Checker")
    parser.add_argument("--cv", required=True, help="Path to CV .docx file (or glob pattern)")
    parser.add_argument("--must-keys", help="Comma-separated list of required keywords")
    parser.add_argument("--expected-links", type=int, help="Expected hyperlink count")
    parser.add_argument("--expected-bullets", type=int, help="Expected bullet count")
    parser.add_argument("--output", help="Output JSON path (optional)")
    parser.add_argument("--glob", action="store_true", help="Treat --cv as a glob pattern")
    args = parser.parse_args()

    must_keys = []
    if args.must_keys:
        must_keys = [k.strip() for k in args.must_keys.split(",") if k.strip()]
    else:
        must_keys = DEFAULT_MUST_KEYS

    # Resolve CV file(s)
    if args.glob:
        cv_files = sorted(glob.glob(args.cv))
        # Skip lock files
        cv_files = [f for f in cv_files if not os.path.basename(f).startswith("~$")]
    else:
        cv_files = [args.cv]

    if not cv_files:
        print("ERROR: no CV files found", file=sys.stderr)
        sys.exit(1)

    reports = []
    for cv_path in cv_files:
        report = _check_single_cv(cv_path, must_keys, args)
        reports.append(report)

    result = {
        "checked_files": len(reports),
        "reports": reports,
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


def _check_single_cv(cv_path, must_keys, args):
    """Check a single CV file."""
    doc = Document(cv_path)
    cv_text = " ".join(p.text for p in doc.paragraphs)
    fmt = check_formatting(cv_path)
    present, missing = check_keywords(cv_text, must_keys)

    # Verify hyperlink count if expected provided
    link_flag = None
    if args.expected_links is not None and fmt["links"] != args.expected_links:
        link_flag = f"LINK_COUNT: expected {args.expected_links}, got {fmt['links']}"

    # Verify bullet count if expected provided
    bullet_flag = None
    if args.expected_bullets is not None and fmt["bullets"] != args.expected_bullets:
        bullet_flag = f"BULLET_COUNT: expected {args.expected_bullets}, got {fmt['bullets']}"

    all_flags = list(fmt["flags"])
    if link_flag:
        all_flags.append(link_flag)
    if bullet_flag:
        all_flags.append(bullet_flag)

    return {
        "file": os.path.basename(cv_path),
        "path": cv_path,
        "keyword_check": {
            "status": "PASS" if not missing else "FAIL",
            "present": present,
            "missing": missing,
        },
        "formatting": fmt,
        "overall": "PASS" if (not missing and not all_flags) else "FAIL",
    }


if __name__ == "__main__":
    main()
