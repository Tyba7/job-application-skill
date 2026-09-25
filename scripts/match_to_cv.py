#!/usr/bin/env python3
"""
match_to_cv.py — JD-to-CV Match Tool

Evaluates fit between a user's CV and a job description.
Reads the CV via python-docx, checks codebase evidence, builds a match matrix.

Usage:
  python match_to_cv.py \
    --cv /path/to/cv.docx \
    --jd-json /path/to/jd.json \
    --codebase /path/to/codebase \
    --output /path/to/match_result.json

Output JSON:
  {
    "fit_score": "HIGH (85%)",
    "match_details": [
      {"skill": "Python", "status": "EXACT", "evidence": "CV + codebase: src/audio/"},
      ...
    ],
    "gaps": [
      {"skill": "Azure", "note": "User has AWS/GCP only — MISSING"}
    ]
  }
"""

import argparse
import json
import os
import re
import subprocess
from docx import Document
from pathlib import Path


def read_cv_text(cv_path):
    """Extract all text from a .docx CV."""
    doc = Document(cv_path)
    return " ".join(p.text for p in doc.paragraphs)


def check_codebase_evidence(codebase_root, skill_keywords):
    """
    Search the codebase for evidence of claimed skills.
    Returns dict: skill -> (found: bool, location: str)
    """
    if not codebase_root or not os.path.isdir(codebase_root):
        return {k: (False, "no codebase") for k in skill_keywords}

    results = {}
    for skill in skill_keywords:
        found_files = []
        # Search for the skill name and common variants
        patterns = [skill.lower()]
        # Add common variant patterns
        if "pytorch" in skill.lower():
            patterns.append("torch")
        if "tensorflow" in skill.lower():
            patterns.append("tf.")
        if "aws" in skill.lower():
            patterns.append("boto")
        if "gcp" in skill.lower():
            patterns.append("google-cloud")
        if "azure" in skill.lower():
            patterns.append("azure")
        if "docker" in skill.lower():
            patterns.append("dockerfile")
        if "kubernetes" in skill.lower() or "k8s" in skill.lower():
            patterns.append("kubernetes")
            patterns.append("k8s")
            patterns.append("kubectl")

        for pattern in patterns:
            try:
                result = subprocess.run(
                    ["grep", "-rl", pattern, codebase_root],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0 and result.stdout.strip():
                    for f in result.stdout.strip().split("\n")[:5]:
                        rel = os.path.relpath(f, codebase_root)
                        found_files.append(rel)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        found = len(found_files) > 0
        location = "; ".join(found_files[:3]) if found_files else ""
        results[skill] = (found, location)

    return results


def compute_match(cv_text, jd, codebase_evidence, all_skills_override=None):
    """
    Build match matrix: each JD requirement -> EXACT / PARTIAL / MISSING
    with evidence location.
    """
    cv_lower = cv_text.lower()
    required_skills = jd.get("required_skills", [])
    if isinstance(required_skills, str):
        required_skills = [s.strip() for s in required_skills.split(",")]

    secondary_skills = jd.get("secondary_skills", [])
    if isinstance(secondary_skills, str):
        secondary_skills = [s.strip() for s in secondary_skills.split(",")]

    # Use merged skill list if provided (structured + text-extracted), else
    # build from jd fields only.
    if all_skills_override is not None and len(all_skills_override) > 0:
        all_skills = all_skills_override
    else:
        all_skills = required_skills + secondary_skills

    match_details = []
    gaps = []
    exact_count = 0
    partial_count = 0
    total_count = len(all_skills)

    for skill in all_skills:
        skill_lower = skill.lower()
        cv_has = skill_lower in cv_lower
        in_required = skill_lower in {s.lower() for s in required_skills}

        # Check codebase evidence
        cb_found, cb_location = codebase_evidence.get(skill, (False, ""))

        if cv_has and cb_found:
            status = "EXACT"
            evidence = f"CV + codebase: {cb_location}"
            exact_count += 1
        elif cv_has:
            status = "PARTIAL"
            evidence = "CV: present, codebase: not found"
            partial_count += 1
        elif cb_found:
            status = "PARTIAL"
            evidence = f"codebase: {cb_location}, CV: absent"
            partial_count += 1
        else:
            status = "MISSING"
            evidence = "absent from both CV and codebase"
            if in_required:
                gaps.append({
                    "skill": skill,
                    "note": "Not found in CV or codebase",
                    "required": True,
                })

        match_details.append({
            "skill": skill,
            "status": status,
            "evidence": evidence,
            "required": in_required,
        })

    fit_pct = round((exact_count + partial_count) / total_count * 100) if total_count > 0 else 0
    if fit_pct >= 80:
        fit_label = "HIGH"
    elif fit_pct >= 60:
        fit_label = "MEDIUM"
    else:
        fit_label = "LOW"

    fit_score = f"{fit_label} ({fit_pct}%)"

    return {
        "fit_score": fit_score,
        "fit_pct": fit_pct,
        "fit_label": fit_label,
        "match_details": match_details,
        "gaps": gaps,
        "total_skills": total_count,
        "exact_matches": exact_count,
        "partial_matches": partial_count,
    }


def _extract_skills_from_text(text: str) -> list[str]:
    """
    When required_skills is empty (extraction failure cascade), fall back to
    deriving skill keywords from the full_jd text. Returns a list of
    individual skills / technology names / keywords present in the JD prose.
    """
    if not text:
        return []
    text_lower = text.lower()
    terms: list[str] = []

    # Technology / framework name dictionary — ordered so longer multi-word
    # phrases are tried before their single-word substrings.
    tech_terms = [
        "Python", "PyTorch", "TensorFlow", "Keras", "JAX", "scikit-learn",
        "NumPy", "Pandas", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
        "Elasticsearch", "Kafka", "RabbitMQ", "Airflow", "Prefect", "Luigi",
        "Spark", "PySpark", "Databricks", "Delta Lake", "Delta Live Tables",
        "dbt", "Hive", "Presto", "Trino", "Snowflake", "BigQuery", "Redshift",
        "Azure", "AWS", "GCP", "Google Cloud", "OCI", "Oracle Cloud",
        "Docker", "Kubernetes", "K8s", "kubectl", "Helm", "Terraform",
        "CI/CD", "GitHub Actions", "GitLab CI", "Jenkins", "CircleCI",
        "MLOps", "ML Pipeline", "Feature Store", "Model Registry",
        "Transformer", "BERT", "GPT", "LLaMA", "Mistral", "Claude",
        "Gemini", "LLM", "Large Language Model", "RAG", "Retrieval",
        "Vector Database", "Vector DB", "FAISS", "Milvus", "Pinecone",
        "Qdrant", "Weaviate", "Chroma", "chromadb", "Embeddings",
        "LangChain", "LlamaIndex", "Haystack", "DSPy",
        "Hugging Face", "Transformers", "sentence-transformers",
        "OpenAI", "GPT-4", "GPT-3", "API", "REST", "gRPC", "GraphQL",
        "FastAPI", "Flask", "Django", "Node.js", "TypeScript", "JavaScript",
        "React", "Vue", "Angular", "Next.js", "Express", "Spring Boot",
        "Java", "Scala", "Go", "Rust", "C++", "C#", ".NET",
        "Linux", "Bash", "Shell", "Git", "Agile", "Scrum", "Kanban",
        "Machine Learning", "Deep Learning", "Neural Network", "CNN",
        "RNN", "Transformer", "Attention", "Self-attention",
        "Computer Vision", "NLP", "Natural Language Processing",
        "Speech", "ASR", "TTS", "STT", "Voice", "Audio",
        "VAD", "Voice Activity Detection", "Diarization", "Speaker",
        "Sentiment", "Classification", "Clustering", "Regression",
        "Time Series", "Forecasting", "Anomaly", "Recommendation",
        "Reinforcement Learning", "RL", "RLHF", "Fine-tuning",
        "SFT", "PEFT", "LoRA", "QLoRA", "Quantization", "Pruning",
        "Evaluation", "Benchmark", "A/B Testing", "Experimentation",
        "Prompt Engineering", "Prompt", "Chain-of-thought", "CoT",
        "Few-shot", "Zero-shot", "In-context", "Context window",
        "Agent", "Agents", "Agentic", "Workflow", "Orchestration",
        "Tool use", "Function calling", "MCP", "RAGAS", "Ragas",
        "Ragas", " faithfulness", "answer relevance", "context precision",
        "Hallucination", " hallucinations", "Groundedness",
        "Knowledge Graph", "Graph", "Neo4j", "Cypher", "SPARQL",
        "OCR", "Tesseract", "Document Understanding", "PDF", "PPTX",
        "Docx", "Excel", "Pandas", "OpenPyXL", "PyMuPDF", "fitz",
        "Tesseract", "OCR", "image", "image processing", "OpenCV",
        "Pillow", "PIL", "matplotlib", "plotly", "seaborn", "visualization",
        "Dashboard", "Streamlit", "Gradio", "Dash", "Tableau", "PowerBI",
        "Git", "GitHub", "GitLab", "Bitbucket", "PR", "Pull Request",
        "Code Review", "Testing", "pytest", "unittest", "JUnit",
        "Coverage", "CI", "CD", "Deployment", "Production", "Scale",
        "Latency", "Throughput", "Performance", "Optimization",
        "Monitoring", "Logging", "Tracing", "Observability",
        "Prometheus", "Grafana", "Datadog", "New Relic", "Sentry",
        "PII", "GDPR", "Compliance", "Security", "Auth", "OAuth",
        "JWT", "LDAP", "SSO", "SAML", "RBAC",
        "Contact Center", "Call Center", "CCaaS", "Crm", "Zendesk",
        "Salesforce", "ServiceNow", "Freshdesk", "Intercom",
        "Telephony", "CTI", "Amazon Connect", "Aircall", "Twilio",
        "WebRTC", "VoIP", "SIP", "IVR", "ACD", "Queue",
        "CSAT", "NPS", "CES", "FCR", "AHT", "Average Handle Time",
        "SLA", "SLA breach", "KPI", "Dashboard", "Reporting",
    ]

    seen = set()
    for term in tech_terms:
        if term.lower() in text_lower:
            if term not in seen:
                terms.append(term)
                seen.add(term)

    # Also capture any capitalized proper-noun-like chunks (model names,
    # product names, library names) that aren't already captured.
    # Pattern: 1-3 word sequences that start with uppercase in the JD.
    cap_chunks = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", text)
    # Stoplist: common English words, locations, platform UI text, job-board
    # chrome, and verbose general terms that are NOT specific tech skills.
    _STOP_CHUNKS = frozenset({
        # Locations / geo
        "abu dhabi", "dubai", "uae", "united arab", "emirates",
        "united states", "usa", "uk", "europe", "middle east",
        "north america", "south america", "asia", "africa",
        # Job board chrome / UI text
        "email", "share", "twitter", "linkedin", "apply", "posted",
        "click", "here", "more", "jobs", "career", "rate",
        "similar jobs", "engineer jobs", "popular jobs",
        "job applications", "resume review", "privacy policy",
        "service", "professionals", "venture round",
        # Common English words that look capitalized
        "this", "that", "with", "from", "about", "each", "both",
        "upon", "into", "over", "such", "than", "these", "those",
        "other", "some", "any", "many", "very", "also", "well",
        "back", "still", "even", "much", "yet", "already",
        "additionally", "furthermore", "however", "therefore",
        "meanwhile", "moreover", "nevertheless",
        # Performance / general engineering verbs
        "collaborate", "maintain", "requirements", "construct",
        "manufacturing", "retail", "construction",
        # Compensation / HR terms
        "compensation", "salary", "benefits", "bonus", "equity",
        "stock", "options", "visa", "sponsor", "relocation",
        # General job terms
        "engineer", "engineering", "developer", "development",
        "manager", "management", "senior", "junior", "lead",
        "director", "head", "chief", "officer", "vp", "cto",
        "remote", "hybrid", "onsite", "full-time", "part-time",
        "contract", "internship", "intern", "apprentice",
        # Short noise tokens
        "ax", "ay", "be", "by", "he", "if", "in", "is", "it",
        "me", "my", "no", "of", "on", "or", "so", "to", "up",
        "us", "we", "re", "ve", "ll", "d", "t", "s",
        # Already-captured tech terms (avoid double counting)
        "python", "sql", "aws", "azure", "gcp", "git", "api",
        "ci", "cd", "pr", "ner", "rl", "nlp", "llm", "rag",
        "mlops", "iot", "ar", "vr", "xr", "ml", "dl", "cv",
        "ocr", "nlu", "nlg", "nli", "pos", "cto", "vp",
    })
    # Process the actual cap_chunks (not the regex pattern string 'extent').
    # Fix: was `for chunk in extent:` which iterated over the regex pattern
    # character-by-character instead of the matched chunks.
    for chunk in cap_chunks:
        c_lower = chunk.lower()
        if c_lower in _STOP_CHUNKS:
            continue
        # ── Additional garbage filters (fixes "AbuDhabimlposted"-style noise) ──
        # 1. Drop chunks containing any digit (job-post IDs, dates, version numbers)
        if re.search(r"\d", chunk):
            continue
        # 2. Drop chunks shorter than 4 characters
        if len(chunk) < 4:
            continue
        # 3. Drop chunks that are single common English words (even if capitalized
        #    in a heading/sentence-start position).
        if len(chunk.split()) == 1 and c_lower in _STOP_CHUNKS:
            continue
        # 4. Drop chunks where any stoplist word appears as a substring
        #    (catches concatenated chrome like "AbuDhabimlposted" → "dubai"/"posted")
        if any(stop in c_lower for stop in _STOP_CHUNKS):
            continue
        # 5. Drop chunks that look like concatenated non-dictionary noise:
        #    a single token with no spaces AND no tech-adjacent signal.
        if len(chunk.split()) == 1 and not any(
            sub in c_lower for sub in (
                "ai", "ml", "llm", "rag", "nlp", "cv", "model", "engine",
                "cloud", "platform", "service", "studio", "api", "sdk",
                "lib", "lab", "board", "flow", "run", "data", "agent",
                "train", "infer", "speech", "text", "vision", "emit",
                "struct", "transform", "learn", "network", "deep",
                "vector", "embed", "token", "prompt", "chain",
            )
        ):
            continue

        # Keep: multi-word proper nouns OR single words with tech signal AND len>=4
        if chunk not in seen and len(chunk.split()) <= 2:
            terms.append(chunk)
            seen.add(chunk)

    # NLP related terms that appear as phrases
    nlp_phrases = [
        "Named Entity Recognition", "NER", "part-of-speech", "POS tagging",
        "token classification", "dependency parsing", "semantic search",
        "semantic similarity", "semantic segmentation", "object detection",
        "image classification", "image generation", "text generation",
        "question answering", "summarization", "translation", "transcription",
        "intent classification", "intent detection", "entity extraction",
        "text classification", "sentiment analysis", "emotion detection",
        "speaker diarization", "speech recognition", "speech-to-text",
        "text-to-speech", "voice conversion", "voice cloning",
    ]
    for phrase in nlp_phrases:
        if phrase.lower() in text_lower:
            if phrase not in seen:
                terms.append(phrase)
                seen.add(phrase)

    return terms


def main():
    parser = argparse.ArgumentParser(description="JD-to-CV Match Tool")
    parser.add_argument("--cv", required=True, help="Path to CV .docx")
    parser.add_argument("--jd-json", required=True, help="Path to JD JSON")
    parser.add_argument("--codebase", help="Path to codebase root (optional)")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    cv_text = read_cv_text(args.cv)

    with open(args.jd_json) as f:
        jd = json.load(f)

    # Extract skill keywords from JD
    skill_keywords = []
    for field in ["required_skills", "secondary_skills", "skills"]:
        val = jd.get(field, [])
        if isinstance(val, str):
            val = [s.strip() for s in val.split(",")]
        skill_keywords.extend(val)

    # Also add JD title keywords
    title = jd.get("title", "")
    if title:
        skill_keywords.append(title)

    # ── Skill extraction: always run text extraction on full_jd and merge
    # with structured required_skills / secondary_skills. The structured fields
    # Extract skills from the full_jd text as a fallback + enrichment source.
    # This catches skills mentioned in prose that the (often-empty) structured
    # required_skills / secondary_skills fields miss. The extraction runs
    # regardless of whether structured fields are populated — the merged list
    # gives the most complete skill set for matching against the CV.
    extracted_from_text = []
    if jd.get("full_jd"):
        skill_set = {s.lower() for s in skill_keywords}
        raw = _extract_skills_from_text(jd["full_jd"])
        extracted_from_text = [s for s in raw if s.lower() not in skill_set]
    skill_keywords.extend(extracted_from_text)

    # Deduplicate
    skill_keywords = list(dict.fromkeys(skill_keywords))

    codebase_evidence = check_codebase_evidence(args.codebase, skill_keywords)
    result = compute_match(cv_text, jd, codebase_evidence, all_skills_override=skill_keywords)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
