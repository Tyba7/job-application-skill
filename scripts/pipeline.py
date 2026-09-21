#!/usr/bin/env python3
"""
pipeline.py — End-to-end Job Application Pipeline Orchestrator

Chains all 8 tools sequentially. Each tool's output feeds the next.
Stops only on fatal errors; non-fatal failures (dead links, extraction
failures) are logged and the pipeline continues.

Usage:
    python pipeline.py --query "AI engineer UAE" --max-jobs 20 --output-dir ../../applications/2026-09-20

Requirements:
    - Run inside Hermes runtime (hermes_tools must be available)
    - gh CLI authenticated (for github_track at the end)
"""

import argparse
import json
import os
import sys
import subprocess
from datetime import date, timezone
from pathlib import Path

# ── Lazy hermes_tools import — must be inside main(), not module level ─────

HERMES_AVAILABLE = False
HERMES_WEB_SEARCH = None
HERMES_WEB_EXTRACT = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATE_STR = date.today().isoformat()


def log(msg):
    print(f"[pipeline] {msg}", flush=True)


def fail(msg):
    print(f"[pipeline] ERROR: {msg}", file=sys.stderr, flush=True)


def get_hermes_tools():
    """Lazy import hermes_tools — only available inside Hermes runtime."""
    global HERMES_WEB_SEARCH, HERMES_WEB_EXTRACT, HERMES_AVAILABLE
    if HERMES_WEB_SEARCH is not None:
        return HERMES_WEB_SEARCH, HERMES_WEB_EXTRACT
    try:
        from hermes_tools import web_search, web_extract
        HERMES_WEB_SEARCH = web_search
        HERMES_WEB_EXTRACT = web_extract
        HERMES_AVAILABLE = True
        return web_search, web_extract
    except ImportError:
        HERMES_AVAILABLE = False
        return None, None


# ── Phase 1: Discover ───────────────────────────────────────────────────────

def phase1_discover(query: str, max_jobs: int, output_dir: str) -> list[dict]:
    """Search multiple platforms for UAE AI/ML jobs. Returns ranked list."""
    log(f"Phase 1: Discovering jobs for '{query}' (max {max_jobs})")

    web_search_fn, _ = get_hermes_tools()
    if web_search_fn is None:
        fail("hermes_tools not available — run inside Hermes")
        return []

    # Discovery queries — targeted to surface individual job postings, not
    # category/aggregator pages. Each query names a specific company, role, or
    # platform known to host UAE AI/ML listings.
    platforms = [
        # Indeed — specific role + location queries (not generic "AI engineer UAE")
        f"AI Engineer Abu Dhabi site:indeed.ae",
        f"Machine Learning Engineer Dubai site:indeed.ae",
        f"LLM Engineer UAE site:indeed.ae",
        f"GenAI Engineer Dubai site:indeed.ae",
        f"AI Research Engineer Abu Dhabi site:indeed.ae",
        # Bayt — specific role pages
        f"AI Engineer UAE site:bayt.com",
        f"ML Engineer Abu Dhabi site:bayt.com",
        f"GenAI Engineer UAE site:bayt.com",
        # LinkedIn
        f"AI Engineer Dubai site:linkedin.com/jobs",
        f"Machine Learning Engineer UAE site:linkedin.com/jobs",
        # NaukriGulf
        f"AI Engineer Dubai site:naukrigulf.com",
        f"ML Engineer Abu Dhabi site:naukrigulf.com",
        # User-requested additions
        f"AI Engineer UAE site:remote.com",
        f"Machine Learning Engineer UAE site:himalayas.app",
    ]

    platform_names = [
        "Indeed: AI Eng Abu Dhabi",
        "Indeed: ML Eng Dubai",
        "Indeed: LLM Eng UAE",
        "Indeed: GenAI Eng Dubai",
        "Indeed: AI Research Eng Abu Dhabi",
        "Bayt: AI Engineer UAE",
        "Bayt: ML Engineer Abu Dhabi",
        "Bayt: GenAI Engineer UAE",
        "LinkedIn: AI Engineer Dubai",
        "LinkedIn: ML Engineer UAE",
        "Naukrigulf: AI Engineer Dubai",
        "Naukrigulf: ML Engineer Abu Dhabi",
        "Remote.com: AI Engineer UAE",
        "Himalayas: ML Engineer UAE",
    ]

    all_jobs = []
    seen_urls = set()

    for i, search_query in enumerate(platforms):
        log(f"  Searching platform {i+1}/7: {search_query[:60]}...")
        try:
            results = web_search_fn(search_query, limit=10)
            for item in results.get("data", {}).get("web", []):
                url = item.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title = item.get("title", "").strip()
                desc = item.get("description", "").strip()

                # Job-quality filter: distinguish real postings from aggregator/list pages.
                # Primary signal is body content. Title-level "N+ Role Jobs, Employment DATE"
                # pattern is a weak secondary signal because Indeed shows both categories and
                # individual listings via search results with the same title format.
                desc_lower = desc.lower()
                title_lower = title.lower()
                body_is_list = any(s in desc_lower for s in [
                    "discover ", "find ", "search ", "results ", "view all",
                    "make your job", "job opportunities in",
                ])
                title_looks_category = "employment" in title_lower and "+" in title
                has_posting = any(s in desc_lower for s in [
                    "we are seeking", "we are looking", "responsibilities",
                    "requirements", "qualifications", "about the role",
                    "the ideal candidate", "your role", "your responsibilities",
                    "you will", "this role", "based in", "our client",
                ])
                # Skip if the body clearly reads like a list/category page
                if body_is_list:
                    continue
                # Skip obvious category-page titles when the body has no posting language
                if title_looks_category and not has_posting:
                    continue
                # Skip if no posting-specific language AND no engineer/hiring signal
                if not has_posting and "engineer" not in title_lower and "hiring" not in desc_lower:
                    continue

                all_jobs.append({
                    "company": "",
                    "role": title,
                    "platform": platform_names[i],
                    "apply_url": url,
                    "posted": "",
                    "description": desc[:300],
                    "relevance": 0,  # will be scored later
                })
        except Exception as e:
            log(f"  Platform {i+1} error: {e}")

    # Basic company extraction from URL or title
    for job in all_jobs:
        # Try to extract company from title "Role at Company"
        title = job["role"]
        if " at " in title:
            parts = title.split(" at ", 1)
            job["role"] = parts[0].strip()
            job["company"] = parts[1].strip()
        elif " - " in title:
            parts = title.split(" - ", 1)
            job["role"] = parts[0].strip()
            job["company"] = parts[1].strip()

    # Limit to max_jobs, sorted by relevance (basic: prefer recent-looking)
    all_jobs = all_jobs[:max_jobs]

    # Write intermediate result
    jobs_file = os.path.join(output_dir, "discovered_jobs.json")
    with open(jobs_file, "w") as f:
        json.dump({"query": query, "timestamp": DATE_STR, "total": len(all_jobs), "jobs": all_jobs}, f, indent=2)

    log(f"  Discovered {len(all_jobs)} jobs → {jobs_file}")
    return all_jobs


# ── Phase 1b: GitHub Discover (supplementary) ──────────────────────────────

def phase1b_github_discover(query: str, output_dir: str) -> list[dict]:
    """Run github_discover.py as supplementary source."""
    log("Phase 1b: GitHub supplementary discovery")

    script = os.path.join(SCRIPT_DIR, "github_discover.py")
    output_file = os.path.join(output_dir, "github_jobs.json")

    try:
        result = subprocess.run(
            [sys.executable, script, "--query", query, "--output", output_file],
            capture_output=True, text=True, timeout=120,
            cwd=SCRIPT_DIR
        )
        if result.returncode == 0 and os.path.exists(output_file):
            with open(output_file) as f:
                data = json.load(f)
            jobs = data.get("results", [])
            log(f"  GitHub found {len(jobs)} additional jobs → {output_file}")
            return jobs
        else:
            log(f"  GitHub discovery returned no results (status={result.returncode})")
            return []
    except Exception as e:
        log(f"  GitHub discovery failed: {e}")
        return []


# ── Phase 2: Verify Links ───────────────────────────────────────────────────

def phase2_verify(output_dir: str) -> list[dict]:
    """Verify selected job links are still live.

    Looks for selected_jobs.json first (user-picked subset). Falls back to
    discovered_jobs.json if no selection was made.
    """
    log("Phase 2: Verifying selected links")

    selected_file = os.path.join(output_dir, "selected_jobs.json")
    discovered_file = os.path.join(output_dir, "discovered_jobs.json")

    if os.path.exists(selected_file):
        with open(selected_file) as f:
            jobs = json.load(f)
        log(f"  Using user-selected {len(jobs)} jobs from selected_jobs.json")
    elif os.path.exists(discovered_file):
        with open(discovered_file) as f:
            data = json.load(f)
        jobs = data.get("jobs", [])
        log(f"  No selection found — using all {len(jobs)} discovered jobs")
    else:
        log("  No jobs file found — skipping verification")
        return []

    if not jobs:
        return []
    links_file = os.path.join(output_dir, "links_to_verify.json")
    verified_file = os.path.join(output_dir, "verified_jobs.json")

    with open(links_file, "w") as f:
        json.dump(jobs, f, indent=2)

    script = os.path.join(SCRIPT_DIR, "verify_links.py")
    try:
        result = subprocess.run(
            [sys.executable, script, "--links", links_file, "--output", verified_file],
            capture_output=True, text=True, timeout=300,
            cwd=SCRIPT_DIR
        )
        log(f"  verify_links.py output:\n{result.stdout}")

        if result.returncode == 0 and os.path.exists(verified_file):
            with open(verified_file) as f:
                verified = json.load(f)
            live = [j for j in verified if "LIVE" in j.get("status", "")]
            dead = [j for j in verified if j.get("status") == "DEAD"]
            unknown = [j for j in verified if "LIVE" not in j.get("status", "") and j.get("status") != "DEAD"]

            log(f"  LIVE: {len(live)} | DEAD: {len(dead)} | UNKNOWN: {len(unknown)}")
            return live
        return []
    except Exception as e:
        fail(f"  Verification failed: {e}")
        return []


# ── Phase 3: Research Companies ─────────────────────────────────────────────

def phase3_research(live_jobs: list[dict], output_dir: str) -> list[dict]:
    """Research each company via web_search."""
    log(f"Phase 3: Researching {len(live_jobs)} companies")

    _, web_extract_fn = get_hermes_tools()
    if web_extract_fn is None:  # web_search is same module
        fail("hermes_tools not available — run inside Hermes")
        return []

    web_search_fn = web_extract_fn  # same hermes_tools module

    research_file = os.path.join(output_dir, "company_research.json")

    research_results = []
    for job in live_jobs:
        company = job.get("company", "") or job.get("role", "")
        if not company:
            continue

        log(f"  Researching: {company}")
        try:
            # Quick legitimacy check
            searches = [
                f'"{company}" UAE reviews',
                f'"{company}" careers site:greenhouse.io OR site:lever.co OR site:ashbyhq.com',
            ]
            findings = {}
            for s in searches:
                try:
                    r = web_search_fn(s, limit=3)
                    findings[s] = len(r.get("data", {}).get("web", []))
                except:
                    findings[s] = 0

            research_results.append({
                "company": company,
                "role": job.get("role", ""),
                "apply_url": job.get("apply_url", ""),
                "findings": findings,
                "risk": "low" if findings.get(searches[1], 0) > 0 else "medium",
            })
        except Exception as e:
            log(f"  Research error for {company}: {e}")

    with open(research_file, "w") as f:
        json.dump(research_results, f, indent=2)

    log(f"  Research complete → {research_file}")
    return research_results


# ── Phase 3b: GitHub Company Verify (optional) ──────────────────────────────

def phase3b_github_verify(research_results: list[dict], output_dir: str) -> list[dict]:
    """Run github_verify_company.py for each company."""
    log(f"Phase 3b: GitHub company verification ({len(research_results)} companies)")

    script = os.path.join(SCRIPT_DIR, "github_verify_company.py")
    all_checks = []

    for entry in research_results[:10]:  # limit to 10 to avoid excessive API calls
        company = entry.get("company", "")
        check_file = os.path.join(output_dir, f"github_check_{company.replace(' ', '_')}.json")

        try:
            result = subprocess.run(
                [sys.executable, script, "--company", company, "--output", check_file],
                capture_output=True, text=True, timeout=30,
                cwd=SCRIPT_DIR
            )
            if result.returncode in (0, 1) and os.path.exists(check_file):
                with open(check_file) as f:
                    check_data = json.load(f)
                all_checks.append(check_data)
                log(f"  {company}: risk={check_data.get('risk_level', 'unknown')}")
            else:
                log(f"  {company}: verification skipped (exit={result.returncode})")
        except Exception as e:
            log(f"  {company}: error — {e}")

    checks_file = os.path.join(output_dir, "github_company_checks.json")
    with open(checks_file, "w") as f:
        json.dump(all_checks, f, indent=2)

    log(f"  GitHub checks complete → {checks_file}")
    return all_checks


# ── Phase 4: Extract JDs ────────────────────────────────────────────────────

def phase4_extract(live_jobs: list[dict], output_dir: str) -> list[dict]:
    """Extract full JD from each live job URL."""
    log(f"Phase 4: Extracting JDs for {len(live_jobs)} jobs")

    script = os.path.join(SCRIPT_DIR, "extract_jd.py")
    jd_results = []
    company_dirs = {}

    for i, job in enumerate(live_jobs):
        company = job.get("company", "") or f"Company_{i}"
        role = job.get("role", "") or "Unknown Role"
        url = job.get("apply_url", "")

        if not url:
            log(f"  Skipping {company} — no apply URL")
            continue

        # Create company folder
        safe_company = company.replace("/", "_").replace("\\", "_")
        company_dir = os.path.join(output_dir, safe_company)
        os.makedirs(company_dir, exist_ok=True)
        company_dirs[company] = safe_company

        jd_file = os.path.join(company_dir, "jd.json")
        platform = job.get("platform", "unknown")

        log(f"  [{i+1}/{len(live_jobs)}] Extracting: {company} — {role}")
        try:
            result = subprocess.run(
                [sys.executable, script, "--url", url, "--company", company,
                 "--role", role, "--platform", platform, "--output", jd_file],
                capture_output=True, text=True, timeout=60,
                cwd=SCRIPT_DIR
            )
            log(f"    exit={result.returncode}")

            if os.path.exists(jd_file):
                with open(jd_file) as f:
                    jd_data = json.load(f)
                jd_results.append({**job, "company_dir": safe_company, "jd": jd_data})
            else:
                log(f"    FAILED — no output file")
                jd_results.append({**job, "company_dir": safe_company, "jd": None, "extract_error": True})
        except Exception as e:
            log(f"    ERROR: {e}")
            jd_results.append({**job, "company_dir": safe_company, "jd": None, "extract_error": True})

    jd_file = os.path.join(output_dir, "all_jds.json")
    with open(jd_file, "w") as f:
        json.dump(jd_results, f, indent=2)

    log(f"  JD extraction complete → {jd_file}")
    return jd_results


# ── Phase 5: Match to CV ────────────────────────────────────────────────────

def phase5_match(jd_results: list[dict], output_dir: str, cv_path: str = None) -> list[dict]:
    """Match each JD to the CV."""
    log(f"Phase 5: Matching {len(jd_results)} JDs to CV")

    if not cv_path or not os.path.exists(cv_path):
        log("  No CV found — skipping match phase")
        for jd_r in jd_results:
            jd_r["match"] = {"fit_score": "SKIPPED", "note": "No CV available"}
        return jd_results

    script = os.path.join(SCRIPT_DIR, "match_to_cv.py")
    match_results = []

    for i, jd_r in enumerate(jd_results):
        jd = jd_r.get("jd")
        if not jd:
            jd_r["match"] = {"fit_score": "FAILED", "note": "No JD extracted"}
            continue

        company_dir = os.path.join(output_dir, jd_r.get("company_dir", ""))
        jd_json = os.path.join(company_dir, "jd.json")
        match_file = os.path.join(company_dir, "match.json")

        # Write JD to temp file for the script
        with open(jd_json, "w") as f:
            json.dump(jd, f, indent=2)

        log(f"  [{i+1}/{len(jd_results)}] Matching: {jd_r.get('company', '')}")

        try:
            result = subprocess.run(
                [sys.executable, script, "--cv", cv_path, "--jd-json", jd_json,
                 "--output", match_file],
                capture_output=True, text=True, timeout=30,
                cwd=SCRIPT_DIR
            )
            if os.path.exists(match_file):
                with open(match_file) as f:
                    match_data = json.load(f)
                jd_r["match"] = match_data
                log(f"    fit={match_data.get('fit_score', '?')}")
            else:
                jd_r["match"] = {"fit_score": "ERROR", "note": result.stderr[:200]}
        except Exception as e:
            jd_r["match"] = {"fit_score": "ERROR", "note": str(e)}

    return jd_results


# ── Phase 6: Render Documents ───────────────────────────────────────────────

def phase6_render(jd_results: list[dict], output_dir: str, cv_path: str = None) -> list[dict]:
    """Render CV + cover letter + README + jd.xlsx for each job."""
    log(f"Phase 6: Rendering documents for {len(jd_results)} jobs")

    if not cv_path or not os.path.exists(cv_path):
        log("  No CV found — skipping render phase")
        return jd_results

    script = os.path.join(SCRIPT_DIR, "renderer.py")

    for i, jd_r in enumerate(jd_results):
        jd = jd_r.get("jd")
        if not jd:
            log(f"  [{i+1}/{len(jd_results)}] Skipping {jd_r.get('company', '')} — no JD")
            continue

        company_dir = os.path.join(output_dir, jd_r.get("company_dir", ""))
        company = jd_r.get("company", "")
        role = jd_r.get("role", jd.get("title", "Unknown"))

        log(f"  [{i+1}/{len(jd_results)}] Rendering: {company} — {role}")

        try:
            result = subprocess.run(
                [sys.executable, script, "--cv-base", cv_path, "--jd-json", os.path.join(company_dir, "jd.json"),
                 "--output-dir", company_dir, "--company", company, "--role", role],
                capture_output=True, text=True, timeout=30,
                cwd=SCRIPT_DIR
            )
            if result.returncode == 0:
                log(f"    OK — documents written to {company_dir}")
            else:
                log(f"    FAILED: {result.stderr[:200]}")
        except Exception as e:
            log(f"    ERROR: {e}")

    return jd_results


# ── Phase 7: QA Check ───────────────────────────────────────────────────────

def phase7_qa(jd_results: list[dict], output_dir: str) -> list[dict]:
    """Run QA checks on rendered CVs."""
    log(f"Phase 7: QA checking rendered CVs")

    script = os.path.join(SCRIPT_DIR, "qa_check.py")

    for i, jd_r in enumerate(jd_results):
        company_dir = os.path.join(output_dir, jd_r.get("company_dir", ""))
        if not os.path.isdir(company_dir):
            continue

        cv_files = [f for f in os.listdir(company_dir) if f.startswith("CV_") and f.endswith(".docx")]
        if not cv_files:
            log(f"  [{i+1}/{len(jd_results)}] No CV found in {company_dir}")
            continue

        cv_path = os.path.join(company_dir, cv_files[0])
        qa_file = os.path.join(company_dir, "qa_report.json")

        log(f"  [{i+1}/{len(jd_results)}] QA: {os.path.basename(cv_path)}")
        try:
            result = subprocess.run(
                [sys.executable, script, "--cv", cv_path, "--must-keys", "Python,RAG,LLM",
                 "--expected-links", "1", "--output", qa_file],
                capture_output=True, text=True, timeout=30,
                cwd=SCRIPT_DIR
            )
            if result.returncode == 0:
                log(f"    exit=0")
            else:
                log(f"    exit={result.returncode}")
        except Exception as e:
            log(f"    ERROR: {e}")

    log("  QA complete")
    return jd_results


# ── Phase 8: Track Applications ─────────────────────────────────────────────

def phase8_track(jd_results: list[dict], output_dir: str, repo: str = None) -> None:
    """Regenerate local CSV tracker and optionally push to GitHub."""
    log("Phase 8: Tracking applications")

    # Regenerate local CSV from folder structure
    csv_script = os.path.join(SCRIPT_DIR, "track_applications.py")
    csv_output = os.path.join(output_dir, "applications.csv")

    try:
        result = subprocess.run(
            [sys.executable, csv_script, "--root", output_dir, "--output", csv_output],
            capture_output=True, text=True, timeout=30,
            cwd=SCRIPT_DIR
        )
        log(f"  Local CSV → {csv_output}")
        if result.stdout:
            # Print the summary lines
            for line in result.stdout.split("\n")[:5]:
                log(f"    {line}")
    except Exception as e:
        fail(f"  CSV tracking failed: {e}")

    # GitHub tracking (optional)
    if repo:
        log(f"  GitHub tracking to {repo}")
        gh_script = os.path.join(SCRIPT_DIR, "github_track.py")

        for jd_r in jd_results:
            company_dir = os.path.join(output_dir, jd_r.get("company_dir", ""))
            if not os.path.isdir(company_dir):
                continue

            readme_path = os.path.join(company_dir, "README.md")
            apply_url = ""
            role = jd_r.get("role", "")
            if os.path.exists(readme_path):
                with open(readme_path) as f:
                    content = f.read()
                import re
                m = re.search(r"\[Apply:\]\((https?://[^\)]+)\)", content)
                if m:
                    apply_url = m.group(1)

            if apply_url:
                try:
                    subprocess.run(
                        [sys.executable, gh_script, "--repo", repo, "--action", "add",
                         "--company", jd_r.get("company", ""), "--role", role,
                         "--location", "UAE", "--url", apply_url, "--platform", "pipeline",
                         "--notes", f"Auto-tracked by pipeline on {DATE_STR}"],
                        capture_output=True, text=True, timeout=30,
                        cwd=SCRIPT_DIR
                    )
                except Exception as e:
                    log(f"  GitHub track error for {jd_r.get('company', '')}: {e}")

    log("  Tracking complete")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="End-to-end Job Application Pipeline")
    parser.add_argument("--query", required=True, help="Job search query (e.g. 'AI engineer UAE')")
    parser.add_argument("--max-jobs", type=int, default=20, help="Maximum jobs to discover")
    parser.add_argument("--output-dir", required=True, help="Output directory for all artifacts")
    parser.add_argument("--cv", help="Path to base CV .docx (optional — skip render/match if omitted)")
    parser.add_argument("--github-repo", help="GitHub repo for tracking (e.g. OWNER/job-tracker)")
    parser.add_argument("--steps", help="Comma-separated phase numbers to run (default: all). e.g. '1,2,4'")
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Determine which phases to run
    all_steps = [1, 1, 2, 3, 3, 4, 5, 6, 7, 8]  # 1b,3b use same numbers
    if args.steps:
        wanted = set(int(s.strip().rstrip("bc")) for s in args.steps.split(","))
    else:
        wanted = set(all_steps)

    log(f"Pipeline starting — query='{args.query}', output={output_dir}")
    log(f"Phases: {sorted(wanted)}")
    log(f"CV: {args.cv or 'not provided'}")
    log(f"GitHub repo: {args.github_repo or 'not configured'}")

    # Phase 1: Discover — prefer manual job list if available, fall back to web search
    if 1 in wanted:
        manual_file = os.path.join(output_dir, "manual_jobs.json")
        if os.path.exists(manual_file):
            with open(manual_file) as f:
                manual_jobs = json.load(f)
            # Transform into discovered_jobs.json format that Phase 2 expects
            discovered = []
            for j in manual_jobs:
                discovered.append({
                    "company": j.get("company", ""),
                    "role": j.get("role", ""),
                    "platform": j.get("platform", "manual"),
                    "apply_url": j.get("apply_url", ""),
                    "posted": j.get("posted_date", j.get("location", "")),  # reuse location field if no posted_date
                    "description": j.get("description", ""),
                    "relevance": j.get("relevance", 0),
                })
            # Also write links_to_verify.json (Phase 2 reads this directly
            # when selected_jobs.json doesn't exist)
            links = [{"company": j["company"], "role": j["role"], "apply_url": j["apply_url"]} for j in discovered]
            links_file = os.path.join(output_dir, "links_to_verify.json")
            with open(links_file, "w") as lf:
                json.dump(links, lf, indent=2)
            # Write discovered_jobs.json for Phase 1c pick_jobs.py (if it runs)
            jobs_file = os.path.join(output_dir, "discovered_jobs.json")
            with open(jobs_file, "w") as jf:
                json.dump({"query": "manual_jobs.json", "timestamp": DATE_STR, "total": len(discovered), "jobs": discovered}, jf, indent=2)
            jobs = discovered
            log(f"  Loaded {len(jobs)} jobs from manual_jobs.json → discovered_jobs.json + links_to_verify.json")
        else:
            jobs = phase1_discover(args.query, args.max_jobs, output_dir)
            log(f"  Web discovery returned {len(jobs)} jobs")
    else:
        log("Skipping phase 1 (discover)")
        jobs = []

    # Phase 1b: GitHub discover (skip if we used manual list)
    if 1 in wanted and not os.path.exists(os.path.join(output_dir, "manual_jobs.json")):
        github_jobs = phase1b_github_discover(args.query, output_dir)
        jobs = jobs + github_jobs
        log(f"  After GitHub merge: {len(jobs)} total jobs")

    # Phase 1c: User picks which jobs to proceed with
    if 2 in wanted and jobs:
        pick_script = os.path.join(SCRIPT_DIR, "pick_jobs.py")
        if os.path.exists(pick_script):
            try:
                result = subprocess.run(
                    [sys.executable, pick_script, os.path.join(output_dir, "discovered_jobs.json")],
                    capture_output=True, text=True, timeout=30,
                    cwd=SCRIPT_DIR,
                    input="",  # runs non-interactively; picks nothing
                )
                if result.stdout:
                    log(f"  pick_jobs.py: {result.stdout.strip()}")
            except Exception as e:
                log(f"  pick_jobs.py skipped: {e}")
        else:
            log("  pick_jobs.py not found — skipping job selection gate")

    # Phase 2: Verify
    if 2 in wanted:
        live_jobs = phase2_verify(output_dir)
    else:
        log("Skipping phase 2 (verify)")
        live_jobs = jobs

    # Phase 3: Research
    if 3 in wanted:
        research = phase3_research(live_jobs, output_dir)
    else:
        log("Skipping phase 3 (research)")
        research = []

    # Phase 3b: GitHub company verify
    if 3 in wanted:
        checks = phase3b_github_verify(research, output_dir)
    else:
        log("Skipping phase 3b (github verify)")

    # Phase 4: Extract JDs
    if 4 in wanted:
        jd_results = phase4_extract(live_jobs, output_dir)
    else:
        log("Skipping phase 4 (extract)")
        jd_results = []

    # Phase 5: Match
    if 5 in wanted:
        jd_results = phase5_match(jd_results, output_dir, args.cv)
    else:
        log("Skipping phase 5 (match)")

    # Phase 6: Render
    if 6 in wanted:
        jd_results = phase6_render(jd_results, output_dir, args.cv)
    else:
        log("Skipping phase 6 (render)")

    # Phase 7: QA
    if 7 in wanted:
        jd_results = phase7_qa(jd_results, output_dir)
    else:
        log("Skipping phase 7 (qa)")

    # Phase 8: Track
    if 8 in wanted:
        phase8_track(jd_results, output_dir, args.github_repo)
    else:
        log("Skipping phase 8 (track)")

    # Summary
    log("=" * 60)
    log("PIPELINE COMPLETE")
    log(f"Output directory: {output_dir}")
    log(f"Jobs discovered: {len(jobs)}")
    log(f"Jobs verified live: {len(live_jobs)}")
    log(f"JDs extracted: {len([j for j in jd_results if j.get('jd')])}")
    log(f"CSVs: {os.path.join(output_dir, 'applications.csv')}")
    log("=" * 60)


if __name__ == "__main__":
    main()
