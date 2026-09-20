#!/usr/bin/env python3
"""Track job applications as GitHub Issues in a private repo.

Each application becomes a GitHub Issue with:
- Title: "[STATUS] Company — Role"
- Labels: applied / interviewing / offer / rejected / dropped / todo
- Body: structured application data (company, role, location, apply URL, dates, notes)
- Comments: interview feedback, follow-up reminders, status changes

Usage:
    python github_track.py --repo Tyba7/job-tracker --action list
    python github_track.py --repo Tyba7/job-tracker --action add --company "Fuse Energy" --role "Applied AI Engineer" --location "Dubai" --url "https://..."
    python github_track.py --repo Tyba7/job-tracker --action update --number 42 --status "interviewing"
    python github_track.py --repo Tyba7/job-tracker --action comment --number 42 --body "First round technical interview scheduled for Monday"
    python github_track.py --repo Tyba7/job-tracker --action close --number 42 --reason "rejected"
    python github_track.py --repo Tyba7/job-tracker --action export --output applications_export.csv
"""
import argparse
import json
import subprocess
import sys
import csv
import os
from datetime import datetime, timezone


def gh(*args: str) -> str:
    """Run a gh CLI command and return stdout."""
    cmd = ["gh"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def gh_api(path: str, method: str = "GET", data: dict = None, params: dict = None) -> dict:
    """Make a GitHub API call via gh api. Returns parsed JSON."""
    # Build query string from params
    if params:
        param_parts = []
        for key, value in params.items():
            param_parts.append(f"{key}={value}")
        if "?" in path:
            path = path + "&" + "&".join(param_parts)
        else:
            path = path + "?" + "&".join(param_parts)
    
    cmd = ["gh", "api", path]
    if method != "GET":
        cmd += ["--method", method]
    if data:
        # Use stdin for JSON body (handles arrays, nested objects correctly)
        body = json.dumps(data)
        cmd += ["--input", "-"]
        result = subprocess.run(cmd, input=body, capture_output=True, text=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh api {path} failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def repo_exists(owner: str, repo: str) -> bool:
    """Check if a GitHub repo exists."""
    try:
        gh_api(f"/repos/{owner}/{repo}")
        return True
    except RuntimeError:
        return False


def create_tracker_repo(owner: str, repo: str, private: bool = True) -> dict:
    """Create a private job tracker repo."""
    if repo_exists(owner, repo):
        print(f"Repo {owner}/{repo} already exists — using existing")
        return {"owner": owner, "repo": repo}
    
    print(f"Creating private repo {owner}/{repo}...")
    result = gh_api("/user/repos", method="POST", data={
        "name": repo,
        "private": private,
        "description": "Job application tracker — AI/ML roles in UAE",
        "auto_init": True
    })
    print(f"Created {result['full_name']}")
    return {"owner": owner, "repo": repo}


def get_labels(owner: str, repo: str) -> dict:
    """Get existing labels as a name→id map."""
    result = gh_api(f"/repos/{owner}/{repo}/labels")
    return {label["name"]: label["id"] for label in result}


def ensure_labels(owner: str, repo: str) -> dict:
    """Ensure standard job-tracking labels exist."""
    existing = get_labels(owner, repo)
    desired = {
        "applied": "Application submitted",
        "interviewing": "In interview process",
        "technical": "Technical interview round",
        "offer": "Offer received",
        "rejected": "Rejected",
        "dropped": "Dropped / withdrawn",
        "todo": "To apply",
        "dead": "Job closed / no longer accepting",
        "not-my-domain": "Not relevant to my profile",
    }
    
    for name, description in desired.items():
        if name not in existing:
            print(f"  Creating label: {name}")
            gh_api(f"/repos/{owner}/{repo}/labels", method="POST", data={
                "name": name,
                "description": description,
                "color": "000000"
            })
            existing[name] = True  # Mark as handled
    
    # Return label names that exist (we use gh issue edit for adding labels)
    return {k: True for k in desired}


def issue_title(status: str, company: str, role: str) -> str:
    """Generate a standardized issue title."""
    return f"[{status.upper()}] {company} — {role}"


def issue_body(company: str, role: str, location: str, apply_url: str,
               platform: str = "", notes: str = "", date_applied: str = None) -> str:
    """Generate a structured issue body."""
    date = date_applied or datetime.now().strftime("%Y-%m-%d")
    body = f"""## Application

**Company:** {company}
**Role:** {role}
**Location:** {location}
**Date Applied:** {date}
**Platform:** {platform or "Direct"}
**Apply URL:** {apply_url}

## Status

- Status: applied
- Interview rounds: none yet
- Offer: no

## Notes

{notes or "No notes yet."}

---
_Added via job-application pipeline_
"""
    return body


def add_application(owner: str, repo: str, company: str, role: str, location: str,
                    apply_url: str, platform: str = "", notes: str = "",
                    status: str = "applied", date_applied: str = None) -> int:
    """Add a new application as a GitHub Issue. Returns issue number."""
    labels = ensure_labels(owner, repo)
    title = issue_title(status, company, role)
    body = issue_body(company, role, location, apply_url, platform, notes, date_applied)
    
    print(f"Creating issue: {title}")
    result = gh_api(f"/repos/{owner}/{repo}/issues", method="POST", data={
        "title": title,
        "body": body,
        "labels": [status]
    })
    
    issue_num = result["number"]
    print(f"  Created #{issue_num} — {result['html_url']}")
    return issue_num


def list_applications(owner: str, repo: str, status: str = None) -> list[dict]:
    """List all application issues, optionally filtered by status label."""
    params = {"state": "all", "per_page": 100}
    if status:
        params["labels"] = status
    
    result = gh_api(f"/repos/{owner}/{repo}/issues", params=params)
    
    applications = []
    for issue in result:
        if "pull_request" in issue:
            continue  # Skip PRs
        
        # Extract structured data from issue body
        body = issue.get("body", "") or ""
        company = ""
        role = ""
        location = ""
        apply_url = ""
        date_applied = ""
        labels_list = [l["name"] for l in issue.get("labels", [])]
        
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("**Company:**"):
                company = line.split("**Company:**")[1].strip()
            elif line.startswith("**Role:**"):
                role = line.split("**Role:**")[1].strip()
            elif line.startswith("**Location:**"):
                location = line.split("**Location:**")[1].strip()
            elif line.startswith("**Apply URL:**"):
                apply_url = line.split("**Apply URL:**")[1].strip()
            elif line.startswith("**Date Applied:**"):
                date_applied = line.split("**Date Applied:**")[1].strip()
        
        applications.append({
            "number": issue["number"],
            "title": issue["title"],
            "status": labels_list[0] if labels_list else "unknown",
            "company": company,
            "role": role,
            "location": location,
            "apply_url": apply_url,
            "date_applied": date_applied,
            "state": issue["state"],
            "html_url": issue["html_url"],
            "all_labels": labels_list,
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
        })
    
    return applications


def update_status(owner: str, repo: str, issue_number: int, new_status: str,
                  notes: str = "") -> dict:
    """Update an application's status label and optionally add a comment."""
    # Remove old status labels, add new one
    current = list_applications(owner, repo)
    issue = next((i for i in current if i["number"] == issue_number), None)
    if not issue:
        raise RuntimeError(f"Issue #{issue_number} not found")
    
    old_labels = [l for l in issue["all_labels"] if l in 
                  ["applied", "interviewing", "technical", "offer", "rejected", "dropped", "dead", "not-my-domain", "todo"]]
    
    # Edit issue to set new labels
    new_labels = [new_status] + [l for l in old_labels if l != new_status]
    
    print(f"Updating #{issue_number}: {old_labels} → {new_labels}")
    gh_api(f"/repos/{owner}/{repo}/issues/{issue_number}/labels", method="PUT", data={
        "labels": new_labels
    })
    
    # Also update the title
    company = issue["company"]
    role = issue["role"]
    gh_api(f"/repos/{owner}/{repo}/issues/{issue_number}", method="PATCH", data={
        "title": issue_title(new_status, company, role)
    })
    
    # Add comment if notes provided
    if notes:
        gh_api(f"/repos/{owner}/{repo}/issues/{issue_number}/comments", method="POST", data={
            "body": f"_Status changed to **{new_status}** on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}_\n\n{notes}"
        })
    
    return {"number": issue_number, "status": new_status}


def add_comment(owner: str, repo: str, issue_number: int, body: str) -> dict:
    """Add a comment to an application issue."""
    print(f"Adding comment to #{issue_number}")
    result = gh_api(f"/repos/{owner}/{repo}/issues/{issue_number}/comments", method="POST", data={
        "body": body
    })
    print(f"  Comment ID: {result['id']}")
    return result


def close_application(owner: str, repo: str, issue_number: int, reason: str = "rejected") -> dict:
    """Close an application issue."""
    # Map our reason to GitHub's allowed state_reason values
    gh_reason = {
        "rejected": "not_planned",
        "applied": "completed",
        "interviewing": "completed",
        "offer": "completed",
        "dropped": "not_planned",
        "dead": "not_planned",
        "not-my-domain": "not_planned",
        "test-complete": "completed",
    }.get(reason, "not_planned")
    
    print(f"Closing #{issue_number} — {reason}")
    result = gh_api(f"/repos/{owner}/{repo}/issues/{issue_number}", method="PATCH", data={
        "state": "closed",
        "state_reason": gh_reason
    })
    print(f"  Closed: {result['html_url']}")
    return result


def export_csv(owner: str, repo: str, output: str):
    """Export all applications to a CSV file (compatible with applications.csv format)."""
    applications = list_applications(owner, repo)
    
    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["priority", "company", "role", "location", "status", 
                        "apply_link", "apply_route", "folder", "cv_file", 
                        "cover_letter", "notes"])
        
        for i, app in enumerate(applications, 1):
            writer.writerow([
                i,
                app["company"],
                app["role"],
                app["location"],
                app["status"],
                app["apply_url"],
                "GitHub",
                "",
                "",
                "",
                f"GitHub issue #{app['number']}: {app['html_url']}"
            ])
    
    print(f"Exported {len(applications)} applications to {output}")


def main():
    parser = argparse.ArgumentParser(description="Track job applications as GitHub Issues")
    parser.add_argument("--repo", required=True, help="GitHub repo in OWNER/REPO format (e.g. Tyba7/job-tracker)")
    parser.add_argument("--action", required=True, 
                       choices=["list", "add", "update", "comment", "close", "export", "create-repo"])
    parser.add_argument("--company", help="Company name (for add)")
    parser.add_argument("--role", help="Job role (for add)")
    parser.add_argument("--location", help="Job location (for add)")
    parser.add_argument("--url", help="Apply URL (for add)")
    parser.add_argument("--platform", help="Platform source (for add)")
    parser.add_argument("--notes", help="Application notes (for add)")
    parser.add_argument("--status", help="Status label: applied/interviewing/technical/offer/rejected/dropped/dead/not-my-domain/todo")
    parser.add_argument("--number", type=int, help="Issue number (for update/comment/close)")
    parser.add_argument("--body", help="Comment body (for comment)")
    parser.add_argument("--reason", help="Close reason (for close)")
    parser.add_argument("--output", "-o", help="Output file (for export)")
    parser.add_argument("--filter", help="Filter by status label (for list)")
    args = parser.parse_args()
    
    owner, repo_name = args.repo.split("/", 1)
    
    # Handle create-repo separately
    if args.action == "create-repo":
        create_tracker_repo(owner, repo_name)
        ensure_labels(owner, repo_name)
        print(f"\nTracker repo ready: https://github.com/{owner}/{repo_name}")
        print("Use --action add to start tracking applications.")
        return 0
    
    # For all other actions, ensure repo exists
    if not repo_exists(owner, repo_name):
        print(f"Repo {owner}/{repo_name} does not exist.")
        print("Create it first: github_track.py --repo {args.repo} --action create-repo")
        return 1
    
    ensure_labels(owner, repo_name)  # Ensure labels exist (idempotent)
    
    if args.action == "list":
        apps = list_applications(owner, repo_name, args.filter)
        if not apps:
            print("No applications found.")
            return 0
        print(f"\n{len(apps)} applications:\n")
        for app in apps:
            status_icon = "🔴" if app["state"] == "closed" else "🟢"
            print(f"  {status_icon} #{app['number']:3} [{app['status']:12}] {app['company']} — {app['role'][:40]}")
            print(f"       {app['location']} | {app['date_applied']} | {app['html_url']}")
        return 0
    
    elif args.action == "add":
        if not all([args.company, args.role, args.location, args.url]):
            print("ERROR: --company, --role, --location, and --url are required for add", file=sys.stderr)
            return 1
        num = add_application(owner, repo_name, args.company, args.role, args.location,
                             args.url, args.platform or "", args.notes or "",
                             args.status or "applied")
        print(f"\nApplication tracked as issue #{num}")
        return 0
    
    elif args.action == "update":
        if not args.number or not args.status:
            print("ERROR: --number and --status are required for update", file=sys.stderr)
            return 1
        result = update_status(owner, repo_name, args.number, args.status, args.notes or "")
        print(f"\nUpdated: #{result['number']} → {result['status']}")
        return 0
    
    elif args.action == "comment":
        if not args.number or not args.body:
            print("ERROR: --number and --body are required for comment", file=sys.stderr)
            return 1
        add_comment(owner, repo_name, args.number, args.body)
        return 0
    
    elif args.action == "close":
        if not args.number:
            print("ERROR: --number is required for close", file=sys.stderr)
            return 1
        close_application(owner, repo_name, args.number, args.reason or "rejected")
        return 0
    
    elif args.action == "export":
        if not args.output:
            print("ERROR: --output is required for export", file=sys.stderr)
            return 1
        export_csv(owner, repo_name, args.output)
        return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
