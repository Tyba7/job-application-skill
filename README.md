# Job Application Skill — UAE AI/ML Job Pipeline

End-to-end pipeline for discovering, verifying, researching, and applying to AI/ML jobs in the UAE (Dubai, Abu Dhabi, remote UAE). Designed for Hermes Agent. Produces dated application folders with per-job CV + cover letter + JD XLSX, plus a master CSV you can click through and apply from.

## What this skill does

Given a date (or today), it:

1. **Discovers** candidate UAE AI/ML job listings (LinkedIn, Bayt, Indeed, NaukriGulf, AIU.AE, Glassdoor, employer career pages).
2. **Verifies** each listing is actually live (not expired/dead) by checking the source.
3. **Researches** company background where available.
4. **Extracts** the full job description into a structured JD JSON + JD XLSX.
5. **Matches** each JD against a master CV to pick the best CV variant for that role.
6. **Renders** a per-job CV and cover letter (DOCX) personalized to the JD.
7. **QA-checks** every rendered document for formatting issues (no leaked markdown, no blanks).
8. **Tracks** applications (status: Applied / Interviewing / Rejected / etc.) in a CSV + optional GitHub tracker repo.

The end result is a `applications/YYYY-MM-DD/` folder with one subfolder per job, each containing:
- `CV_<Role>.docx`
- `CoverLetter_<Role>.docx`
- `jd.xlsx` (parsed job description)
- `jd.json` (structured JD)
- `README.md` (role summary + how to apply)

And a root `applications.csv` with all jobs, clickable application links, and status.

## Requirements

- Hermes Agent installed and configured.
- Python 3 with `python-docx`, `openpyxl` available.
- For the GitHub tracker path: `gh` CLI authenticated.
- A master CV source (Markdown) plus a DOCX generator that converts it to clean DOCX (no leaked markdown, no raw `**`, backticks, `---`, `####` in output).

## Quick start

Load the skill, then ask Hermes to run the pipeline for today:

```
Use the job-application skill and complete today's UAE AI/ML job applications.
```

For a custom date:

```
Use the job-application skill to build applications for 2026-09-21.
```

You can also invoke individual tools directly from the scripts directory for one-off tasks (discover, verify, render, track, etc.). See SKILL.md for the full sequential tool order and per-tool usage.

## Repository layout

```
job-application-skill/
├── SKILL.md            # Full skill definition + tool inventory + workflow
└── scripts/
    ├── pipeline.py         # Main orchestrator — runs tools in sequence
    ├── github_discover.py  # Discover jobs via GitHub (optional path)
    ├── github_verify_company.py
    ├── github_track.py     # Track applications in a GitHub repo
    ├── track_applications.py
    ├── verify_links.py     # Verify job links are live
    ├── extract_jd.py       # Extract + structure job descriptions
    ├── match_to_cv.py      # Match JD to best CV variant
    ├── renderer.py         # Render per-job CV + cover letter DOCX
    ├── qa_check.py         # QA-check rendered documents
    ├── config_template.json  # Safe config template (copy to .app_config.json)
    ├── .app_config.json   # ⚠️ Local config — NOT committed (see .gitignore)
    └── .gitignore
```

## Config

Copy `scripts/config_template.json` to `scripts/.app_config.json` and fill in your details:

```bash
cp scripts/config_template.json scripts/.app_config.json
# edit .app_config.json with your name, email, phone, LinkedIn, GitHub, location
```

`.app_config.json` is gitignored — it stays local. Never commit your personal contact info.

## Public use

This repo can be made public so others can use the skill. Personal info stays in `.app_config.json` (gitignored). Code references to `<your-gh-username>` are placeholders — replace with your own.

## License

MIT — use it, fork it, improve it.
