#!/usr/bin/env python3
"""Discover UAE AI/ML jobs from GitHub sources.

GitHub sources:
1. github.com/jobs — official GitHub job board (search API, no auth needed for search)
2. GitHub repo search — READMEs containing "hiring", "jobs", "careers" in UAE-related repos
3. GitHub issues search — issues labeled "job" or "hiring" in tech repos
4. GitHub discussions search — hiring discussions in tech community repos

Usage:
    python github_discover.py --query "AI engineer UAE" --output github_jobs.json
    python github_discover.py --query "machine learning engineer Dubai" --output github_jobs.json
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime


def github_jobs_search(query: str) -> list[dict]:
    """Search GitHub's official job board via web_search (no API key needed)."""
    results = []
    # GitHub jobs is at github.com/jobs — search via web_search
    try:
        from hermes_tools import web_search
        search_results = web_search(
            f"site:github.com/jobs {query}",
            limit=10
        )
        for item in search_results.get("data", {}).get("web", []):
            results.append({
                "source": "github_jobs",
                "company": item.get("title", "").split(" at ")[0] if " at " in item.get("title", "") else "",
                "role": item.get("title", ""),
                "location": "",
                "apply_url": item.get("url", ""),
                "posted": "",
                "description": item.get("description", ""),
                "platform": "GitHub Jobs"
            })
    except ImportError:
        print("WARNING: hermes_tools not available — skipping GitHub Jobs search", file=sys.stderr)
    return results


def github_repo_hiring_search(query: str, location: str = "UAE") -> list[dict]:
    """Search for repos whose READMEs mention hiring + location."""
    results = []
    try:
        from hermes_tools import web_search
        # Search for repos with hiring/signup in README
        searches = [
            f"site:github.com {location} hiring AI engineer README",
            f"site:github.com {location} 'we are hiring' machine learning",
            f"site:github.com {location} careers AI ML engineer open source",
        ]
        for search in searches:
            search_results = web_search(search, limit=5)
            for item in search_results.get("data", {}).get("web", []):
                url = item.get("url", "")
                if "github.com" in url and "/blob/" not in url and "/issues/" not in url:
                    results.append({
                        "source": "github_repo",
                        "company": "",
                        "role": f"Hiring — {query}",
                        "location": location,
                        "apply_url": url,
                        "posted": "",
                        "description": item.get("description", ""),
                        "platform": "GitHub Repo"
                    })
    except ImportError:
        print("WARNING: hermes_tools not available — skipping GitHub repo search", file=sys.stderr)
    return results


def github_issues_hiring_search(query: str, location: str = "UAE") -> list[dict]:
    """Search GitHub issues for hiring/open-position posts."""
    results = []
    try:
        from hermes_tools import web_search
        searches = [
            f"site:github.com/issues {location} 'hiring' OR 'open position' OR 'job opening' AI OR ML OR 'machine learning'",
        ]
        for search in searches:
            search_results = web_search(search, limit=5)
            for item in search_results.get("data", {}).get("web", []):
                results.append({
                    "source": "github_issues",
                    "company": "",
                    "role": f"Open position — {query}",
                    "location": location,
                    "apply_url": item.get("url", ""),
                    "posted": "",
                    "description": item.get("description", ""),
                    "platform": "GitHub Issues"
                })
    except ImportError:
        print("WARNING: hermes_tools not available — skipping GitHub issues search", file=sys.stderr)
    return results


def run_github_discover(query: str, location: str = "UAE", output: str = None) -> list[dict]:
    """Run all GitHub discovery sources and combine results."""
    all_results = []
    
    print(f"Searching GitHub Jobs for: {query}")
    jobs = github_jobs_search(query)
    all_results.extend(jobs)
    print(f"  → {len(jobs)} results from GitHub Jobs")
    
    print(f"Searching GitHub repos for hiring + {location}")
    repos = github_repo_hiring_search(query, location)
    all_results.extend(repos)
    print(f"  → {len(repos)} results from GitHub repos")
    
    print(f"Searching GitHub issues for open positions")
    issues = github_issues_hiring_search(query, location)
    all_results.extend(issues)
    print(f"  → {len(issues)} results from GitHub issues")
    
    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for r in all_results:
        url = r.get("apply_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)
    
    print(f"\nTotal unique GitHub results: {len(unique)}")
    
    if output:
        output_data = {
            "query": query,
            "location": location,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total": len(unique),
            "results": unique
        }
        with open(output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results written to {output}")
    
    return unique


def main():
    parser = argparse.ArgumentParser(description="Discover jobs from GitHub sources")
    parser.add_argument("--query", required=True, help="Job search query (e.g. 'AI engineer UAE')")
    parser.add_argument("--location", default="UAE", help="Location filter (default: UAE)")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    args = parser.parse_args()
    
    results = run_github_discover(args.query, args.location, args.output)
    
    if not results:
        print("\nNo GitHub job results found. This is normal — GitHub is a supplementary source.")
        print("Continue with LinkedIn/Indeed/Bayt discovery for the main pipeline.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
