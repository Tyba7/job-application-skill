#!/usr/bin/env python3
"""
track_applications.py — Application Tracker Regenerator

Regenerates the applications.csv tracker from folder ground truth.
Never appends — always rebuilds from what's actually on disk.

Usage:
  python track_applications.py \
    --root /Users/tayyabarizwan/vestwell_contact_center/applications/2026-09-18 \
    --output /Users/tayyabarizwan/vestwell_contact_center/applications/2026-09-18/applications.csv

Reads each company subfolder, detects what files exist (cv.docx, cover_letter.docx,
jd.xlsx, README.md), and writes one CSV row per company with the correct status.

CSV columns:
  priority,company,role,location,status,apply_link,apply_route,folder,cv_file,
  cover_letter,jd_xlsx,readme,notes
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import date

TODAY = date.today().isoformat()

# Status inference from folder contents
STATUS_FROM_FILES = {
    # No files at all
    frozenset(): "DISCOVERED",
    # Just a README (role identified but no docs)
    frozenset(["README.md"]): "RESEARCHED",
    # JD extracted
    frozenset(["jd.xlsx"]): "EXTRACTED",
    # JD + README
    frozenset(["jd.xlsx", "README.md"]): "EXTRACTED",
    # CV generated
    frozenset(["cv.docx"]): "GENERATED",
    # CV + README
    frozenset(["cv.docx", "README.md"]): "GENERATED",
    # CV + cover letter
    frozenset(["cv.docx", "cover_letter.docx"]): "QA-PASS",
    # Full set
    frozenset(["cv.docx", "cover_letter.docx", "jd.xlsx", "README.md"]): "APPLIED",
    # CV + CL + README
    frozenset(["cv.docx", "cover_letter.docx", "README.md"]): "QA-PASS",
    # CV + CL + jd
    frozenset(["cv.docx", "cover_letter.docx", "jd.xlsx"]): "QA-PASS",
}

# Status override markers — if a folder contains a STATUS file, use it
STATUS_FILE = "status.txt"


def infer_status(files):
    """Infer application status from the set of files in a folder."""
    file_set = frozenset(files)
    # Check for explicit status file first
    if STATUS_FILE in files:
        return "CUSTOM"

    # Match against known patterns (most specific first)
    for known_set, status in sorted(STATUS_FROM_FILES.items(),
                                      key=lambda x: -len(x[0])):
        if file_set == known_set:
            return status

    # Partial matches — find the closest known state
    if "cv.docx" in file_set and "cover_letter.docx" in file_set:
        return "QA-PASS"
    if "cv.docx" in file_set:
        return "GENERATED"
    if "jd.xlsx" in file_set:
        return "EXTRACTED"
    if "README.md" in file_set:
        return "RESEARCHED"
    return "DISCOVERED"


def extract_role_from_readme(readme_path):
    """Try to extract role title from README.md content."""
    if not os.path.exists(readme_path):
        return ""
    with open(readme_path) as f:
        content = f.read()
    # Try "— Role" pattern: "# Company — Role"
    m = re.search(r"# .+? — (.+)", content)
    if m:
        return m.group(1).strip()
    # Try first heading
    lines = content.split("\n")
    for line in lines[:5]:
        if line.startswith("# "):
            # Strip the company name, leave the role
            parts = line[2:].split("—")
            if len(parts) > 1:
                return parts[-1].strip()
            return line[2:].strip()
    return ""


def extract_apply_url_from_readme(readme_path):
    """Extract apply URL from README.md."""
    if not os.path.exists(readme_path):
        return ""
    with open(readme_path) as f:
        content = f.read()
    m = re.search(r"\[?Apply.*?\]\((https?://[^\)]+)\)", content)
    if m:
        return m.group(1)
    # Try bare URL
    m = re.search(r"(https?://[^\s)]+)", content)
    if m:
        return m.group(1)
    return ""


def extract_company_from_folder(folder_name):
    """Extract company name from folder name."""
    return folder_name


def regenerate_tracker(root_dir, output_path, manual_entries=None):
    """
    Walk the root directory, find company subfolders, and regenerate the CSV.
    manual_entries: optional dict of company -> extra notes to include.
    """
    if not os.path.isdir(root_dir):
        print(f"ERROR: {root_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    rows = []
    companies = sorted(os.listdir(root_dir))

    for company in companies:
        company_dir = os.path.join(root_dir, company)
        if not os.path.isdir(company_dir):
            continue

        # Skip hidden and system files
        if company.startswith("."):
            continue

        files = os.listdir(company_dir)
        # Filter to relevant files
        relevant_files = [
            f for f in files
            if f.endswith((".docx", ".xlsx", ".md", ".txt"))
            and not f.startswith("~$")
        ]

        status = infer_status(relevant_files)

        # Extract role from README
        readme_path = os.path.join(company_dir, "README.md")
        role = extract_role_from_readme(readme_path)

        # Extract apply URL from README
        apply_url = extract_apply_url_from_readme(readme_path)

        # Detect CV file
        cv_files = [f for f in relevant_files if f.endswith(".docx") and f.startswith("CV_")]
        cv_file = cv_files[0] if cv_files else ""

        # Detect cover letter
        cl_files = [f for f in relevant_files if f.endswith(".docx") and f.startswith("CoverLetter_")]
        cover_letter = cl_files[0] if cl_files else ""

        # Detect jd.xlsx
        jd_xlsx = "jd.xlsx" if "jd.xlsx" in relevant_files else ""

        # Notes
        notes = ""
        if manual_entries and company in manual_entries:
            notes = manual_entries[company]

        # Priority — default to 3, can be overridden
        priority = 3

        row = {
            "priority": priority,
            "company": company,
            "role": role,
            "location": "",
            "status": status,
            "apply_link": apply_url,
            "apply_route": "",
            "folder": company,
            "cv_file": cv_file,
            "cover_letter": cover_letter,
            "jd_xlsx": jd_xlsx,
            "readme": "README.md" if "README.md" in relevant_files else "",
            "notes": notes,
        }
        rows.append(row)

    # Sort by priority, then company
    rows.sort(key=lambda r: (r["priority"], r["company"]))

    # Write CSV
    fieldnames = [
        "priority", "company", "role", "location", "status",
        "apply_link", "apply_route", "folder", "cv_file",
        "cover_letter", "jd_xlsx", "readme", "notes"
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    status_counts = {}
    for row in rows:
        s = row["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    print(f"Tracker regenerated: {len(rows)} companies")
    print(f"Status breakdown: {status_counts}")
    print(f"Output: {output_path}")

    # Also print the CSV content for verification
    print()
    print("--- CSV preview ---")
    with open(output_path) as f:
        print(f.read())


def main():
    parser = argparse.ArgumentParser(description="Application Tracker Regenerator")
    parser.add_argument("--root", required=True, help="Root applications folder")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument("--manual-notes", help="JSON file with company -> notes mapping")
    args = parser.parse_args()

    manual_entries = {}
    if args.manual_notes and os.path.exists(args.manual_notes):
        with open(args.manual_notes) as f:
            manual_entries = json.load(f)

    regenerate_tracker(args.root, args.output, manual_entries)


if __name__ == "__main__":
    main()
