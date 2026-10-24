# Build career-ops CV payload for SOUM from cv.md: every job and every bullet kept, reordered for the JD.
import json, re, sys

cv = open(sys.argv[1]).read()
exp = cv.split("## Experience")[1].split("## Education")[0]
jobs = []
for block in re.split(r"\n(?=### )", exp.strip()):
    if not block.startswith("### "):
        continue
    lines = [l for l in block.splitlines() if l.strip()]
    company, loc = lines[0][4:].split(" — ", 1)
    role, dates = lines[1].strip("*"), lines[2]
    bullets = [l[2:].strip() for l in lines[3:] if l.startswith("* ")]
    context = next((l.strip("*") for l in lines[3:] if l.startswith("*") and not l.startswith("* ")), None)
    jobs.append({"company": company, "role": role, "location": loc, "dates": dates, "bullets": bullets, **({"context": context} if context else {})})

n_src = sum(len(j["bullets"]) for j in jobs)

def first(job, *keys):
    """Move bullets containing any key to the front, in key order."""
    b = job["bullets"]
    picked = [x for k in keys for x in b if k in x]
    picked = list(dict.fromkeys(picked))
    job["bullets"] = picked + [x for x in b if x not in picked]

inv, dy, af, hm = jobs
first(inv, "hybrid LLM-as-judge", "RAG-grounded judge", "multi-provider LLM routing", "end-to-end traceability", "LLM guardrails", "41-entry")
first(af, "agentic RAG", "Webex", "Ollama")
first(dy, "advanced RAG")

# honest keyword wording on existing claims only
inv["bullets"] = [b.replace("multi-provider LLM routing (", "multi-provider LLM routing with tool calling and structured outputs (", 1)
                  .replace("with A/B model baselines and structured evaluation", "with A/B testing against model baselines and structured evaluation", 1)
                  for b in inv["bullets"]]
af["bullets"] = [b.replace("agentic RAG (LangChain", "agentic RAG (Retrieval Augmented Generation; LangChain", 1) for b in af["bullets"]]

assert sum(len(j["bullets"]) for j in jobs) == n_src == 21, n_src

skills = {}
for l in cv.split("## Skills")[1].split("## Experience")[0].splitlines():
    m = re.match(r"\*\*(.+?):\*\* (.+)", l)
    if m:
        skills[m.group(1)] = m.group(2)
order = ["LLM Systems & AI Agents", "RAG & Knowledge Engineering", "LLM Evaluation & QA", "LLMOps, Observability & Safety",
         "Models, Backend & Cloud", "Voice & Conversational AI"]
skills_out = [{"category": k, "items": skills[k].replace("vLLM ;", "vLLM;").replace("cloudrun", "Google Cloud Run")} for k in order]

highlights = [l[2:].strip() for l in cv.split("## Career Highlights")[1].split("## Skills")[0].splitlines() if l.startswith("* ")]
extra = {m.group(1): m.group(2) for m in re.finditer(r"\*\*(Languages|References):\*\* (.+)", cv.split("## Additional Information")[1])}

payload = {
    "lang": "en", "page_format": "a4",
    "candidate": {"name": "Tayyaba Rizwan Malik Rizwan Ahmed", "title": "Applied AI Engineer | GenAI, LLM Systems, RAG & Hybrid Retrieval, LLM Evaluation, Python/FastAPI",
                  "phone": "<phone>", "email": "<email>",
                  "linkedin": {"url": "https://linkedin.com/in/tayyaba-rizwan-zenithraaix", "display": "linkedin.com/in/tayyaba-rizwan-zenithraaix"},
                  "github": {"url": "https://github.com/Tyba7", "display": "github.com/Tyba7"},
                  "location": "UAE (all Emirates) | UAE Resident, no sponsorship | On-site, hybrid, remote or contract"},
    "summary": cv.split("## Summary")[1].split("## ")[0].strip().replace(" Also designed", " Deep in retrieval (hybrid BM25, dense and sparse search, reranking, FAISS) and evaluation rigor. Also designed"),
    "sections": {"projects": "Career Highlights"},
    "projects": [{"name": n, "description": h} for n, h in zip(["Production speech pipeline", "LLM-as-judge QA", "Auditable, safe LLM scoring"], highlights)],
    "experience": jobs,
    "education": [{"title": "BS in Artificial Intelligence", "org": "Iqra University, Pakistan", "year": "", "description": "Gold Medallist, CGPA 3.89. Degree attested (UAE)"}],
    "skills": skills_out + [{"category": "Languages", "items": extra["Languages"]}, {"category": "References", "items": extra["References"]}],
}
json.dump(payload, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
print("jobs", len(jobs), "bullets", n_src)
