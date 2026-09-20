#!/usr/bin/env python3
"""
match_to_cv.py — JD-to-CV Match Tool

Evaluates fit between a user's CV and a job description.
Reads the CV via python-docx, checks codebase evidence, builds a match matrix.

Usage:
  python match_to_cv.py \
    --cv /path/to/cv.docx \
    --jd-json /path/to/jd.json \
    --codebase /path/to/codebase \
    --output /path/to/match_result.json

Output JSON:
  {
    "fit_score": "HIGH (85%)",
    "match_details": [
      {"skill": "Python", "status": "EXACT", "evidence": "CV + codebase: src/audio/"},
      ...
    ],
    "gaps": [
      {"skill": "Azure", "note": "User has AWS/GCP only — MISSING"}
    ]
  }
"""

import argparse
import json
import os
import re
import subprocess
from docx import Document
from pathlib import Path


def read_cv_text(cv_path):
    """Extract all text from a .docx CV."""
    doc = Document(cv_path)
    return " ".join(p.text for p in doc.paragraphs)


def check_codebase_evidence(codebase_root, skill_keywords):
    """
    Search the codebase for evidence of claimed skills.
    Returns dict: skill -> (found: bool, location: str)
    """
    if not codebase_root or not os.path.isdir(codebase_root):
        return {k: (False, "no codebase") for k in skill_keywords}

    results = {}
    for skill in skill_keywords:
        found_files = []
        # Search for the skill name and common variants
        patterns = [skill.lower()]
        # Add common variant patterns
        if "pytorch" in skill.lower():
            patterns.append("torch")
        if "tensorflow" in skill.lower():
            patterns.append("tf.")
        if "aws" in skill.lower():
            patterns.append("boto")
        if "gcp" in skill.lower():
            patterns.append("google-cloud")
        if "azure" in skill.lower():
            patterns.append("azure")
        if "docker" in skill.lower():
            patterns.append("dockerfile")
        if "kubernetes" in skill.lower() or "k8s" in skill.lower():
            patterns.append("kubernetes")
            patterns.append("k8s")
            patterns.append("kubectl")

        for pattern in patterns:
            try:
                result = subprocess.run(
                    ["grep", "-rl", pattern, codebase_root],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0 and result.stdout.strip():
                    for f in result.stdout.strip().split("\n")[:5]:
                        rel = os.path.relpath(f, codebase_root)
                        found_files.append(rel)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        found = len(found_files) > 0
        location = "; ".join(found_files[:3]) if found_files else ""
        results[skill] = (found, location)

    return results


def compute_match(cv_text, jd, codebase_evidence):
    """
    Build match matrix: each JD requirement -> EXACT / PARTIAL / MISSING
    with evidence location.
    """
    cv_lower = cv_text.lower()
    required_skills = jd.get("required_skills", [])
    if isinstance(required_skills, str):
        required_skills = [s.strip() for s in required_skills.split(",")]

    secondary_skills = jd.get("secondary_skills", [])
    if isinstance(secondary_skills, str):
        secondary_skills = [s.strip() for s in secondary_skills.split(",")]

    all_skills = required_skills + secondary_skills

    match_details = []
    gaps = []
    exact_count = 0
    total_count = len(all_skills)

    for skill in all_skills:
        skill_lower = skill.lower()
        cv_has = skill_lower in cv_lower

        # Check codebase evidence
        cb_found, cb_location = codebase_evidence.get(skill, (False, ""))

        if cv_has and cb_found:
            status = "EXACT"
            evidence = f"CV + codebase: {cb_location}"
            exact_count += 1
        elif cv_has:
            status = "PARTIAL"
            evidence = "CV: present, codebase: not found"
        elif cb_found:
            status = "PARTIAL"
            evidence = f"codebase: {cb_location}, CV: absent"
        else:
            status = "MISSING"
            evidence = "absent from both CV and codebase"
            gaps.append({
                "skill": skill,
                "note": f"Not found in CV or codebase",
                "required": skill in required_skills
            })

        match_details.append({
            "skill": skill,
            "status": status,
            "evidence": evidence,
            "required": skill in required_skills
        })

    fit_pct = round(exact_count / total_count * 100) if total_count > 0 else 0
    if fit_pct >= 80:
        fit_label = "HIGH"
    elif fit_pct >= 60:
        fit_label = "MEDIUM"
    else:
        fit_label = "LOW"

    fit_score = f"{fit_label} ({fit_pct}%)"

    return {
        "fit_score": fit_score,
        "fit_pct": fit_pct,
        "fit_label": fit_label,
        "match_details": match_details,
        "gaps": gaps,
        "total_skills": total_count,
        "exact_matches": exact_count,
    }


def main():
    parser = argparse.ArgumentParser(description="JD-to-CV Match Tool")
    parser.add_argument("--cv", required=True, help="Path to CV .docx")
    parser.add_argument("--jd-json", required=True, help="Path to JD JSON")
    parser.add_argument("--codebase", help="Path to codebase root (optional)")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    cv_text = read_cv_text(args.cv)

    with open(args.jd_json) as f:
        jd = json.load(f)

    # Extract skill keywords from JD
    skill_keywords = []
    for field in ["required_skills", "secondary_skills", "skills"]:
        val = jd.get(field, [])
        if isinstance(val, str):
            val = [s.strip() for s in val.split(",")]
        skill_keywords.extend(val)

    # Also add JD title keywords
    title = jd.get("title", "")
    if title:
        skill_keywords.append(title)

    # Deduplicate
    skill_keywords = list(dict.fromkeys(skill_keywords))

    codebase_evidence = check_codebase_evidence(args.codebase, skill_keywords)
    result = compute_match(cv_text, jd, codebase_evidence)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
