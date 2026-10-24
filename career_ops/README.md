# career-ops add-ons

Glue between [career-ops](https://github.com/career-ops-hq/career-ops) and the Desktop job tracker CSV.

- `sync_career_ops.py`: copies career-ops `data/applications.md` rows into the tracker CSV. Dry run by default; `--write` backs up first. Never downgrades a status.
- `export_application.py`: copies a tailored CV PDF and ATS copy into `Apply_Queue_<DDMon>/<NN>_<Code>_<Company>/`, assigns the next UAE/KSA/REM code and fills the tracker row.
- `build_payload_example.py`: example of building a career-ops CV payload from `cv.md` that keeps every job, bullet, highlight and reference.
- `house_rules_custom.md`: the `modes/_custom.md` house rules used with career-ops.
