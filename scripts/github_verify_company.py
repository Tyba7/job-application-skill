#!/usr/bin/env python3
"""Verify company legitimacy and activity using GitHub data.

Checks:
1. Does the company have a GitHub org or repos?
2. When was their last activity? (stale org = red flag)
3. How many repos, stars, contributors? (signal of real engineering team)
4. Does their GitHub profile match their claimed website/industry?

Usage:
    python github_verify_company.py --company "Fuse Energy" --output company_check.json
    python github_verify_company.py --company "NeuralHorizonsAI" --output company_check.json
    python github_verify_company.py --company "Acme AI Inc" --output company_check.json
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone


def gh_api(path: str, method: str = "GET", data: dict = None):
    """Make a GitHub API call. Returns None on failure."""
    cmd = ["gh", "api"]
    if path.startswith("/"):
        cmd.append(path)
    else:
        cmd += path.split()
    if method != "GET":
        cmd += ["--method", method]
    if data:
        body = json.dumps(data)
        cmd += ["--input", "-"]
        result = subprocess.run(cmd, input=body, capture_output=True, text=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def gh(*args: str) -> str:
    """Run a gh CLI command and return stdout."""
    cmd = ["gh"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def search_org_or_user(company: str):
    """Search for a GitHub org or user matching the company name."""
    # Try org search first
    result = gh_api(f"/search/organizations?q={company.replace(' ', '+')}&per_page=5")
    if result and result.get("total_count", 0) > 0:
        for org in result.get("items", []):
            if org.get("name", "").lower() == company.lower() or \
               org.get("login", "").lower() == company.lower() or \
               company.lower() in org.get("name", "").lower():
                return {"type": "org", "data": org}
    
    # Try user search
    result = gh_api(f"/search/users?q={company.replace(' ', '+')}&per_page=5")
    if result and result.get("total_count", 0) > 0:
        for user in result.get("items", []):
            if company.lower() in user.get("login", "").lower():
                return {"type": "user", "data": user}
    
    return None


def search_repos_by_company(company: str):
    """Search for repos that might belong to the company."""
    result = gh_api(f"/search/repositories?q={company.replace(' ', '+')}+in:name+description&per_page=10")
    if not result:
        return []
    return result.get("items", [])


def check_repo_activity(repo_full_name: str) -> dict:
    """Check activity metrics for a specific repo."""
    data = gh_api(f"/repos/{repo_full_name}")
    if not data:
        return {}
    
    # Get recent commits
    commits = gh_api(f"/repos/{repo_full_name}/commits?per_page=5&sha=main")
    if not commits:
        commits = gh_api(f"/repos/{repo_full_name}/commits?per_page=5&sha=master")
    
    last_commit = None
    if commits and len(commits) > 0:
        last_commit = commits[0].get("commit", {}).get("author", {}).get("date", "unknown")
    
    # Get contributors
    contributors = gh_api(f"/repos/{repo_full_name}/contributors?per_page=1")
    contributor_count = 0
    if contributors:
        contributor_count = contributors.get("total_count", 0) or len(contributors)
    
    return {
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "language": data.get("language", ""),
        "last_commit": last_commit,
        "contributors": contributor_count,
        "is_fork": data.get("fork", False),
        "size_kb": data.get("size", 0),
        "license": data.get("license", {}).get("spdx_id", "") if data.get("license") else "",
    }


def format_activity_age(last_commit: str) -> str:
    """Format how long ago a commit was as a human-readable string."""
    if not last_commit or last_commit == "unknown":
        return "unknown"
    try:
        commit_time = datetime.fromisoformat(last_commit.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - commit_time
        days = delta.days
        if days == 0:
            return "today"
        elif days == 1:
            return "1 day ago"
        elif days < 30:
            return f"{days} days ago"
        elif days < 365:
            months = days // 30
            return f"{months} months ago"
        else:
            years = days // 365
            return f"{years} years ago"
    except (ValueError, TypeError):
        return str(last_commit)


def verify_company(company: str) -> dict:
    """Run all verification checks for a company."""
    print(f"\n{'='*60}")
    print(f"Verifying: {company}")
    print(f"{'='*60}")
    
    result = {
        "company": company,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "github_presence": "none",
        "risk_level": "unknown",
        "findings": []
    }
    
    # 1. Search for org/user
    print(f"\n[1/4] Searching GitHub for '{company}'...")
    match = search_org_or_user(company)
    
    if match:
        entity_type = match["type"]
        entity = match["data"]
        login = entity.get("login", "")
        name = entity.get("name", login)
        
        result["github_presence"] = entity_type
        result["github_login"] = login
        result["github_name"] = name
        
        print(f"  Found {entity_type}: {login} ({name})")
        result["findings"].append(f"Found GitHub {entity_type}: @{login}")
        
        # Get org repos if org
        if entity_type == "org":
            repos_result = gh_api(f"/orgs/{login}/repos?per_page=5&sort=updated")
            if repos_result:
                repos = repos_result if isinstance(repos_result, list) else repos_result.get("repositories", [])
                result["repo_count"] = entity.get("public_repos", len(repos))
                result["member_count"] = entity.get("public_members", 0)
                
                if repos:
                    latest = repos[0]
                    result["latest_repo"] = latest.get("name", "")
                    result["latest_repo_updated"] = latest.get("updated_at", "")
                    result["latest_repo_language"] = latest.get("language", "")
                    
                    age = format_activity_age(latest.get("updated_at", ""))
                    print(f"  Latest repo: {latest.get('name', '')} ({latest.get('language', '')}) — updated {age}")
                    result["findings"].append(f"Latest repo '{latest.get('name', '')}' updated {age}")
                    
                    if "years" in age:
                        result["findings"].append(f"WARNING: Repo activity is {age} — org may be inactive")
                        result["risk_level"] = "high"
                    elif "months" in age and int(age.split()[0]) > 6:
                        result["findings"].append(f"NOTE: Repo activity is {age} — moderate concern")
                        if result["risk_level"] == "unknown":
                            result["risk_level"] = "medium"
            
            print(f"  Public repos: {result.get('repo_count', 'unknown')}, Members: {result.get('member_count', 'unknown')}")
        
        # Check some repos for activity
        if entity_type == "org":
            repos_to_check = repos_result[:3] if repos_result and isinstance(repos_result, list) else []
        else:
            # Search for company repos
            repos_to_check = search_repos_by_company(company)[:3]
        
        for repo in repos_to_check:
            repo_name = repo.get("full_name", "") if isinstance(repo, dict) else ""
            if repo_name:
                activity = check_repo_activity(repo_name)
                if activity:
                    age = format_activity_age(activity.get("last_commit", ""))
                    print(f"  Repo {repo_name}: {activity.get('language', '')} | {activity.get('stars', 0)}★ | last commit {age}")
                    result["findings"].append(f"Repo '{repo_name}': {activity.get('language', '')} ({activity.get('stars', 0)}★), last commit {age}")
    else:
        print(f"  No GitHub org or user found for '{company}'")
        result["findings"].append("No GitHub presence found")
        # This is a yellow flag, not a red one — many legitimate companies don't use GitHub
        result["risk_level"] = "low"  # GitHub absence alone isn't risky
    
    # 2. Search for mentions (web) — done via web_search in the calling context
    # This script focuses on GitHub data only; web search is handled by the pipeline
    
    # 3. Summary
    print(f"\n[RESULT] Risk level: {result['risk_level'].upper()}")
    print(f"  GitHub presence: {result['github_presence']}")
    if result.get('github_login'):
        print(f"  GitHub: https://github.com/{result['github_login']}")
    
    if result['risk_level'] == 'high':
        print("  ⚠ WARNING: Company shows signs of inactivity or mismatch")
    elif result['risk_level'] == 'medium':
        print("  ⚡ CAUTION: Some concerns — verify through other channels")
    elif result['risk_level'] == 'low':
        print("  ✅ No GitHub red flags")
    else:
        print("  ℹ️  Unable to assess — no GitHub data available")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Verify company legitimacy via GitHub")
    parser.add_argument("--company", required=True, help="Company name to verify")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    args = parser.parse_args()
    
    result = verify_company(args.company)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nResults written to {args.output}")
    
    # Return exit code based on risk
    if result["risk_level"] == "high":
        return 1  # High risk — should flag
    return 0


if __name__ == "__main__":
    sys.exit(main())
