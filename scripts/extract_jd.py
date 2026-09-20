#!/usr/bin/env python3
"""
extract_jd.py — Job Description Extraction Tool

Pulls the full job description from a posting URL. Uses web_extract as primary,
falls back to web_search for gated/blocked pages (Indeed, LinkedIn, Greenhouse, etc.).

Usage:
  python extract_jd.py \
    --url https://jobs.ashbyhq.com/openai/... \
    --company OpenAI \
    --role "Applied AI Engineer" \
    --platform ashby \
    --output jd.json

Output jd.json:
  {
    "title": "Applied AI Engineer",
    "company": "OpenAI",
    "location": "Abu Dhabi, UAE",
    "apply_url": "https://jobs.ashbyhq.com/openai/...",
    "url": "https://jobs.ashbyhq.com/openai/...",
    "platform": "ashby",
    "posted_date": "2026-09-18",
    "type": "Full-time",
    "years_exp": "",
    "degree": "",
    "salary": "",
    "required_skills": ["Python", "RAG", "LLM", ...],
    "full_jd": "Full extracted job description text..."
  }
"""

import argparse
import json
import re
import sys
from datetime import date

TODAY = date.today().isoformat()


# Signals that a job is dead (from verify_links.py kill signals)
KILL_SIGNALS = [
    "no longer accepting applications",
    "has been filled",
    "job not found",
    "this position has been closed",
    "applications are closed",
    "position filled",
]


def _lazy_hermes_tools():
    """Lazy import hermes_tools — only available inside Hermes runtime."""
    try:
        from hermes_tools import web_search, web_extract
        return web_search, web_extract
    except ImportError:
        return None, None


def extract_jd_from_url(url, company, role, platform):
    """
    Primary: web_extract on the apply URL.
    Fallback: web_search for cached/indexed versions when extract is blocked.
    Returns a structured JD dict.
    """
    web_search_fn, web_extract_fn = _lazy_hermes_tools()
    if web_extract_fn is None:
        return {
            "title": role, "company": company, "location": "",
            "apply_url": url, "url": url, "platform": platform,
            "posted_date": TODAY, "type": "", "years_exp": "",
            "degree": "", "salary": "", "required_skills": [],
            "full_jd": "(hermes_tools not available — run inside Hermes)",
            "extraction_source": "FAILED",
        }

    jd = {
        "title": role,
        "company": company,
        "location": "",
        "apply_url": url,
        "url": url,
        "platform": platform,
        "posted_date": TODAY,
        "type": "",
        "years_exp": "",
        "degree": "",
        "salary": "",
        "required_skills": [],
        "full_jd": "",
        "extraction_source": "",
    }

    # Primary: direct extract
    r = web_extract_fn([url])
    entries = r.get("results", [{}])

    if entries and not entries[0].get("error"):
        content = entries[0].get("content", "")
        jd["full_jd"] = content
        jd["extraction_source"] = "direct"
        jd = _parse_jd_fields(jd, content)
        return jd

    # Extract returned an error or empty — try search fallback
    domain = url.split("/")[2] if len(url.split("/")) > 2 else ""

    # Try the domain directly
    search_results = web_search_fn(f'"{company}" "{role}" site:{domain}')
    web_hits = search_results.get("data", {}).get("web", [])

    if web_hits:
        # Merge snippets — often the full JD is in the description field
        snippets = []
        for hit in web_hits:
            desc = hit.get("description", "")
            title = hit.get("title", "")
            if desc:
                snippets.append(desc)
            if title and title != role:
                snippets.append(title)

        if snippets:
            jd["full_jd"] = "\n\n---\n\n".join(snippets)
            jd["extraction_source"] = "search_fallback"
            jd = _parse_jd_fields(jd, jd["full_jd"])

            # Check for kill signals in the snippets
            combined = " ".join(snippets).lower()
            for signal in KILL_SIGNALS:
                if signal in combined:
                    jd["status"] = "DEAD"
                    jd["kill_signal"] = signal
                    return jd

            # Check for freshness signals
            for hit in web_hits:
                desc = hit.get("description", "").lower()
                if "days ago" in desc or "be among" in desc:
                    jd["freshness_signal"] = "found in search snippet"
                    break

            return jd

    # Also try LinkedIn and Indeed indexed versions
    for search_site in ["linkedin.com/jobs", "indeed.ae", "naukrigulf.com"]:
        alt_results = web_search_fn(f'"{company}" "{role}" site:{search_site}')
        alt_hits = alt_results.get("data", {}).get("web", [])
        if alt_hits:
            alt_snippets = [h.get("description", "") for h in alt_hits if h.get("description")]
            if alt_snippets:
                jd["full_jd"] = "\n\n---\n\n".join(alt_snippets)
                jd["extraction_source"] = f"search_fallback:{search_site}"
                jd = _parse_jd_fields(jd, jd["full_jd"])
                return jd

    # All sources failed
    jd["extraction_source"] = "FAILED"
    jd["full_jd"] = "(could not extract — all sources blocked or returned no content)"
    return jd


def _parse_jd_fields(jd, text):
    """
    Attempt to extract structured fields from raw JD text.
    This is best-effort — many JDs don't have clean field boundaries.
    """
    lower = text.lower()

    # Location
    loc_patterns = [
        r"(\w+\s*,\s*\w+\s*\(?\w{2}\)?)",  # "City, Country (AE)"
        r"(\w+\s*,\s*\w+)",                    # "City, Country"
        r"based\s+in\s+([^\n.]+)",
        r"location:\s*([^\n]+)",
        r"office\s+:\s*([^\n]+)",
    ]
    for pat in loc_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            jd["location"] = m.group(1).strip()
            break

    # Employment type
    type_map = {
        "full.time": "Full-time",
        "full time": "Full-time",
        "part.time": "Part-time",
        "part time": "Part-time",
        "contract": "Contract",
        "intern": "Internship",
        "remote": "Remote",
    }
    for key, val in type_map.items():
        if key in lower:
            jd["type"] = val
            break

    # Years of experience
    yr_m = re.search(r"(\d+)\s*(?:\+?\s*)?years?\s+of\s+experience", lower)
    if yr_m:
        jd["years_exp"] = yr_m.group(1)

    # Degree
    degree_m = re.search(r"(master|phd|ph\.d|bachelor|m\.?sc|b\.?sc|mba)\s+(?:degree\s+)?(?:in\s+)?(?:computer\s+)?(?:science|engineering|technology|ai|ml)", lower)
    if degree_m:
        jd["degree"] = degree_m.group(0).title()

    # Salary
    sal_m = re.search(r"(\d{3,6})\s*(k|kynix|k\d|\d{3,6}\s*[\u20AC$£])", text)
    if sal_m:
        jd["salary"] = sal_m.group(0)

    # Required skills — extract from a "skills" or "requirements" section
    # Look for bullet lists after "requirements", "skills", "qualifications"
    skills_section_m = re.search(
        r"(?:requirements|skills|qualifications|you\s+will|what\s+you\s+bring)[:\s]*\n(.{50,2000})",
        text, re.IGNORECASE | re.DOTALL
    )
    if skills_section_m:
        section_text = skills_section_m.group(1)
        # Split on bullets, numbers, or commas
        items = re.split(r"\n\s*[-•]\s*|\n\s*\d+\.\s*|\n\s*\*\s*", section_text)
        skills = []
        for item in items:
            item = item.strip()
            if len(item) > 3 and len(item) < 120 and not item.lower().startswith(("you", "we", "the", "our", "this", "description", "role")):
                skills.append(item)
        jd["required_skills"] = skills[:20]  # cap at 20

    return jd


def main():
    parser = argparse.ArgumentParser(description="Job Description Extraction Tool")
    parser.add_argument("--url", required=True, help="Apply URL to extract JD from")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--role", required=True, help="Job role title")
    parser.add_argument("--platform", default="unknown", help="Platform name (ashby, greenhouse, linkedin, indeed, etc.)")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    jd = extract_jd_from_url(args.url, args.company, args.role, args.platform)

    # Add metadata
    jd["extracted_at"] = TODAY

    with open(args.output, "w") as f:
        json.dump(jd, f, indent=2)

    # Summary to stdout
    status = jd.get("status", "LIVE")
    source = jd.get("extraction_source", "unknown")
    print(f"Extracted: {args.company} — {args.role}")
    print(f"Source: {source} | Status: {status}")
    print(f"Skills found: {len(jd.get('required_skills', []))}")
    print(f"Location: {jd.get('location', 'not found')}")
    print(f"Type: {jd.get('type', 'not found')}")
    print(f"Years exp: {jd.get('years_exp', 'not found')}")
    print(f"Degree: {jd.get('degree', 'not found')}")
    print()
    print(json.dumps(jd, indent=2))


if __name__ == "__main__":
    main()
