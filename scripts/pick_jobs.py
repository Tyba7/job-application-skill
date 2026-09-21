#!/usr/bin/env python3
"""
Ask the user to review and pick 5 jobs from the discovered list.
Runs after Phase 1 (discover), before Phase 2 (verify).
"""

import json
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python pick_jobs.py <discovered_jobs.json>")
        sys.exit(1)

    jobs_file = sys.argv[1]
    with open(jobs_file) as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    print(f"\n{'='*70}")
    print(f"DISCOVERED {len(jobs)} JOBS — PICK 5 TO PROCEED")
    print(f"{'='*70}\n")

    for i, job in enumerate(jobs, 1):
        company = job.get("company", "—").strip()
        role = job.get("role", "—")
        url = job.get("apply_url", "—")
        platform = job.get("platform", "—")
        desc = job.get("description", "")
        print(f"{i:2d}. [{platform}] {company}")
        print(f"    Role: {role}")
        print(f"    URL:  {url}")
        if desc:
            print(f"    Desc: {desc[:120]}")
        print()

    print(f"{'='*70}")
    print("Enter the numbers of the jobs you want to proceed with (e.g. 1 3 5 7 9)")
    print("Or press Enter to skip this step and exit.")
    print(f"{'='*70}\n")

    try:
        selection = input("Your selection (space-separated numbers): ").strip()
    except EOFError:
        print("\nNo input — exiting.")
        sys.exit(0)

    if not selection:
        print("No selection made — exiting.")
        sys.exit(0)

    try:
        indices = [int(x) - 1 for x in selection.split()]
    except ValueError:
        print("Invalid input — numbers only.")
        sys.exit(1)

    selected = []
    for idx in indices:
        if 0 <= idx < len(jobs):
            selected.append(jobs[idx])
        else:
            print(f"Warning: index {idx+1} out of range, skipping.")

    if not selected:
        print("No valid selections — exiting.")
        sys.exit(0)

    # Write selected jobs
    out_file = os.path.join(os.path.dirname(jobs_file), "selected_jobs.json")
    with open(out_file, "w") as f:
        json.dump(selected, f, indent=2)

    print(f"\nSelected {len(selected)} jobs → {out_file}")
    for j in selected:
        print(f"  - {j.get('company','?')}: {j.get('role','?')[:50]} ({j.get('platform','?')})")

if __name__ == "__main__":
    main()
