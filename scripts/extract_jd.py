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
        "signup_flow": "",  # sign-up instructions for annotation/training platforms
        "assessment_required": False,
        "assessment_hours_estimate": 0,
        "pay_range": "",
        "notes": "",
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
    # Strip www. prefix for consistent domain matching
    domain = domain.removeprefix("www.")

    # Check for annotation platform domains — these are sign-up flows, not JD scrape targets.
    # Return the concrete sign-up flow as full_jd instead of attempting a scrape (which
    # would fail and waste the search fallback round-trips).
    _jd_domain = domain.lower()
    if _jd_domain in _ANNOTATION_DOMAINS:
        return _annotation_signup_jd(url, company, role, platform, _jd_domain)

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


# ── AI training / data annotation platform sign-up flows ─────────────────────
#
# When extract_jd_from_url receives a URL whose domain is in
# _ANNOTATION_DOMAINS, it returns the matching signup_flow metadata directly
# instead of attempting a scrape (sign-up landing pages have no extractable
# JD).  The pipeline still produces a CV in the job folder; the applicant
# manually follows the signup_flow steps.
#
# To add or update a platform's flow, edit ANNOTATION_PLATFORM_FLOWS below.
# Each entry:
#   signup_url         — exact URL to open to start
#   steps              — ordered list of actions the applicant takes
#   assessment_required — True if a test/assessment is required before access
#   assessment_hours   — estimated hours to set aside for the assessment
#   assessment_once_only — True if the assessment can only be taken once (no retakes)
#   pay_range          — expected compensation (from research; verify on the site)
#   prerequisites      — list of things to have ready before starting
#   notes              — platform-specific cautions or tips
#   status_after_signup — recommended applications.csv status after sign-up
#
# Source: web research on 2026-09-24.  Pay ranges and processes may change;
# verify on the platform's own site before relying on them.

ANNOTATION_PLATFORM_FLOWS = {
    "dataannotation.tech": {
        "signup_url": "https://app.dataannotation.tech/worker_signup",
        "steps": [
            "1. Go to https://app.dataannotation.tech/worker_signup",
            "2. Create account: enter name, email, skills, professional background",
            "3. Take the Starter Assessment (~1 hour) — read instructions carefully, review before submitting",
            "4. Optional: take domain-specific qualification assessments (Coding, Math, Chemistry, Biology, Physics, Finance, Law, Medicine, Languages — 1-2 hours each)",
            "5. Wait for review (typically a few days)",
            "6. If approved: log in, select projects matching your skills, start working",
        ],
        "assessment_required": True,
        "assessment_hours": 1.0,
        "assessment_once_only": True,
        "pay_range": "Generalist: $25-30+/hr; Coding: $50-100+/hr; domain specialist: higher",
        "prerequisites": [
            "Valid government ID (for identity verification)",
            "Bachelor's degree or equivalent real-world experience (minimum for generalist work)",
            "Advanced degree/credentials for higher-paying tiers ($50+/hr)",
            "Strong writing and critical thinking (generalist track)",
            "Programming experience in Python, JavaScript, HTML, C++, C#, or SQL (coding track)",
        ],
        "notes": "*** STARTER ASSESSMENT IS ONE-TIME — NO RETAKES. *** If you fail, you cannot reapply with the same account. Do not rush — review for thoroughness, not speed. Most assessments take ~1 hour. Domain qualifications may take 1-2 hours each. Approval is not guaranteed; rejection means you won't get platform access.",
        "status_after_signup": "ASSESSMENT_PENDING",
    },
    "outlier.ai": {
        "signup_url": "https://app.outlier.ai/login",
        "steps": [
            "1. Go to https://app.outlier.ai/login and sign up (email or social login)",
            "2. Find an opportunity matching your skills (software engineering, coding, writing, languages, math, science, AI training, data, other)",
            "3. Add accurate professional information — focus on relevant skills, no exaggeration",
            "4. Upload your current, easy-to-read resume focused on relevant skills",
            "5. Verify your identity: valid ID, phone number, LinkedIn profile",
            "6. Complete the skill assessment for the opportunity (varies by project: coding project tests programming; language project tests reading/writing in that language)",
            "7. Complete project-specific onboarding (~30-90 min general onboarding)",
            "8. Start working: write prompts, evaluate AI responses, correct AI content, complete coding tasks, provide expert feedback",
        ],
        "assessment_required": True,
        "assessment_hours": 1.0,
        "assessment_once_only": False,
        "pay_range": "Varies by project — not publicly listed as a single rate",
        "prerequisites": [
            "Valid ID (for identity verification)",
            "Phone number (for verification)",
            "Current resume (PDF, focused on relevant skills)",
            "LinkedIn profile URL",
            "Expertise in at least one of: software development, coding, writing, languages, mathematics, science",
        ],
        "notes": "Onboarding generally takes 30-90 minutes. Skill assessment is project-specific — you don't take one generic test. Start with the opportunity closest to your actual expertise. Freelance/project-based, not guaranteed full-time work.",
        "status_after_signup": "ASSESSMENT_PENDING",
    },
    "alignerr.com": {
        "signup_url": "https://app.alignerr.com/",
        "steps": [
            "1. Go to https://app.alignerr.com/ and sign up",
            "2. Complete application: upload resume, set skill/domain preferences",
            "3. Wait for approval (email invitation sent when approved)",
            "4. Complete contract + billing setup (~1 hour, via Stripe)",
            "5. Join the Alignerr community and take on projects",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "~$25/hr reported (varies by project/domain)",
        "prerequisites": [
            "Resume (current, relevant to AI/ML/data work)",
            "Skill/domain preferences (identify your areas of expertise)",
            "Stripe account or payment details for billing setup",
        ],
        "notes": "Approval step before access — not automatic. Contract + billing setup takes ~1 hour. Powered by Labelbox. Some users report delayed payments — verify current reputation before committing significant time.",
        "status_after_signup": "PENDING_APPROVAL",
    },
    "mercor.com": {
        "signup_url": "https://work.mercor.com/explore",
        "steps": [
            "1. Go to https://work.mercor.com/login to sign up (enter email → Sign Up)",
            "2. Check email for verification link and click it to complete registration",
            "3. Complete minimal profile fields to enable role applications",
            "4. Go to https://work.mercor.com/explore to browse available expert roles",
            "5. Apply to roles matching your expertise (ML Engineer, Physician, Finance, Legal, Cybersecurity, Finance Analyst, etc.)",
            "6. Wait for offer/invitation from Mercor",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "ML Engineer: $70-250/hr; Physician: $110-250/hr; Finance: $60-180/hr; Legal: $60-150/hr; Cybersecurity: $200-250/hr; Legacy Codebase Migration: $200/hr; Financial Analyst: $60-180/hr",
        "prerequisites": [
            "Valid mobile phone number (required for security)",
            "Email address you can access immediately (verification email sent on sign-up and each login)",
            "Deep expertise in a specific domain (ML, medicine, finance, law, cybersecurity, etc.) — this is an expert-level platform",
        ],
        "notes": "Expert-level platform — roles are for people with deep domain expertise, not generalist AI/ML work. You receive a one-time verification email each time you sign in. Country restrictions may apply (some countries excluded from the talent network).",
        "status_after_signup": "PROFILE_COMPLETE",
    },
    "telusinternational.ai": {
        "signup_url": "https://www.telusinternational.ai/",
        "steps": [
            "1. Go to https://www.telusinternational.ai/ and find the AI community / contributor sign-up",
            "2. Apply to join the AI training community (application + qualification model, similar to former Lionbridge AI)",
            "3. Complete qualification tests for the project types you're interested in",
            "4. If accepted, receive project invitations and start working on search evaluation, AI evaluation, translation, or other tasks",
        ],
        "assessment_required": True,
        "assessment_hours": 1.0,
        "assessment_once_only": False,
        "pay_range": "Some listings at $25-45/hr; varies by project",
        "prerequisites": [
            "Valid ID (likely required for identity verification)",
            "Expertise in relevant domain (search evaluation, languages, AI content evaluation)",
        ],
        "notes": "Formerly Lionbridge AI (TELUS acquired Lionbridge's AI division in 2020). Flow is similar to the legacy Lionbridge model: apply → qualify → get projects. Exact sign-up path may require navigating the TELUS International AI site to find the contributor/contractor application. Check the site for current process.",
        "status_after_signup": "ASSESSMENT_PENDING",
    },
    "appen.com": {
        "signup_url": "https://www.appen.com/",
        "steps": [
            "1. Go to https://www.appen.com/ and find the 'Join' / 'Become a Contributor' / 'AI Community' sign-up",
            "2. Create account and complete profile",
            "3. Take qualification tests for the project types you're interested in (search evaluation, AI training, language pairs, etc.)",
            "4. If you pass qualifications, you're added to the pool for relevant projects",
            "5. Receive project invitations and complete tasks for pay",
        ],
        "assessment_required": True,
        "assessment_hours": 1.0,
        "assessment_once_only": False,
        "pay_range": "Top rate of $100+/hr on some projects; varies widely by task type and qualification",
        "prerequisites": [
            "Valid ID (for identity verification)",
            "Expertise in relevant domain (languages, search evaluation, AI content, etc.)",
            "Reliable internet connection and computer",
        ],
        "notes": "One of the oldest AI data companies with global reach. Project availability varies by country, language, and qualification. Some projects are ongoing; others are short-term. Qualification tests are typically project-specific.",
        "status_after_signup": "ASSESSMENT_PENDING",
    },
    "remotasks.com": {
        "signup_url": "https://www.remotasks.com/signup",
        "steps": [
            "1. Go to https://www.remotasks.com/signup and create a free account",
            "2. Complete profile and any required onboarding",
            "3. Browse available tasks and start working",
            "4. Get paid weekly via PayPal or AirTM",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "Per-task; varies by task type. Paid weekly.",
        "prerequisites": [
            "Computer (Windows/Mac) with internet connection",
            "PayPal or AirTM account for payment (or ability to set one up)",
        ],
        "notes": "Tasks include image/video/LiDAR annotation, AI training, RLHF. Beginner-friendly — no assessment barrier to start. Gamified onboarding. Pay per task; total earnings depend on task availability and your speed.",
        "status_after_signup": "SIGNED_UP",
    },
    "oneforma.com": {
        "signup_url": "https://my.oneforma.com/center/signup",
        "steps": [
            "1. Go to https://my.oneforma.com/center/signup and create an account",
            "2. Complete your contributor profile",
            "3. Wait for or browse project invitations",
            "4. Accept tasks and get paid per task",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "Per-task; varies by project. Part of Centific.",
        "prerequisites": [
            "Computer with internet connection",
            "Payment method for payouts",
        ],
        "notes": "Part of Centific (formerly Pactera EDGE). No upfront fee. After sign-up, check the contributor center for available projects. Some projects may require qualification tests.",
        "status_after_signup": "SIGNED_UP",
    },
    "mindrift.ai": {
        "signup_url": "https://mindrift.ai/apply",
        "steps": [
            "1. For basic tasks: go to https://mindrift.ai/apply or https://mindrift.toloka.ai/ and register",
            "2. For specialized roles: browse actual job postings at https://apply.workable.com/toloka-ai/ (or follow links from mindrift.ai)",
            "3. Apply to individual specialized roles (Brand Designer, Software Engineer, AI Trainer, Data Scraping Engineer, Web Designer, etc.) via Workable",
            "4. Pass qualifications to access specialized projects",
            "5. Start with straightforward tasks open to everyone, then progress to specialized work",
        ],
        "assessment_required": True,
        "assessment_hours": 1.0,
        "assessment_once_only": False,
        "pay_range": "Basic tasks: $5-15/hr; Specialized roles: up to $50/hr (Brand Designer, Software Engineer, AI Trainer, Data Scraping Engineer, etc.)",
        "prerequisites": [
            "For basic tasks: computer + internet, no special skills required",
            "For specialized roles: relevant expertise (software engineering, design, AI training, data engineering, etc.)",
        ],
        "notes": "Mindrift is the most job-board-like of the annotation platforms — it has real job postings with specific roles, rates, and Workable apply links. Treat specialized roles like normal job applications. Basic tasks are open to everyone with no assessment. Formerly Toloka; Toloka account may carry over.",
        "status_after_signup": "SIGNED_UP",
    },
    "surgehq.ai": {
        "signup_url": "mailto:talent@surgehq.ai",
        "steps": [
            "1. Compose an email to talent@surgehq.ai",
            "2. In the subject line or body, include the name of the role you're applying for",
            "3. Describe your background and interest in collaborating with Surge",
            "4. Send the email",
            "5. Wait for review and response from Surge talent team",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "Not publicly listed — varies by role and negotiation",
        "prerequisites": [
            "Professional email account",
            "Clear description of your background and the specific role you're interested in",
            "Resume or background summary to attach/reference",
        ],
        "notes": "Surge AI uses email application rather than a web sign-up form. You must email talent@surgehq.ai with your background and the role you're applying for. This is not a 'sign up and start' platform — it's an application process. Pay and terms are not publicly listed; likely negotiated per role.",
        "status_after_signup": "APPLIED",
    },
    "superannotate.com": {
        "signup_url": "https://www.superannotate.com/",
        "steps": [
            "1. Go to https://www.superannotate.com/ and sign up for an account",
            "2. After sign-up, click your Profile in the top navigation",
            "3. Click 'Jobs' to open the full job list",
            "4. Browse open freelance AI training / SME gigs",
            "5. Apply to individual gigs that match your expertise",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "Varies per gig — not publicly listed as a single rate",
        "prerequisites": [
            "Computer with internet connection",
            "Domain expertise relevant to the gigs you want to apply for (SME roles require subject-matter expertise)",
        ],
        "notes": "After sign-up, the key step many users miss: go to Profile → Jobs to see open work. Signing up alone doesn't show you jobs — you have to navigate to the Jobs section from your profile. Freelance AI training and SME (Subject Matter Expert) roles available. Also has a careers page at superannotate.com/careers for full-time roles.",
        "status_after_signup": "JOB_BROWSING",
    },
    "rws.com": {
        "signup_url": "https://jobs.lever.co/rws",
        "steps": [
            "1. Go to https://jobs.lever.co/rws or https://www.rws.com/artificial-intelligence/train-ai-data-services/trainai-community/",
            "2. Click 'Join our TrainAI community'",
            "3. Complete the sign-up process (basic details, no fee required)",
            "4. Complete training and testing for the project types you're suited for",
            "5. Accept tasks and get paid per task (PayPal or direct bank transfer)",
        ],
        "assessment_required": True,
        "assessment_hours": 1.0,
        "assessment_once_only": False,
        "pay_range": "Per-task; paid per task completed. No salary guarantee — earnings depend on number of tasks completed and qualified for.",
        "prerequisites": [
            "Personal computer running Windows or Mac OS X",
            "High-speed internet access (cable modem, DSL, etc.)",
            "Email service (Outlook, Gmail, or any other)",
            "Latest version of Google Chrome",
            "At least 18 years old",
        ],
        "notes": "No fee to join — RWS will never ask for payments. No training or experience required to join the community; you get invited to projects suited to you after joining. Payments via PayPal or direct bank account (select during registration). Once joined, you routinely receive project invitations via email. Also has Moravia brand (moravia.com) under RWS.",
        "status_after_signup": "TRAINING_PENDING",
    },
    "opentrain.ai": {
        "signup_url": "https://www.opentrain.ai/jobs/",
        "steps": [
            "1. Go to https://www.opentrain.ai/jobs/ and browse open remote AI jobs",
            "2. Find a role matching your skills (e.g. Clio Workflow AI Training Specialist, GitHub Workflow Evaluation Specialist, AI Model Evaluation Trainer, Google Analytics Workflow Specialist, Toast POS AI Training Specialist, etc.)",
            "3. Click 'Apply now' on the specific role",
            "4. Complete the application (the role's apply link goes to a Workable-style application)",
            "5. Wait for review and onboarding if selected",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "$14-175/hr depending on role (e.g. AI Model Evaluation Trainer: $14-36/hr; GitHub Workflow Evaluation Specialist: $90-175/hr; Clio Workflow: $30-100/hr; Google Analytics: $30-100/hr; Toast POS: $28-92/hr; HubSpot CRM: $28-92/hr)",
        "prerequisites": [
            "Relevant expertise for the specific role you're applying to",
            "20+ hours weekly availability for most roles (many require 20+ hrs/week)",
            "Resume or background relevant to the role",
        ],
        "notes": "OpenTrain AI is the closest to a normal job board among the annotation platforms. Roles are real contractor positions with specific pay ranges, hours requirements, and apply links. Most require 20+ hrs/week. Many list UAE as an eligible country. Treat like a normal remote job board — apply per role.",
        "status_after_signup": "APPLIED",
    },
    "lxt.ai": {
        "signup_url": "https://clickworker.app/UG3Am",
        "steps": [
            "1. Go to https://www.lxt.ai/jobs/ and click 'Become a Contributor'",
            "2. This redirects to https://clickworker.app/UG3Am — complete the Clickworker sign-up",
            "3. Complete profile and any required setup",
            "4. Start contributing to LXT crowd tasks via Clickworker",
            "5. Get paid per task",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "Per-task; paid per task completed. LXT crowd contributors are paid through Clickworker.",
        "prerequisites": [
            "Computer with internet connection",
            "Clickworker account (LXT crowd contributors sign up through Clickworker)",
            "Payment method for Clickworker payouts",
        ],
        "notes": "LXT crowd contributor sign-up goes through Clickworker (clickworker.app/UG3Am). LXT is a Canadian AI data company. The LXT jobs page links to Clickworker for actual sign-up. If you want LXT specifically, you sign up via Clickworker and then work on LXT-sourced tasks.",
        "status_after_signup": "SIGNED_UP",
    },
    "invisible.com": {
        "signup_url": "https://invisibletech.ai/join-us",
        "steps": [
            "1. Go to https://invisibletech.ai/join-us to browse open roles",
            "2. Review roles (these are full-time/contract roles, not gig work)",
            "3. Apply to individual roles that match your background",
            "4. Go through Invisible's hiring process for the role",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "Competitive benefits, equity, flexible PTO (full-time roles) — not publicly listed as hourly rates",
        "prerequisites": [
            "Resume/CV relevant to the role",
            "Background in AI, operations, or the specific domain of the role",
        ],
        "notes": "Invisible Technologies is NOT a gig/annotation platform — it's an applied AI research company hiring full-time and contract employees. Roles are real jobs with benefits, not per-task pay. Apply per role like a normal job. Different model from DataAnnotation/Outlier/Mercor.",
        "status_after_signup": "APPLIED",
    },
    "remoter.me": {
        "signup_url": "https://www.remoter.me/",
        "steps": [
            "1. Go to https://www.remoter.me/ and sign up",
            "2. Complete profile",
            "3. Browse available image/video annotation tasks",
            "4. Complete tasks and get paid per task ($50 minimum withdrawal)",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "Per-task; $50 minimum withdrawal",
        "prerequisites": [
            "Computer with internet connection",
            "Payment method for payouts",
        ],
        "notes": "Image and video annotation platform. Lower priority than Remotasks (functionally overlaps). $50 minimum withdrawal threshold. Include for completeness but Remotasks is generally the better-known option in this category.",
        "status_after_signup": "SIGNED_UP",
    },
    "clickworker.com": {
        "signup_url": "https://www.clickworker.com/",
        "steps": [
            "1. Go to https://www.clickworker.com/ and sign up",
            "2. Complete UHCI (User Generated Content Intelligence) setup if required",
            "3. Browse and complete microtasks, surveys, voice recordings, AI training tasks",
            "4. Get paid weekly",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "Per-task; paid weekly. Varies by task type.",
        "prerequisites": [
            "Computer with internet connection",
            "Payment method for weekly payouts",
        ],
        "notes": "General microtask platform that also includes AI training tasks (User Generated Content Intelligence). Weekly payouts. Lower barrier to entry than assessment-based platforms. Also serves as the sign-up path for LXT crowd contributors.",
        "status_after_signup": "SIGNED_UP",
    },
    "prolific.com": {
        "signup_url": "https://www.prolific.com/",
        "steps": [
            "1. Go to https://www.prolific.com/ and sign up",
            "2. Join the waitlist (if applicable — sometimes there's a waitlist)",
            "3. Complete identity verification when invited",
            "4. Start browsing and completing research studies (some are AI-relevant)",
            "5. Get paid per study completed (minimum £8/hr, typically £9-12/hr effective)",
        ],
        "assessment_required": False,
        "assessment_hours": 0,
        "assessment_once_only": False,
        "pay_range": "Minimum £8/hr (UK-regulated); effective rate typically £9-12/hr",
        "prerequisites": [
            "Email account",
            "Identity verification (when invited off waitlist)",
            "UK pounds sterling payout method (PayPal typically)",
        ],
        "notes": "Academic research studies platform, UK-regulated. Not specifically an AI training platform, but some studies are AI-relevant (evaluating AI outputs, providing human judgments). International users accepted but some studies have country restrictions. Waitlist may apply. Minimum hourly rate is a UK consumer protection, not a guarantee of study availability.",
        "status_after_signup": "SIGNED_UP",
    },
}


# Domains (bare, without scheme) whose URLs should return signup_flow instead of a scraped JD.
_ANNOTATION_DOMAINS = frozenset(ANNOTATION_PLATFORM_FLOWS.keys())


def _annotation_signup_jd(url, company, role, platform, domain):
    """
    Build a JD-like dict from the annotation platform's signup_flow metadata.
    This is NOT a scraped job description — it is the concrete steps to sign up
    for the platform, returned as full_jd so the pipeline does not need a real JD
    in order to render a CV.
    """
    flow = ANNOTATION_PLATFORM_FLOWS.get(domain, {})
    if not flow:
        return {
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
            "full_jd": f"(annotation platform: {domain} — no scrapeable JD; follow sign-up steps below)",
            "extraction_source": "signup_flow",
            "signup_flow": "",
            "assessment_required": False,
            "assessment_hours_estimate": 0,
            "pay_range": "",
            "notes": "",
        }

    steps_text = "\n".join(flow.get("steps", []))
    full_jd = (
        f"=== {company} — {role} ===\n"
        f"Platform: {domain}\n"
        f"Type: AI training / data annotation platform (sign-up required)\n"
        f"\n"
        f"SIGN-UP URL: {flow.get('signup_url', url)}\n"
        f"\n"
        f"SIGN-UP FLOW (concrete steps):\n"
        f"{steps_text}\n"
        f"\n"
        f"ASSESSMENT REQUIRED: {'YES' if flow.get('assessment_required') else 'NO'}\n"
        f"ASSESSMENT TIME ESTIMATE: {flow.get('assessment_hours', 0)} hour(s)\n"
        f"ASSESSMENT ONE-TIME ONLY: "
        f"{'YES — NO RETAKES' if flow.get('assessment_once_only') else 'NO'}\n"
        f"\n"
        f"PAY RANGE: {flow.get('pay_range', '(not publicly listed)')}\n"
        f"\n"
        f"PREREQUISITES (have these ready before starting):\n"
        + "\n".join(f"  - {p}" for p in flow.get("prerequisites", []))
        + "\n"
        f"\n"
        f"NOTES: {flow.get('notes', '')}\n"
    )

    return {
        "title": role,
        "company": company,
        "location": "Remote (sign-up required)",
        "apply_url": flow.get("signup_url", url),
        "url": url,
        "platform": platform or domain,
        "posted_date": TODAY,
        "type": "Contract/Freelance",
        "years_exp": "",
        "degree": "",
        "salary": flow.get("pay_range", ""),
        "required_skills": [],
        "full_jd": full_jd,
        "extraction_source": "signup_flow",
        "signup_flow": steps_text,
        "assessment_required": flow.get("assessment_required", False),
        "assessment_hours_estimate": flow.get("assessment_hours", 0),
        "pay_range": flow.get("pay_range", ""),
        "notes": flow.get("notes", ""),
    }


if __name__ == "__main__":
    main()

