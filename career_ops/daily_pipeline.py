"""Daily job pipeline: search LinkedIn for new AI/ML jobs in UAE, KSA, Qatar (incl. remote),
score fit from the full JD, build a tailored career-ops CV (PDF + ATS copy) for each job with fit >= 3,
add it to the tracker CSV and export it to Apply_Queue_<DDMon>/. Prints a short summary
(the message Hermes delivers to WhatsApp). Never applies anywhere.

Run:
  python3 daily_pipeline.py              # full run
  python3 daily_pipeline.py --dry-run    # search + score only, nothing written
  python3 daily_pipeline.py --selftest

Tailoring is deterministic: every headline/sentence below is a pre-vetted, true claim from cv.md,
picked by JD keywords. No LLM writes CV text, so house rules cannot drift.
"""
import argparse, csv, datetime, html, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request

CO = os.path.expanduser("~/code/career-ops")
APPS = os.path.expanduser("~/Desktop/Tayyaba_Job_Applications")
TRACKER = os.path.join(APPS, "Tayyaba_Job_Application_Tracker.csv")
STATE = os.path.expanduser("~/.hermes/job-pipeline")
HERE = os.path.dirname(os.path.abspath(__file__))
LI = "https://www.linkedin.com/jobs-guest/jobs/api/"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

LOCATIONS = {"United Arab Emirates": "UAE", "Saudi Arabia": "KSA", "Qatar": "QAT"}
KEYWORDS = ["AI Engineer", "Machine Learning Engineer", "LLM", "Generative AI", "Applied AI", "NLP", "Agentic AI", "MLOps"]
TITLE_OK = re.compile(r"\b(AI|A\.I\.|ML|LLM|GenAI|Gen AI|Generative|Machine Learning|NLP|Data Scien|Agentic|Agent|Conversational|MLOps|Deep Learning|Artificial Intelligence)", re.I)
TITLE_SKIP = re.compile(r"\b(intern|internship|trainee|director|head of|vp|vice president|principal|staff|professor|lecturer|teacher|tutor|sales|recruiter|product manager|project manager|marketing)\b", re.I)
MAX_NEW = 8

# Fit: each group hit in the JD is +0.5 on a base of 1; each unclaimed must-have is -0.75.
GROUPS = {
    "llm": r"\bLLMs?\b|large language model|generative ai|genai|gpt|prompt",
    "rag": r"\bRAG\b|retrieval|vector (db|database|store)|embedding|faiss|semantic search",
    "agents": r"\bagent(s|ic)?\b|tool calling|function calling|langgraph|langchain|crewai|autogen",
    "eval": r"evaluat|llm-as-(a-)?judge|benchmark|guardrail|hallucinat",
    "python": r"\bpython\b|fastapi|flask",
    "nlp_speech": r"\bNLP\b|natural language|speech|asr|whisper|voice|conversational|chatbot|diarization",
    "mlops": r"mlops|llmops|mlflow|databricks|deploy|production|monitoring|observability",
    "cloud": r"\baws\b|\bgcp\b|google cloud|azure|docker|cloud run|bedrock|vertex",
    "ml": r"machine learning|deep learning|pytorch|hugging ?face|transformers|fine-tun|scikit",
}
UNCLAIMED = r"typescript|react(\.js|js)?\b|kubernetes|\bk8s\b|terraform|\bjava\b(?!script)|\bc#|\.net\b|golang|\bgo\b developer|computer vision|\bphd\b required|scala\b"
HARD_SKIP = [
    (r"\b(fluent|fluency|native|proficien\w*|excellent|strong)\b[^.\n]{0,40}\barabic\b|\barabic\b[^.\n]{0,30}\b(required|must|mandatory|essential)", "Arabic required"),
    (r"\b(uae|saudi|qatari|emirati|gcc) nationals? only|\bonly (uae|saudi|qatari|emirati) nationals|\bsaudi nationals?\b[^.\n]{0,20}(only|required)|emiratisation|saudization", "Nationals only"),
    (r"\binternship\b|\bintern\b", "Internship"),
]
COVER = re.compile(r"cover letter|motivation letter|letter of motivation", re.I)

# Pre-vetted tailoring presets (same claims the main session already fact-checked against cv.md).
PRESETS = {
    "rag": dict(head="GenAI, LLM Systems, RAG & Hybrid Retrieval, LLM Evaluation, Python/FastAPI",
                sent="Deep in retrieval (hybrid BM25, dense and sparse search, reranking, FAISS) and evaluation rigor.",
                inv='"RAG-grounded judge", "multi-provider LLM routing", "hybrid LLM-as-judge", "end-to-end traceability"', af='"agentic RAG", "Webex", "Ollama"',
                order='"LLM Systems & AI Agents", "RAG & Knowledge Engineering", "LLM Evaluation & QA", "Models, Backend & Cloud", "LLMOps, Observability & Safety", "Voice & Conversational AI"'),
    "agents": dict(head="Agentic AI, LLM Systems in Production, RAG, LLM Evaluation",
                   sent="Experienced in taking agentic AI and LLM applications into production with real users and working directly with business stakeholders on requirements and trade-offs.",
                   inv='"multi-provider LLM routing", "RAG-grounded judge", "hybrid LLM-as-judge", "LLM guardrails"', af='"agentic RAG", "Webex", "JIRA-to-ServiceNow"',
                   order='"LLM Systems & AI Agents", "Models, Backend & Cloud", "RAG & Knowledge Engineering", "LLM Evaluation & QA", "LLMOps, Observability & Safety", "Voice & Conversational AI"'),
    "nlp_speech": dict(head="AI Agents, Conversational AI, NLP, Real-Time Voice Pipelines",
                       sent="Focused on AI agents and real-time conversational systems, from speech and NLP pipelines to API integrations in production.",
                       inv='"GPU speech pipeline", "multi-provider LLM routing", "multimodal enrichment", "2-speaker diarization"', af='"agentic RAG", "Webex", "intent classification"',
                       order='"Voice & Conversational AI", "LLM Systems & AI Agents", "Models, Backend & Cloud", "RAG & Knowledge Engineering", "LLM Evaluation & QA", "LLMOps, Observability & Safety"'),
    "eval": dict(head="LLM Engineer, LLM Evaluation, Multi-Agent Systems, Model Benchmarking",
                 sent="Benchmarks models on quality, latency and cost with A/B baselines before promotion.",
                 inv='"multi-provider LLM routing", "Benchmarked 5+", "hybrid LLM-as-judge", "RAG-grounded judge"', af='"Webex", "agentic RAG", "Ollama"',
                 order='"LLM Systems & AI Agents", "LLM Evaluation & QA", "RAG & Knowledge Engineering", "Models, Backend & Cloud", "LLMOps, Observability & Safety", "Voice & Conversational AI"'),
    "ml": dict(head="Machine Learning Engineer, LLM & NLP Pipelines, RAG, MLOps",
               sent="Experienced in LLM and NLP pipelines with RAG over technical documents and reproducible MLflow-tracked deployment.",
               inv='"RAG-grounded judge", "hybrid LLM-as-judge", "Benchmarked 5+", "multi-provider LLM routing"', af='"agentic RAG", "Ollama", "Webex"',
               order='"LLM Systems & AI Agents", "RAG & Knowledge Engineering", "Models, Backend & Cloud", "LLMOps, Observability & Safety", "LLM Evaluation & QA", "Voice & Conversational AI"'),
}
PRESET_FOR = {"rag": "rag", "agents": "agents", "nlp_speech": "nlp_speech", "eval": "eval", "ml": "ml", "mlops": "ml"}

norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
text = lambda h: html.unescape(re.sub(r"\s+", " ", re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", h)).replace("\n ", "\n"))


def get(url, tries=3):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code not in (429, 999) or i == tries - 1:
                raise
            time.sleep(30 * (i + 1))  # LinkedIn rate limit


def search():
    """Jobs posted in the last 24h: {id: dict(title, company, location, posted, market)}."""
    found = {}
    for loc, market in LOCATIONS.items():
        for kw in KEYWORDS:
            q = urllib.parse.urlencode(dict(keywords=kw, location=loc, f_TPR="r86400", start=0))
            try:
                page = get(LI + "seeMoreJobPostings/search?" + q)
            except Exception as e:
                print(f"search error {kw}/{loc}: {e}", file=sys.stderr); continue
            for card in page.split("<li>")[1:]:
                m = re.search(r"jobPosting:(\d+)", card)
                if not m:
                    continue
                g = lambda c: html.unescape(re.sub(r"<[^>]+>", "", (re.search(c + r'[^>]*>(.*?)</', card, re.S) or [None, ""])[1]).strip())
                loc_txt = g("job-search-card__location")
                found.setdefault(m[1], dict(title=g("base-search-card__title"), company=g("hidden-nested-link"), location=loc_txt,
                                            posted=(re.search(r'datetime="([^"]+)"', card) or [None, ""])[1],
                                            market="REM" if re.search(r"remote", loc_txt, re.I) else market))
            time.sleep(2)
    return found


def fetch_jd(jid):
    page = get(LI + f"jobPosting/{jid}")
    m = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', page, re.S)
    crit = " | ".join(html.unescape(x.strip()) for x in re.findall(r'description__job-criteria-text[^>]*>(.*?)</span>', page, re.S))
    remote = bool(re.search(r"\bremote\b", page[:20000], re.I))
    return (text(m[1]).strip() if m else ""), crit, remote


def score(jd):
    """(fit 1-5, skip reason or None, top group, matched groups, unclaimed must-haves)."""
    for pat, why in HARD_SKIP:
        for m in re.finditer(pat, jd, re.I):
            line = jd[jd.rfind("\n", 0, m.start()) + 1:jd.find("\n", m.end()) % (len(jd) + 1)]
            if not re.search(r"\bplus\b|prefer|advantage|nice to have|bonus|desirable", line, re.I):
                return 0, why, None, [], []
    yrs = [int(a) for a in re.findall(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?years", jd, re.I) if int(a) < 30]
    if yrs and min(yrs) >= 8:
        return 0, f"{min(yrs)}+ yrs", None, [], []
    counts = {g: len(re.findall(p, jd, re.I)) for g, p in GROUPS.items()}
    hits = [g for g, c in counts.items() if c]
    gaps = sorted({m[0].lower() for m in re.finditer(UNCLAIMED, jd, re.I)})
    fit = max(1.0, min(5.0, 1 + 0.5 * len(hits) - 0.75 * len(gaps)))
    top = max((g for g in PRESET_FOR if counts.get(g)), key=lambda g: counts[g], default="rag")
    return round(fit, 1), None, PRESET_FOR[top], hits, gaps


def tracked():
    rows = list(csv.DictReader(open(TRACKER, encoding="utf-8")))
    return rows, {norm(r["Company"]) + "|" + norm(r["Job Title"]) for r in rows}, " ".join(r["Job Link"] for r in rows)


def build_cv(slug, preset, jd_txt, url, title, company, loc):
    """Write payload builder from the template, render HTML/ATS/PDF; return (pdf, ats, payload, ok, log)."""
    p = PRESETS[preset]
    cv = open(os.path.join(CO, "cv.md"), encoding="utf-8").read()
    phone, email = re.search(r"^(\+[\d ]+) \| (\S+@\S+)", cv, re.M).groups()  # contact line of cv.md, never committed
    open(f"{CO}/jds/{slug}.md", "w").write(f"URL: {url}\n\n# {title} - {company}\nLocation: {loc}\n\n{jd_txt}")
    s = open(os.path.join(HERE, "build_payload_example.py")).read()
    for a, b in [('"<phone>"', json.dumps(phone)), ('"<email>"', json.dumps(email)),
                 ('"Applied AI Engineer | GenAI, LLM Systems, RAG & Hybrid Retrieval, LLM Evaluation, Python/FastAPI"', json.dumps("Applied AI Engineer | " + p["head"])),
                 ('first(inv, "hybrid LLM-as-judge", "RAG-grounded judge", "multi-provider LLM routing", "end-to-end traceability", "LLM guardrails", "41-entry")', f"first(inv, {p['inv']})"),
                 ('first(af, "agentic RAG", "Webex", "Ollama")', f"first(af, {p['af']})"),
                 ('" Deep in retrieval (hybrid BM25, dense and sparse search, reranking, FAISS) and evaluation rigor. Also designed"', json.dumps(" " + p["sent"] + " Also designed")),
                 ('''["LLM Systems & AI Agents", "RAG & Knowledge Engineering", "LLM Evaluation & QA", "LLMOps, Observability & Safety",
         "Models, Backend & Cloud", "Voice & Conversational AI"]''', f"[{p['order']}]")]:
        assert a in s, a
        s = s.replace(a, b)
    py = f"{CO}/jds/build_payload_{slug}.py"
    open(py, "w").write(s)
    o = f"{CO}/output"
    sh = (f'cd {CO} && python3 {py} cv.md {o}/payload-{slug}.json'
          f' && node build-cv-html.mjs {o}/payload-{slug}.json {o}/cv-{slug}.html templates/cv-template.compact.html'
          f' && node build-cv-html.mjs {o}/payload-{slug}.json {o}/cv-{slug}-ats.html "$(node cv-templates.mjs resolve cv ats)"'
          f' && node generate-pdf.mjs {o}/cv-{slug}.html {o}/cv-{slug}.pdf --format=a4')
    r = subprocess.run(sh, shell=True, capture_output=True, text=True)
    log = r.stdout + r.stderr
    pages = re.search(r"Pages?:\s*(\d+)", log)
    ok = r.returncode == 0 and "Fact check passed" in log and (pages is None or pages[1] == "2")
    return f"{o}/cv-{slug}.pdf", f"{o}/cv-{slug}-ats.html", f"{o}/payload-{slug}.json", ok, log


def add_row(job, fit, gaps, cover):
    rows, _, _ = tracked()
    cols = list(rows[0].keys())
    shutil.copy2(TRACKER, TRACKER.replace(".csv", f"_backup_{datetime.date.today()}_daily.csv"))
    nums = [int(r["#"]) for r in rows if r["#"].isdigit()]
    d = datetime.date.today()
    rows.append({c: "" for c in cols} | {
        "#": str(max(nums, default=0) + 1), "Market": job["market"], "Job Title": job["title"], "Company": job["company"],
        "Location / Eligibility": job["location"], "Work Mode": "Remote" if job["market"] == "REM" else "",
        "Posted": job["posted"], "Source": f"Daily pipeline {d.day:02d} {d:%b} (LinkedIn)", "Job Link": job["url"],
        "Status": "Not applied",
        "Notes": f"Auto fit {fit}/5 from full JD." + (" Cover letter requested: write one before applying." if cover else "")
                 + (f" Gaps: {', '.join(gaps)}." if gaps else "")})
    with open(TRACKER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--max", type=int, default=MAX_NEW)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    os.makedirs(STATE, exist_ok=True)
    seen_path = os.path.join(STATE, "seen.json")
    seen = json.load(open(seen_path)) if os.path.exists(seen_path) else {}
    _, keys, links = tracked()
    jobs = search()
    made, skipped = [], 0
    for jid, j in jobs.items():
        if len(made) >= a.max:
            break
        key = norm(j["company"]) + "|" + norm(j["title"])
        if jid in seen or jid in links or key in keys or not TITLE_OK.search(j["title"]) or TITLE_SKIP.search(j["title"]):
            continue
        try:
            jd, crit, remote = fetch_jd(jid)
        except Exception as e:
            print(f"jd error {jid}: {e}", file=sys.stderr); continue
        time.sleep(2)
        if len(jd) < 300:
            continue  # unreadable JD, retry next run
        fit, why, preset, hits, gaps = score(jd + "\n" + crit)
        j["url"] = f"https://www.linkedin.com/jobs/view/{jid}"
        seen[jid] = dict(title=j["title"], company=j["company"], fit=fit, skip=why, date=str(datetime.date.today()))
        keys.add(key)
        if why or fit < 3:
            skipped += 1; continue
        if a.dry_run:
            made.append(f"[dry] {fit} {preset} {j['title']} @ {j['company']} ({j['market']}) {j['url']} gaps={gaps}"); continue
        slug = re.sub(r"[^a-z0-9]+", "-", f"{j['company']}-{j['title']}".lower()).strip("-")[:60]
        pdf, ats, payload, ok, log = build_cv(slug, preset, jd, j["url"], j["title"], j["company"], j["location"])
        if not ok:
            seen[jid]["skip"] = "render failed"
            print(f"render failed {slug}:\n{log[-800:]}", file=sys.stderr); continue
        cover = bool(COVER.search(jd))
        add_row(j, fit, gaps, cover)
        r = subprocess.run([sys.executable, os.path.join(APPS, "export_application.py"), "--payload", payload, "--pdf", pdf,
                            "--ats-html", ats, "--company", j["company"], "--role", j["title"], "--market", j["market"],
                            "--keywords", ", ".join(hits), "--gaps", ", ".join(gaps)], capture_output=True, text=True, cwd=APPS)
        folder = (re.search(r"-> (.+)", r.stdout) or [None, "export failed: " + r.stderr[-200:]])[1]
        made.append(f"{len(made) + 1}. {j['title']} @ {j['company']} ({j['market']}, fit {fit})"
                    + (" [cover letter requested]" if cover else "") + f"\n   {folder}\n   {j['url']}")
    if not a.dry_run:
        json.dump(seen, open(seen_path, "w"), indent=1)
    d = datetime.date.today()
    head = f"Daily AI jobs {d.day:02d} {d:%b}: {len(made)} new folder(s) ready, {skipped} skipped, {len(jobs)} postings scanned."
    print(head + ("\n\n" + "\n".join(made) if made else "\nNo new jobs with fit >= 3 today.")
          + ("\n\nReview each CV, then apply yourself. Nothing was submitted." if made else ""))


def selftest():
    good = "We build LLM agents with RAG and evaluation in Python/FastAPI on AWS, deploy to production with MLflow, NLP chatbots. 3+ years."
    fit, why, preset, hits, gaps = score(good)
    assert why is None and fit >= 3 and not gaps, (fit, why, gaps)
    assert score("Fluent Arabic is required. LLM RAG Python")[1] == "Arabic required"
    assert score("Requires 10+ years of experience with LLMs")[1] == "10+ yrs"
    assert score(good + " Must know TypeScript, React and Kubernetes and Terraform.")[0] < 3
    assert score("Summer internship in AI")[1] == "Internship"
    assert TITLE_SKIP.search("AI Intern") and not TITLE_SKIP.search("AI Engineer") and TITLE_OK.search("Senior LLM Engineer")
    print("selftest ok")


if __name__ == "__main__":
    main()
