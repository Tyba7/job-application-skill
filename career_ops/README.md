# career-ops add-ons

Glue between [career-ops](https://github.com/career-ops-hq/career-ops) and the Desktop job tracker CSV.

- `sync_career_ops.py`: copies career-ops `data/applications.md` rows into the tracker CSV. Dry run by default; `--write` backs up first. Never downgrades a status.
- `export_application.py`: copies a tailored CV PDF and ATS copy into `Apply_Queue_<DDMon>/<NN>_<Code>_<Company>/`, assigns the next UAE/KSA/REM code and fills the tracker row.
- `build_payload_example.py`: example of building a career-ops CV payload from `cv.md` that keeps every job, bullet, highlight and reference.
- `house_rules_custom.md`: the `modes/_custom.md` house rules used with career-ops.
- `daily_pipeline.py`: daily run. Searches LinkedIn (last 24h) for AI/ML jobs in UAE, KSA, Qatar and remote, scores fit from the full JD, skips Arabic-required, nationals-only, internships and 8+ yrs, and for fit >= 3 builds the tailored CV (PDF + ATS copy) with pre-vetted claims only, adds a tracker row (backup first) and exports via `export_application.py`. Prints the summary message. `--dry-run`, `--max N`, `--selftest`. Never applies.
- `hermes_daily_jobs.sh`: copy to `~/.hermes/scripts/daily_jobs.sh`, then `hermes cron create "0 8 * * *" --name daily-ai-jobs --script daily_jobs.sh --no-agent --deliver whatsapp`.
