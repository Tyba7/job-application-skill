#!/usr/bin/env python3
"""
verify_links.py — Job Link Verification Tool

Verifies whether job postings are still live. Uses web_extract as primary,
falls back to web_search for gated/blocked pages.

Usage:
  python verify_links.py \
    --links job_links.json \
    --output verification_results.json

Input job_links.json:
  [
    {"company": "G42", "role": "AI Engineer", "apply_url": "https://..."},
    ...
  ]

Output verification_results.json:
  [
    {"company": "G42", "role": "AI Engineer", "apply_url": "https://...",
     "status": "LIVE", "reason": "content extracted, no kill signals"},
    {"company": "DeadCo", "role": "Data Scientist", "apply_url": "https://...",
     "status": "DEAD", "reason": "no longer accepting applications"},
    ...
  ]
"""

import argparse
import json
import sys


def verify_single_link(job):
    """Verify one job link. Returns the job dict with status added."""
    apply_url = job.get("apply_url", "")
    company = job.get("company", "")
    role = job.get("role", "")

    KILL_SIGNALS = [
        "no longer accepting applications",
        "has been filled",
        "job not found",
        "this position has been closed",
        "applications are closed",
        "position filled",
    ]

    result = {
        "company": company,
        "role": role,
        "apply_url": apply_url,
        "status": "UNKNOWN",
        "reason": "",
    }

    # Lazy import — only available inside Hermes runtime
    try:
        from hermes_tools import web_search, web_extract
    except ImportError:
        result["status"] = "UNKNOWN (hermes_tools not available — run inside Hermes)"
        result["reason"] = "standalone execution outside Hermes runtime"
        return result

    # Primary: web_extract
    r = web_extract([apply_url])
    entries = r.get("results", [{}])

    if entries and entries[0].get("error"):
        # Extract failed — try search fallback
        domain = apply_url.split("/")[2] if len(apply_url.split("/")) > 2 else ""
        fresh = web_search(f'"{company}" "{role}" site:{domain}')
        web_results = fresh.get("data", {}).get("web", [])

        if web_results:
            descriptions = [s.get("description", "").lower() for s in web_results]
            has_fresh = any(
                "days ago" in d or "be among" in d
                for d in descriptions
            )
            has_dead = any(
                signal in d for signal in KILL_SIGNALS for d in descriptions
            )
            if has_dead:
                result["status"] = "DEAD"
                result["reason"] = "search fallback: dead signals found"
            elif has_fresh:
                result["status"] = "LIVE (via search fallback)"
                result["reason"] = "extract blocked; search shows fresh signals"
            else:
                result["status"] = "UNKNOWN (verify manually)"
                result["reason"] = "extract blocked; search inconclusive"
        else:
            result["status"] = "UNKNOWN (verify manually)"
            result["reason"] = "extract failed; no search results"
    else:
        body = entries[0].get("content", "").lower() if entries else ""
        for signal in KILL_SIGNALS:
            if signal in body:
                result["status"] = "DEAD"
                result["reason"] = f"kill signal: '{signal}'"
                break
        else:
            result["status"] = "LIVE"
            result["reason"] = "content extracted, no kill signals"

    return result


def main():
    parser = argparse.ArgumentParser(description="Job Link Verification Tool")
    parser.add_argument("--links", required=True, help="Path to job links JSON")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    with open(args.links) as f:
        jobs = json.load(f)

    results = []
    for job in jobs:
        verified = verify_single_link(job)
        results.append(verified)

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    # Also print summary to stdout
    live = sum(1 for r in results if r["status"] == "LIVE" or "LIVE" in r["status"])
    dead = sum(1 for r in results if r["status"] == "DEAD")
    unknown = len(results) - live - dead
    print(f"Verified: {len(results)} | LIVE: {live} | DEAD: {dead} | UNKNOWN: {unknown}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
