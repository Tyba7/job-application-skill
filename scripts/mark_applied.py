#!/usr/bin/env python3
"""
mark_applied.py — Explicit "I actually submitted this" marker.

Guardrail: track_applications.py never infers APPLIED from rendered files.
The only way a company folder counts as APPLIED is this script writing
APPLIED_ON.txt into it — after YOU confirm you clicked submit on the real
job board. This exists because the pipeline previously auto-labeled every
folder with CV+CoverLetter+jd.xlsx+README as APPLIED, which was false —
"documents exist" is not "I applied."

Usage:
  python mark_applied.py --root applications/2026-09-25 --company "G42"
  python mark_applied.py --root applications/2026-09-25 --company "G42" --date 2026-09-24
  python mark_applied.py --root applications/2026-09-25 --unmark --company "G42"

After marking, re-run track_applications.py to regenerate the CSV with the
corrected status.
"""
import argparse
import os
import sys
from datetime import date


def main():
    parser = argparse.ArgumentParser(description="Mark a company folder as genuinely applied-to")
    parser.add_argument("--root", required=True, help="Root applications/<date> folder")
    parser.add_argument("--company", required=True, help="Company folder name (exact match)")
    parser.add_argument("--date", default=date.today().isoformat(), help="Date actually applied (ISO), default today")
    parser.add_argument("--unmark", action="store_true", help="Remove the APPLIED marker instead of adding it")
    args = parser.parse_args()

    company_dir = os.path.join(args.root, args.company)
    if not os.path.isdir(company_dir):
        print(f"ERROR: no folder at {company_dir}", file=sys.stderr)
        sys.exit(1)

    marker_path = os.path.join(company_dir, "APPLIED_ON.txt")

    if args.unmark:
        if os.path.exists(marker_path):
            os.remove(marker_path)
            print(f"Unmarked: {marker_path} removed")
        else:
            print(f"Nothing to unmark: {marker_path} did not exist")
        return

    with open(marker_path, "w") as f:
        f.write(args.date + "\n")
    print(f"Marked APPLIED: {marker_path} = {args.date}")
    print("Run track_applications.py to regenerate the CSV with this status.")


if __name__ == "__main__":
    main()
