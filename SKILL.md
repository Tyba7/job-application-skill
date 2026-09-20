---
name: job-application
description: "End-to-end UAE AI/ML job application pipeline: discover, verify, research, extract, match, generate, QA, track. UAE-resident, no visa sponsorship needed."
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [job-search, cv-engineering, applications, UAE, pipeline]
    related_skills: [cv-engineering, productivity/docx, productivity/google-workspace]
---

# Job Application Pipeline

Operate Tayyaba Rizwan's job applications end-to-end. UAE-resident Applied AI Engineer based in Dubai — no visa sponsorship required, immediately available.

Each phase is a callable tool. Run the full pipeline or any phase independently. The system is stateful: folders and CSV track where each job is in the pipeline.

## Where Things Live

- **Working directory:** `~/vestwell_contact_center/`
- **Application folders:** `applications/<date>/<company>/` — one per target
- **Tracker:** `applications/<date>/applications.csv` — regenerated from ground truth every session
- **Master CVs:** `CV_HOLISTIC_MASTER.md` (source) + 4 DOCX variants in `applications/2026-09-18/`
- **CV batch generator:** `generate_cvs.py` (standalone, regenerates 4 masters from holistic master)
- **Docx toolkit:** `skills/productivity/docx/scripts/` — docx_read.py, docx_edit.py, docx_create.py, docx_validate.py, etc.
- **Job spec:** `job_applications.md` — pre-researched UAE/Saudi/Qatar roles
- **Today's shortlist:** `todays-applications.md` — 5 top targets
- **GitHub tracker repo:** `Tyba7/job-tracker` — private repo for issue-based application tracking (created on first use)
- **GitHub scripts:** `skills/job-application/scripts/github_discover.py`, `github_verify_company.py`, `github_track.py`

## Tool Inventory (Sequential Order)

These are the 8 tools in pipeline order. Each takes structured input and produces structured output. Run them in sequence for a full pipeline, or call any one independently.

### Tool 0: pipeline — `scripts/pipeline.py` (Orchestrator)

**What:** End-to-end pipeline orchestrator. Chains all 8 tools sequentially with one command. Each tool's output feeds the next. Non-fatal failures (dead links, extraction failures) are logged and the pipeline continues.

**Usage:**
```bash
python pipeline.py \
  --query "AI engineer UAE" \
  --max-jobs 20 \
  --output-dir ../../applications/2026-09-20 \
  --cv CV_Tayyaba_Rizwan_AI_Engineer_Master.docx \
  --github-repo Tyba7/job-tracker \
  --steps 1,2,3,4,5,6,7,8
```

**Steps (select with --steps, default: all):**
- `1` — discover_jobs + github_discover (merged)
- `2` — verify_links
- `3` — research_companies + github_verify_company
- `4` — extract_jd per live job
- `5` — match_to_cv per extracted JD
- `6` — render (CV + cover letter + README + jd.xlsx per company folder)
- `7` — qa_check per rendered CV
- `8` — track_applications (local CSV) + github_track (GitHub Issues)

**End result on disk:**
```

**What:** Search for live UAE AI/ML/GenAI roles across multiple platforms.

**Source:** This is done via `web_search` calls directly — no script. The agent searches 3-5 platforms in parallel and returns a ranked table.

**Query pattern:**
```
web_search('AI engineer Dubai UAE site:linkedin.com/jobs')
web_search('machine learning engineer Abu Dhabi site:indeed.ae')
web_search('genai engineer UAE site:bayt.com')
```

**Platforms (priority order):**
1. Indeed UAE (indeed.ae, indeed.com/ae)
2. LinkedIn Jobs (linkedin.com/jobs — filter: Past 24h / Past week)
3. Bayt (bayt.com)
4. NaukriGulf (naukrigulf.com)
5. Artificial.ae (artificial.ae)
6. AI-jobs.net (ai-jobs.net)
7. Employer portals (G42 careers.g42.ai, Telnyx, etc.)

**Output:** Ranked table — company, title, platform, posted date, apply URL, relevance score.

**Gate:** Present to user. They select 5 to advance. Nothing proceeds until user approves.

---

### Tool 1b: github_discover — `scripts/github_discover.py`

**What:** Search GitHub for UAE AI/ML job postings that may not appear on LinkedIn/Indeed. Supplements Tool 1 — catches startup hiring repos, GitHub Jobs board, and GitHub issue-based job posts.

**Source:** `scripts/github_discover.py` — uses `web_search` internally (no GitHub API key needed for search). Called as an additional discovery channel alongside the main platforms.

**Usage:**
```bash
python github_discover.py \
  --query "AI engineer UAE" \
  --location "UAE" \
  --output github_jobs.json
```

**What it searches:**
1. GitHub Jobs board (github.com/jobs) — official GitHub job board
2. GitHub repo READMEs mentioning "hiring" + UAE + AI/ML keywords
3. GitHub issues labeled or mentioning "hiring", "open position", "job opening"

**Output:** `github_jobs.json` — list of jobs from GitHub sources with company, role, location, apply_url, platform.

**Gate:** Merge GitHub results with Tool 1 results. Deduplicate by URL. Present combined ranked table. User selects from the combined list.

---

### Tool 2: verify_links — `scripts/verify_links.py`

**What:** Verify every selected posting is still live before building any artifacts.

**Input:** JSON file with list of {company, role, apply_url}

**Usage:**
```bash
python verify_links.py \
  --links selected_jobs.json \
  --output verification_results.json
```

**How it works:**
- Primary: `web_extract` on each apply URL
- Fallback: `web_search` for cached/indexed versions when extract is blocked (403/Cloudflare on Indeed, LinkedIn, Greenhouse)
- Kill signals detected: "no longer accepting applications", "has been filled", "job not found", "applications are closed"

**Output:** JSON with status per link — LIVE, DEAD, or UNKNOWN (verify manually). Plus a summary count.

**Gate:** Remove dead postings. User confirms remaining list. UNKNOWN items flagged for manual browser check.

---

### Tool 3: research_companies

**What:** Verify employer legitimacy and find the real apply channel.

**Source:** `web_search` calls — no script. For each verified posting:

```
web_search('<company> UAE review scam')
web_search('<company> careers site:greenhouse.io OR site:lever.co OR site:ashbyhq.com')
web_search('<company> UAE funding employees')
```

**What it finds:**
- Legitimacy flags (scam, fraud, complaint hits)
- Real career portal URL (ATS platform: Greenhouse, Lever, Ashby, Workday)
- Apply link status (OPEN / CLOSED / LOGIN REQUIRED)
- Company size and funding

**Output:** Research card per company — legitimacy, portal, apply link, size.

**Gate:** Flag any legitimacy concerns. User decides whether to proceed.

---

### Tool 3b: github_verify_company — `scripts/github_verify_company.py`

**What:** Verify company legitimacy and activity via GitHub. Supplements Tool 3 — catches companies with no GitHub presence (yellow flag for tech roles), dormant orgs (high risk), and confirms engineering team activity.

**Source:** `scripts/github_verify_company.py` — uses `gh` CLI (already authenticated as Tyba7). No API key needed.

**Usage:**
```bash
python github_verify_company.py \
  --company "Fuse Energy" \
  --output company_check.json
```

**What it checks:**
1. Does the company have a GitHub org or user account?
2. When was their last repo activity? (stale org = red flag for tech companies)
3. How many repos, stars, contributors? (signal of real engineering team)
4. Does their GitHub presence match their claimed industry?

**Risk levels:**
- **high** — Company has GitHub org but repos haven't been updated in 1+ years, or very few repos/stars for a claimed tech company
- **medium** — GitHub presence is thin but not dead (a few repos, modest activity)
- **low** — No GitHub presence (many legitimate companies don't use GitHub — this alone is not a red flag for non-engineering roles)
- **unknown** — Unable to assess

**Output:** `company_check.json` — risk level, github presence type, login, repo count, latest activity, findings list.

**Gate:** For tech roles (AI/ML engineer), a "high" risk level is a significant red flag — discuss with user. "low" from no GitHub presence is acceptable for non-engineering-heavy companies. Combine with Tool 3 web search results for full picture.

---

### Tool 4: extract_jd — `scripts/extract_jd.py`

**What:** Pull the full job description from each posting URL.

**Input:** Apply URL, company name, role title, platform

**Usage:**
```bash
python extract_jd.py \
  --url https://jobs.ashbyhq.com/openai/... \
  --company OpenAI \
  --role "Applied AI Engineer" \
  --platform ashby \
  --output jd.json
```

**How it works:**
- Primary: `web_extract` on the apply URL
- Fallback: `web_search` for cached/indexed versions when extract is blocked (Indeed, LinkedIn, Greenhouse all block extract ~95% of the time)
- Searches LinkedIn, Indeed, NaukriGulf indexed copies as additional fallbacks
- Parses structured fields: location, type, years_exp, degree, salary, required_skills
- Detects kill signals in search snippets (dead job detection)

**Output:** `jd.json` — structured JD dict with full_jd text, plus `jd.xlsx` written into the company folder as an immutable archive.

**Gate:** If JD is only partially recoverable, note what's missing and proceed — a partial JD is better than no JD.

---

### Tool 5: match_to_cv — `scripts/match_to_cv.py`

**What:** Evaluate fit between the user's CV and each JD requirement.

**Input:** CV .docx path, JD JSON path, optional codebase root path

**Usage:**
```bash
python match_to_cv.py \
  --cv CV_Tayyaba_Rizwan_AI_Engineer_Master.docx \
  --jd-json jd.json \
  --codebase /Users/tayyabarizwan/vestwell_contact_center/pipeline_v1 \
  --output match_result.json
```

**How it works:**
- Reads CV text via python-docx
- Searches codebase for evidence of each JD skill (grep-based)
- Builds match matrix: EXACT (CV + codebase), PARTIAL (one source), MISSING (neither)
- Computes fit score: HIGH (80%+), MEDIUM (60-80%), LOW (<60%)
- Identifies gaps: skills absent from both CV and codebase

**Output:** `match_result.json` — fit score, per-skill match details with evidence citations, gaps list.

**Gate:** Present fit scores. User selects which jobs to apply to. Low-fit jobs flagged but not automatically excluded.

---

### Tool 6: render — `scripts/renderer.py`

**What:** Generate all application documents for a selected job: tailored CV, cover letter, README, and jd.xlsx.

**Input:** Base CV path, JD JSON path, output directory, company name, role title

**Usage:**
```bash
python renderer.py \
  --cv-base CV_Tayyaba_Rizwan_AI_Engineer_Master.docx \
  --jd-json jd.json \
  --output-dir applications/2026-09-18/G42 \
  --company G42 \
  --role "AI Engineer"
```

**What it produces:**
- `CV_<Company>_<Role>.docx` — tailored CV (skills reordered to JD priority, summary opening line adjusted, experience bullets verbatim)
- `CoverLetter_<Company>_<Role>.docx` — one page, three paragraphs, names one genuine gap, closes with logistics
- `README.md` — role summary, fit analysis, interview prep focus, follow-up schedule
- `jd.xlsx` — full JD + extracted fields (immutable archive)

**Phone/contact:** Reads from constants in the script: +971589448527, tayyabarizwan87@gmail.com, Dubai UAE, linkedin.com/in/tayyaba-rizwan-3b0400248, github.com/Tyba7

**Alternatives:**
- For batch CV generation from master: `generate_cvs.py` (standalone, in vestwell_contact_center root)

**Gate:** Show the draft before applying. Present before/after for every bullet and wait for explicit approval.

---

### Tool 7: qa_check — `scripts/qa_check.py`

**What:** Run keyword coverage + formatting checks on rendered CVs before delivery.

**Input:** CV .docx path (or glob), required keywords, expected link/bullet counts

**Usage:**
```bash
# Single file
python qa_check.py \
  --cv applications/2026-09-18/G42/CV_G42_AI_Engineer.docx \
  --must-keys Python,RAG,LLM,Databricks,PySpark \
  --expected-links 1 \
  --expected-bullets 10 \
  --output qareport.json

# Batch — check all CVs in a folder
python qa_check.py \
  --cv "applications/2026-09-18/*/CV_*.docx" \
  --must-keys Python,RAG,LLM \
  --glob \
  --output qareport.json
```

**Checks:**
- **Keyword presence:** case-insensitive, with surface-form variant detection (e.g. "Conversational AI" vs "chatbot", "Kubernetes" vs "k8s")
- **Link count:** asserts expected hyperlink count
- **Bullet count:** asserts expected bullet count
- **Usable width:** flags if too narrow (<150mm) or too wide (>200mm)
- **Tables:** flags if present (ATS-unfriendly)
- **Headers/footers:** flags if present
- **Lock files:** skips `~$`-prefixed Word temp files
- **List Bullet font:** warns if bullets have 0pt font (the python-docx bug)

**Output:** `qareport.json` — per-file pass/fail, missing keywords, formatting anomalies, flags.

**Gate:** Fix any FAIL items. User approves before final delivery.

---

### Tool 8: track_applications — `scripts/track_applications.py`

**What:** Regenerate the applications.csv tracker from folder ground truth.

**Rule:** Never append — always rebuild from what's actually on disk. A tracker written early in a session encodes stale state.

**Usage:**
```bash
python track_applications.py \
  --root applications/2026-09-18 \
  --output applications/2026-09-18/applications.csv
```

**How it works:**
- Walks each company subfolder
- Detects which files exist (cv.docx, cover_letter.docx, jd.xlsx, README.md)
- Infers status from file set: DISCOVERED, RESEARCHED, EXTRACTED, GENERATED, QA-PASS, APPLIED
- Extracts role and apply URL from README.md
- Writes one row per company with correct status

**Status inference:**
| Files present | Status |
|---|---|
| (none) | DISCOVERED |
| README.md only | RESEARCHED |
| jd.xlsx | EXTRACTED |
| cv.docx | GENERATED |
| cv.docx + cover_letter.docx | QA-PASS |
| cv.docx + cover_letter.docx + jd.xlsx + README.md | APPLIED |

**Output:** `applications.csv` — sorted by priority, one row per company, correct status.

**Gate:** Present the regenerated tracker. Confirm counts match expectations. Flag any company folders that exist without a CSV row.

---

### Tool 8b: github_track — `scripts/github_track.py`

**What:** Track applications as GitHub Issues in a private repo. Provides a cloud-synced, searchable, labelable, commentable application tracker that complements the local CSV tracker. Accessible from any machine, with full history and interview notes in issue comments.

**Source:** `scripts/github_track.py` — uses `gh` CLI (already authenticated as Tyba7). Creates the private repo `Tyba7/job-tracker` on first use if it doesn't exist.

**Setup (one-time):**
```bash
python github_track.py --repo Tyba7/job-tracker --action create-repo
```
This creates the private repo and sets up standard labels: applied, interviewing, technical, offer, rejected, dropped, todo, dead, not-my-domain.

**Usage:**

Add an application:
```bash
python github_track.py \
  --repo Tyba7/job-tracker \
  --action add \
  --company "Fuse Energy" \
  --role "Applied AI Engineer" \
  --location "Dubai" \
  --url "https://..." \
  --platform "LinkedIn" \
  --notes "Applied via LinkedIn on 2026-09-20"
```

List all applications:
```bash
python github_track.py --repo Tyba7/job-tracker --action list
```

Filter by status:
```bash
python github_track.py --repo Tyba7/job-tracker --action list --filter applied
```

Update status (e.g. after an interview):
```bash
python github_track.py \
  --repo Tyba7/job-tracker \
  --action update \
  --number 42 \
  --status interviewing \
  --notes "Technical screen scheduled for Monday"
```

Add a comment (interview feedback, reminder):
```bash
python github_track.py \
  --repo Tyba7/job-tracker \
  --action comment \
  --number 42 \
  --body "Interview feedback: strong on RAG, weak on Kubernetes. Follow up on K8s in next round."
```

Close/reject:
```bash
python github_track.py \
  --repo Tyba7/job-tracker \
  --action close \
  --number 42 \
  --reason rejected
```

Export to CSV (compatible with applications.csv format):
```bash
python github_track.py \
  --repo Tyba7/job-tracker \
  --action export \
  --output applications_export.csv
```

**Labels:** applied, interviewing, technical, offer, rejected, dropped, todo, dead, not-my-domain

**Output (list):** Table of issues with number, status, company, role, location, date, URL.

**Output (export):** CSV compatible with the local `applications.csv` format.

**Gate:** The GitHub tracker is an ALTERNATIVE or SUPPLEMENT to the local CSV tracker. Use it when you want cloud-synced tracking accessible from multiple machines, or when you want to keep interview notes and follow-up reminders attached to each application. The local CSV remains the primary tracker for the pipeline; GitHub Issues is the persistent long-term tracker.

---

## Full Pipeline (all 10 tools in order — 8 core + 2 GitHub supplements)

```
# 1. Discover (main platforms)
web_search × 5 platforms → selected_jobs.json (user picks 5)

# 1b. Discover (GitHub supplementary — optional)
python github_discover.py --query "AI engineer UAE" --output github_jobs.json
→ Merge with Tool 1 results, deduplicate by URL, present combined table.

# 2. Verify
python verify_links.py --links selected_jobs.json --output verified.json
→ Remove DEAD. User confirms LIVE list.

# 3. Research (web)
web_search per company → research cards
→ User confirms company list.

# 3b. Research (GitHub company verification — optional per company)
python github_verify_company.py --company "<name>" --output check.json
→ Risk level + GitHub activity per company. Flag high-risk.

# 4. Extract
python extract_jd.py --url <url> --company <co> --role <role> --output jd.json
→ Write jd.xlsx into company folder.

# 5. Match
python match_to_cv.py --cv <base_cv> --jd-json jd.json --output match.json
→ Present fit scores. User picks which to apply to.

# 6. Render
python renderer.py --cv-base <base_cv> --jd-json jd.json \
  --output-dir <company_folder> --company <co> --role <role>
→ CV + cover letter + README + jd.xlsx written.

# 7. QA
python qa_check.py --cv <cv_path> --must-keys <keys> --output qareport.json
→ Fix any FAIL items. User approves.

# 8. Track (local CSV)
python track_applications.py --root applications/<date> --output applications.csv
→ Tracker regenerated. User submits manually.

# 8b. Track (GitHub — optional, persistent, cloud-synced)
python github_track.py --repo Tyba7/job-tracker --action add \
  --company <co> --role <role> --location <loc> --url <url> \
  --platform <platform> --notes "<notes>"
→ Application tracked as a GitHub Issue with labels, comments, full history.
```

## Operating Rules

- One task per turn. Do not plan ahead. Do not summarize what you just did.
- When given a spec, execute it exactly. Do not add "helpful" extras.
- When you hit an error, diagnose with one small command before retrying.
- When you've made 3 failed attempts at the same thing, stop and report.
- If a posting is dead, stop and report — do not silently substitute.
- If you haven't verified a link is live within 24 hours, say so.
- If you don't know something, say "I don't know" — never invent files, URLs, companies, or job postings.
- Never claim a job exists because it appeared in a previous session's summary.
- Never write a status report without checking the actual file system.
- Browser is NOT a reliable fallback for job verification or JD extraction. Do not use browser_exec for these tasks.
- Show the draft before applying. Present before/after for every bullet and wait for explicit approval.

## Truth Rules

- UAE Resident — no visa sponsorship required. Immediately available.
- Never invent experience, metrics, tools, or companies not in the source CV or codebase.
- CV experience bullets stay verbatim across tailored versions — only summary opening line and skills order change.
- Cover letters must differ per company — a letter that only changes the company name is one letter sent five times.
- CV must never remove a skill or keyword without asking first.
- Short-course certificates dilute a senior CV — cut them once experience carries the claim.

## Voice

- Direct. Blunt. No corporate hedging.
- No "I'd be happy to help" — just help.
- No emojis in work output.
- When reporting failure, lead with what broke, then what you tried, then what you need.

## User Workflow

### End-to-end (single trigger — all 8 tools chain automatically)

Say one phrase that names the skill and states the goal. The skill chains all 8 tools sequentially — each tool's output feeds the next, with no manual gates mid-pipeline. The chain stops only if a tool fails (dead links, extraction failures, etc.); otherwise it runs straight through to the final CSV.

**Trigger phrases:**

- **"Use the job-application skill to find me 20 jobs in UAE."**
- **"Run job-application: find 20 UAE AI/ML roles and build the full application package."**
- **"job-application: discover 20 roles in UAE, verify, research, extract JDs, match to CV, render documents, QA, and produce the tracker CSV."**

**What happens (sequential chain):**

```
1. discover_jobs  → web_search × 5 platforms → top 20 ranked jobs (company, title, platform, posted date, apply URL)
1b. github_discover → python github_discover.py → GitHub-sourced jobs merged in (startups, GitHub Jobs board)
2. verify_links   → python verify_links.py       → LIVE / DEAD / UNKNOWN per job (dead ones dropped)
3. research_companies → web_search per LIVE job → legitimacy, real ATS portal, apply link status
3b. github_verify_company → python github_verify_company.py per company → GitHub activity, risk level
4. extract_jd     → python extract_jd.py × each LIVE job → jd.json + jd.xlsx written into each company folder
5. match_to_cv    → python match_to_cv.py × each LIVE job → fit score + gaps per job
6. render         → python renderer.py × each LIVE job → CV + CoverLetter + README + jd.xlsx per company folder
7. qa_check       → python qa_check.py × each rendered CV → PASS / FAIL per CV with missing keywords and flags
8. track_applications → python track_applications.py → applications.csv with one row per company, correct status
8b. github_track  → python github_track.py --action add × each applied job → GitHub Issue per application
```

**End result on disk:**

```
applications/2026-09-19/               ← date folder (today's date)
  G42/
    CV_G42_AI_Engineer.docx             ← tailored CV
    CoverLetter_G42_AI_Engineer.docx    ← tailored cover letter
    README.md                            ← role summary, fit, interview prep
    jd.xlsx                              ← extracted JD archive
  OpenAI/
    CV_OpenAI_Applied_AI_Engineer.docx
    CoverLetter_OpenAI_Applied_AI_Engineer.docx
    README.md
    jd.xlsx
  ... (one folder per LIVE job, up to 20)
  applications.csv                       ← ALL jobs listed, one row per company, status per row
```

**The CSV is the final handoff.** It lists every job that made it through the pipeline with: priority, company, role, location, status, apply_link, apply_route, folder, cv_file, cover_letter, jd_xlsx, readme, notes. You then open it and update statuses / notes / priorities as you submit.

**Failure handling:** If verification finds dead links, those are dropped and the chain continues with the remaining LIVE jobs. If extraction fails for a job, that job is flagged and skipped — the chain does not stop. If rendering fails for a specific job, that job's folder is incomplete and flagged in the CSV notes. The user is notified at the end of the run which jobs succeeded fully and which had partial failures.

### Step-by-step (manual control — use when you want to steer each phase)

Use these when you want to stop and decide at each gate:

1. **"Find me AI jobs in Dubai."** → Tool 1 (discover) + Tool 1b (github_discover) → Present combined table → User selects N
2. **"Verify these."** → Tool 2 (verify_links) → Show live/dead → User confirms
3. **"Research the companies."** → Tool 3 (research) + Tool 3b (github_verify_company) → Show research cards + GitHub risk → User confirms
4. **"Match these to my CV."** → Tool 5 (match_to_cv) → Show fit scores → User picks which to apply to
5. **"Generate documents for these."** → Tool 6 (render) → Files written to disk
6. **"QA check."** → Tool 7 (qa_check) → Show QA reports → Fix any FAIL items
7. **"Track these applications."** → Tool 8 (track_applications) + Tool 8b (github_track) → CSV updated + GitHub Issues created
8. **"I'm ready to submit."** → User submits manually via apply URLs

Each phase can be skipped or re-run. The system is stateful: folders and CSV track where each job is in the pipeline.

### Which to use

- **End-to-end** when you want the full pipeline run start to finish with minimal interaction — best for bulk discovery runs.
- **Step-by-step** when you want to review and approve at each stage — best for high-value targets or when you want to steer emphasis.

## Existing Scripts (also available)

These standalone scripts in `~/vestwell_contact_center/` are also usable:

- **generate_cvs.py** — Batch CV generator. Reads `CV_HOLISTIC_MASTER.md` and produces 4 DOCX variants (AI_Engineer, ML_Engineer, DataScientist, Holistic). Run: `python3 generate_cvs.py`.

## GitHub Scripts (job-application skill)

Located in `skills/job-application/scripts/`:

- **github_discover.py** — Discover UAE AI/ML jobs from GitHub sources (GitHub Jobs board, repo READMEs, issues). Run: `python github_discover.py --query "AI engineer UAE" --output github_jobs.json`.
- **github_verify_company.py** — Verify company legitimacy and activity via GitHub. Run: `python github_verify_company.py --company "Fuse Energy" --output check.json`.
- **github_track.py** — Track applications as GitHub Issues in a private repo. Run: `python github_track.py --repo Tyba7/job-tracker --action add --company ... --role ... --url ...`.

## Docx Toolkit (used by render and qa_check)

`skills/productivity/docx/scripts/`:
- `docx_read.py` — read .docx text, structure, styles, images, revisions
- `docx_edit.py` — find/replace, insert paragraphs, edit runs
- `docx_create.py` — create .docx from JSON spec
- `docx_validate.py` — validate .docx structure
- `docx_common.py` — shared helpers
- `docx_template.py` — template management
- `docx_comments.py` — comment handling
- `docx_revisions.py` — revision tracking
