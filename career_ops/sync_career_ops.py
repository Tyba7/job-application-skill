"""Copy career-ops tracker rows (~/code/career-ops/data/applications.md) into Tayyaba_Job_Application_Tracker.csv.

Run: python3 sync_career_ops.py            (dry run, prints changes)
     python3 sync_career_ops.py --write    (backs up the CSV, then writes)
"""
import csv, os, re, shutil, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "Tayyaba_Job_Application_Tracker.csv")
MD = os.path.expanduser("~/code/career-ops/data/applications.md")

# career-ops status -> tracker status
STATUS = {"evaluated": "Not applied", "applied": "Applied", "responded": "Interviewing", "assessment": "Interviewing",
          "interview": "Interviewing", "offer": "Interviewing", "hired": "Interviewing", "rejected": "Rejected",
          "discarded": "Skipped", "skip": "Skipped"}
# a tracker status the sync must never overwrite with an earlier stage
FINAL = {"Applied": 1, "Interviewing": 2, "Rejected": 3, "Withdrawn": 3, "Closed": 3}
RANK = {"Not applied": 0, "Skipped": 0, "Low priority": 0, **FINAL}

norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())


def read_md(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 9 or not cells[0].isdigit():
            continue
        num, date, company, role, score, status, pdf, report, notes = cells[:9]
        rows.append({"num": num, "date": date, "company": company, "role": role, "score": score,
                     "status": STATUS.get(status.lower(), "Not applied"), "report": report, "notes": notes})
    return rows


def sync(csv_rows, md_rows):
    by_key = {(norm(r["Company"]), norm(r["Job Title"])): r for r in csv_rows}
    next_num = max(int(r["#"]) for r in csv_rows if r["#"].isdigit()) + 1
    changes = []
    for m in md_rows:
        tag = f"career-ops #{m['num']} score {m['score']}"
        r = by_key.get((norm(m["company"]), norm(m["role"])))
        if r is None:
            r = {c: "" for c in csv_rows[0]}
            r.update({"#": str(next_num), "Company": m["company"], "Job Title": m["role"], "Source": "career-ops",
                      "Status": m["status"], "Date Applied": m["date"] if m["status"] == "Applied" else "",
                      "Notes": f"{tag}. {m['notes']}".strip()})
            csv_rows.append(r); by_key[(norm(m["company"]), norm(m["role"]))] = r
            changes.append(f"ADD #{next_num} {m['company']} | {m['role']} | {m['status']}"); next_num += 1
            continue
        if RANK.get(m["status"], 0) > RANK.get(r["Status"], 0):
            changes.append(f"UPDATE #{r['#']} {r['Company']} | {r['Status']} -> {m['status']}")
            r["Status"] = m["status"]
            if m["status"] == "Applied" and not r["Date Applied"]:
                r["Date Applied"] = m["date"]
        if tag not in r["Notes"]:
            r["Notes"] = f"{r['Notes']} | {tag}" if r["Notes"] else tag
    return changes


def selftest():
    rows = [{"#": "1", "Company": "Acme", "Job Title": "AI Engineer", "Source": "", "Status": "Withdrawn", "Date Applied": "", "Notes": ""},
            {"#": "2", "Company": "Beta", "Job Title": "ML Engineer", "Source": "", "Status": "Not applied", "Date Applied": "", "Notes": ""}]
    md = [{"num": "1", "date": "2026-10-01", "company": "ACME", "role": "AI engineer", "score": "4.1", "status": "Applied", "report": "", "notes": ""},
          {"num": "2", "date": "2026-10-02", "company": "Beta", "role": "ML Engineer", "score": "4.5", "status": "Applied", "report": "", "notes": ""},
          {"num": "3", "date": "2026-10-03", "company": "Gamma", "role": "MLOps", "score": "3.9", "status": "Not applied", "report": "", "notes": ""}]
    sync(rows, md)
    assert rows[0]["Status"] == "Withdrawn"  # later stage kept
    assert rows[1]["Status"] == "Applied" and rows[1]["Date Applied"] == "2026-10-02"
    assert rows[2]["#"] == "3" and rows[2]["Company"] == "Gamma"
    assert len(sync(rows, md)) == 0  # second run changes nothing


if __name__ == "__main__":
    selftest()
    if not os.path.exists(MD):
        sys.exit(f"No career-ops tracker yet at {MD}")
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    cols = list(rows[0].keys())
    changes = sync(rows, read_md(MD))
    print("\n".join(changes) or "No changes.")
    if "--write" in sys.argv and changes:
        backup = CSV.replace(".csv", f"_backup_{datetime.date.today()}_sync.csv")
        shutil.copy2(CSV, backup)
        with open(CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
        print(f"Written. Backup: {backup}")
