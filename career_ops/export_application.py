"""Export a career-ops tailored CV into the Desktop Apply_Queue folder with Tayyaba's naming.

Run:
  python3 export_application.py \
      --payload /tmp/cv-tayyaba-rizwan-001-soum.json \
      --pdf ~/code/career-ops/output/cv-tayyaba-rizwan-001-soum-2026-10-24.pdf \
      --company SOUM --role "AI / GenAI Solutions Engineer" --market REM \
      [--ats-html ...] [--keywords "..."] [--gaps "..."] [--date 2026-10-24]

Creates Apply_Queue_<DDMon>/<NN>_<Code>_<Company>/ with
  Tayyaba_Rizwan_CV_<Code>_<Company>.pdf (and _ATS.html), then fills the tracker CSV row
  (CV File, CV Folder, Headline Used, Keywords Added, Gaps to Prepare For), backing up the CSV first.
"""
import argparse, csv, datetime, json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "Tayyaba_Job_Application_Tracker.csv")
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
slug = lambda s: re.sub(r"[^A-Za-z0-9-]+", "", s)  # "Vatic Labs" -> "VaticLabs", matching existing folders


def next_code(market):
    """Highest existing <market>-<n> anywhere in the tracker or folder names, plus one."""
    nums = [0]
    for row in csv.DictReader(open(CSV, encoding="utf-8")):
        nums += [int(n) for n in re.findall(rf"{market}-(\d+)", " ".join(row.values()))]
    for _, dirs, files in os.walk(HERE):
        nums += [int(n) for name in dirs + files for n in re.findall(rf"{market}-(\d+)", name)]
    return f"{market}-{max(nums) + 1:02d}"


def main():
    ap = argparse.ArgumentParser()
    for a in ("--payload", "--pdf", "--company", "--role", "--market"):
        ap.add_argument(a, required=True)
    ap.add_argument("--ats-html"); ap.add_argument("--keywords", default=""); ap.add_argument("--gaps", default="")
    ap.add_argument("--date", default=str(datetime.date.today()))
    a = ap.parse_args()
    p = json.load(open(a.payload, encoding="utf-8"))

    rows = list(csv.DictReader(open(CSV, encoding="utf-8"))); cols = list(rows[0].keys())
    row = next((r for r in rows if norm(r["Company"]) == norm(a.company) and norm(r["Job Title"]) == norm(a.role)), None)
    if row is None:
        raise SystemExit(f"No tracker row for {a.company} | {a.role}. Run sync_career_ops.py --write first.")
    existing = re.search(r"(UAE|REM|KSA)-\d+", row["CV File"] or "")
    code = existing.group(0) if existing else next_code(a.market)

    d = datetime.date.fromisoformat(a.date)
    queue = os.path.join(HERE, f"Apply_Queue_{d.day:02d}{d.strftime('%b')}")
    os.makedirs(queue, exist_ok=True)
    company = slug(a.company)
    folder = next((os.path.join(queue, f) for f in os.listdir(queue) if f.endswith(f"_{code}_{company}")), None)
    if folder is None:
        n = 1 + sum(1 for f in os.listdir(queue) if re.match(r"\d+_", f))
        folder = os.path.join(queue, f"{n:02d}_{code}_{company}")
    os.makedirs(folder, exist_ok=True)

    base = f"Tayyaba_Rizwan_CV_{code}_{company}"
    shutil.copy2(os.path.expanduser(a.pdf), os.path.join(folder, base + ".pdf"))
    if a.ats_html:
        shutil.copy2(os.path.expanduser(a.ats_html), os.path.join(folder, base + "_ATS.html"))

    shutil.copy2(CSV, CSV.replace(".csv", f"_backup_{datetime.date.today()}_export.csv"))
    row.update({"CV File": base + ".pdf", "CV Folder": os.path.relpath(folder, HERE),
                "Headline Used": p["candidate"].get("title", ""),
                "Keywords Added": a.keywords or row["Keywords Added"], "Gaps to Prepare For": a.gaps or row["Gaps to Prepare For"]})
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"{code} -> {os.path.relpath(folder, HERE)}")
    for f in sorted(os.listdir(folder)):
        print("  ", f)


if __name__ == "__main__":
    main()
