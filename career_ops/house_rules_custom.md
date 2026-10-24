# Custom Instructions -- career-ops

<!-- User-layer file: never auto-updated. Procedural house rules for Tayyaba Rizwan's job search. -->

## House Rules

### Source of truth and truthfulness
- Tailor every CV from `cv.md` (the full master). Never start from a previously tailored CV.
- Never shrink experience. Keep all 4 jobs. Tailoring may reorder and reword bullets, never delete jobs or real achievements. Minimum bullets: 5-6 for Invisible Technologies (Vestwell) and Afiniti, 3 for AI DataYard, 2 for Humanetek. Keep Career Highlights.
- Keep 2 pages maximum by tightening wording, not by dropping experience.
- Never remove a skill or keyword from the master without asking first.
- Never invent experience, metrics, tools, employers or certifications. Multi-GPU training/pretraining is a real gap: never claim it.
- If something is unknown, say "I don't know". Never claim a job exists because an earlier summary said so: verify the link is live first.

### Tailoring method
- Pull must-have skills, tools and title words from the JD. Use the JD's exact term at least once (skills list or summary) for ATS; bullets may use natural wording.
- Headline: match the JD title plus its top 2-3 skills.
- Summary: 3-4 lines, lead with the JD's main focus and the matching proof (Afiniti = financial services, Vestwell = production LLM/voice AI).
- Reorder bullets within each job so JD-relevant ones come first. Reorder the skills section to the JD stack.
- Seniority language: senior roles get lead/own/architect; mid roles get build/ship/improve.
- Put real gaps in the tracker "Gaps to Prepare For" column and address one genuine gap in the cover letter. Never fake them.
- Location line near the top: UAE resident, all Emirates, no sponsorship needed. Never write "immediately available" anywhere (CV or cover letter).
- ATS-safe format: PDF plus ATS copy, no tables or columns, standard headings.

### Cover letters
- One page, three paragraphs, ends with logistics (UAE resident, no sponsorship needed).
- Every letter must differ per company: a letter that only changes the company name is not allowed.

### Discovery and batches
- Markets: UAE (Dubai, Abu Dhabi, Sharjah) and Saudi Arabia (Riyadh, Jeddah, Dammam). Remote roles open to UAE residents also count.
- Before adding a job, deduplicate against the tracker CSV (path under Output Preferences) by company + job title. Skip anything already Applied, Withdrawn, Closed or Rejected.
- Skip: internships, graduate programmes, junior-only roles, non-engineering roles, temp contracts, postings older than ~45 days, closed links (check before tailoring).

### Pipeline settings
- Always run the `--ats` variant (Step 21a) so there is a plain-text CV to paste into ATS forms.
- If `jd-skill-gap.mjs` reports `no-requirements-section` (common on Lever: "Key Responsibilities", "Academic Qualifications", "Preferred"), copy the JD to a temp file with those headings renamed to `## Requirements`, rerun the check on the copy, and keep the archived JD verbatim. Ignore generic words it flags as gaps (Develop, Ensure, API, CI, Git).
- After any career-ops tracker change, run `python3 /Users/tayyabarizwan/Desktop/Tayyaba_Job_Applications/sync_career_ops.py` (dry run), show the changes, then rerun with `--write`.
- CV payload must carry everything in cv.md: Career Highlights as `projects[]` with `sections.projects: "Career Highlights"` (short `name` + the highlight verbatim as `description`), and Languages (with UAE Driving Licence) and References as the last two `skills[]` lines. Do not use `competencies[]` or `awards[]` (they duplicate Skills and Education and push the CV to 3 pages). Default template is `compact` (original font size; fits 2 pages with all 21 bullets). Summary = master summary verbatim (keeps 600,000+ interactions, speech-to-text pipeline, 19 KPIs); tailoring may only add one sentence. Header uses full name "Tayyaba Rizwan Malik Rizwan Ahmed" (title case, not upper case). Experience heading is "Invisible Technologies Inc." with no "(Client: Vestwell)" and the master location line.
- `candidate.title` (headline) must not claim a seniority above "Applied AI Engineer" unless the user approves it for that job.
- After the PDF and ATS copy pass their checks, export to the Desktop with:
  `cd /Users/tayyabarizwan/Desktop/Tayyaba_Job_Applications && python3 export_application.py --payload <payload.json> --pdf <pdf> --ats-html <ats.html> --company "<Company>" --role "<Role>" --market <UAE|KSA|REM> --keywords "<keywords added>" --gaps "<gaps>"`
  It assigns the next job code, creates `Apply_Queue_<DDMon>/<NN>_<Code>_<Company>/` with `Tayyaba_Rizwan_CV_<Code>_<Company>.pdf/_ATS.html` (no .docx), and fills CV File, CV Folder, Headline Used, Keywords Added and Gaps in the tracker CSV (backup first). Rerunning reuses the same code and folder.

## Custom Workflows

### "daily batch" (UAE + Saudi)
1. Scan for ~20 fresh AI/ML roles (10 UAE, 10 Saudi), verify each link is live, dedupe against the tracker CSV.
2. Score each one; rank STRONG / HIGH / GOOD with a one-line "why".
3. Save the batch list to `/Users/tayyabarizwan/Desktop/Tayyaba_Job_Applications/Apply_Queue_<DDMon>/` (e.g. `Apply_Queue_23Oct`) as `UAE_Saudi_Job_Batch_<YYYY-MM-DD>.md`, plus `APPLY_ORDER.csv` with columns: Order,Tracker #,Code,Company,Role,Apply link,Cover letter,Notes.
4. For each job the user picks: tailored CV + cover letter in its own folder `Apply_Queue_<DDMon>/<NN>_<Code>_<Company>/`.
5. Add the jobs to the tracker CSV as "Not applied".

### "update tracker"
- Back up the tracker CSV first as `Tayyaba_Job_Application_Tracker_backup_<YYYY-MM-DD>.csv`.
- Match by company + job title; set Status and Date Applied; add new rows with the next # number; list unclear matches for the user to check.
- A later "Withdrawn" or "Rejected" beats an older "Applied". Never change Date Applied to the date of the run.

## Output Preferences

### Files and naming
- Tracker (single source of truth): `/Users/tayyabarizwan/Desktop/Tayyaba_Job_Applications/Tayyaba_Job_Application_Tracker.csv`. Columns: #,Market,Job Title,Company,Location / Eligibility,Work Mode,Posted,Source,Job Link,CV File,CV Folder,Headline Used,Keywords Added,Gaps to Prepare For,Status,Date Applied,Notes. Statuses: Not applied, Applied, Rejected, Interviewing, Withdrawn, Closed, Skipped, Low priority. Mirror every new career-ops tracker entry into this CSV.
- Job codes: `UAE-<n>` for UAE, `KSA-<n>` for Saudi, `REM-<n>` for remote, numbered after the highest existing code in the tracker.
- CV file: `Tayyaba_Rizwan_CV_<Code>_<Company>.pdf`. Cover letter: `Tayyaba_Rizwan_CoverLetter_<Code>_<Company>.docx`.
- After the user submits, the job folder moves to `/Users/tayyabarizwan/Desktop/Tayyaba_Job_Applications/Applied/<UAE|KSA|Remote>/<Code>_<Company>/`.
- Record "Headline Used", "Keywords Added" and "Gaps to Prepare For" in the tracker for every tailored CV.

### Reports
- Lead with score and one-line verdict. Keep batch summaries short: table of company, role, location, priority, why.

## Off-Limits
- Never submit an application, send an email or message a recruiter for the user. Prepare everything; the user presses Submit.
- Never send, delete or archive Gmail messages.
- Never overwrite the tracker CSV without a dated backup first.
