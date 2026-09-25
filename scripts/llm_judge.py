#!/usr/bin/env python3
"""
llm_judge.py — LLM-as-Judge Guardrail for JD-to-CV Fit

Reviews the regex/grep match matrix produced by match_to_cv.py using
Tayyaba's local free model (llama.cpp router, OpenAI-compatible endpoint,
port 18434) and returns a corrected verdict. This exists because pure
keyword matching over-counts: a skill mentioned once in a JD sidebar
("nice to have: Kubernetes") and once anywhere in the CV counts as a full
match even if the JD's actual core requirement is unrelated. The judge
reads the real JD prose and the real CV text and gives a holistic verdict,
same philosophy as Vestwell's llm_judge_v2.py (quote-grounded, refuses to
score without evidence).

No paid APIs. Local model only — if the endpoint isn't reachable, this
degrades to a NO_JUDGE result and the caller falls back to the regex score.

Usage (library):
    from llm_judge import judge_fit
    result = judge_fit(jd_dict, cv_text, regex_match_result)

Usage (CLI):
    python llm_judge.py --jd-json jd.json --cv cv.docx --match match_result.json \
        --output llm_judge_result.json
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error

LOCAL_LLM_BASE = os.environ.get("LOCAL_LLM_BASE", "http://127.0.0.1:18434/v1")
LOCAL_LLM_API_KEY = os.environ.get("LOCAL_LLM_API_KEY", "")
LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL", "Qwen3.6-35B-A3B-UD-Q4_K_M")
TIMEOUT_S = 240

JUDGE_SYSTEM_PROMPT = """You are a strict, honest technical recruiter evaluating whether a
candidate's CV genuinely supports a job description's requirements.

Rules:
- Judge ONLY what is in the CV text and JD text given to you. Never assume skills.
- A regex/keyword match matrix is provided as a hint — it over-counts. A skill mentioned
  once anywhere does not mean deep experience. Weigh depth and context, not just presence.
- Distinguish: REQUIRED-and-STRONG (CV shows real production depth), REQUIRED-and-WEAK
  (mentioned but shallow), REQUIRED-and-MISSING (absent), NICE-TO-HAVE variants of the same.
- Give a fit_pct (0-100) reflecting genuine readiness for THIS role, not keyword density.
- Give a fit_label: HIGH (>=75), MEDIUM (50-74), LOW (<50).
- List up to 5 real gaps a hiring manager would actually probe in an interview.
- List up to 5 genuine strengths worth leading the cover letter with.
- Output STRICT JSON only, no prose outside the JSON object, in this exact shape:
{"fit_pct": <int>, "fit_label": "HIGH|MEDIUM|LOW", "strengths": ["...","..."],
 "gaps": ["...","..."], "verdict_note": "<one sentence justification>"}
"""


def _call_local_llm(prompt: str, max_tokens: int = 700) -> str:
    """POST to the local llama.cpp OpenAI-compatible endpoint. Raises on failure.

    This is a reasoning model (Qwen3.6) that streams a <think>...</think>
    block before the final answer, exposed separately as reasoning_content.
    A tight max_tokens budget gets consumed entirely by the thinking block,
    leaving content empty — so we (a) request a large budget and (b) fall
    back to scanning reasoning_content for a trailing JSON object if content
    comes back empty (some quantizations dump the JSON inside <think> and
    never close it before hitting the token limit).
    """
    url = f"{LOCAL_LLM_BASE}/chat/completions"
    payload = {
        "model": LOCAL_LLM_MODEL,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if LOCAL_LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LOCAL_LLM_API_KEY}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    message = body["choices"][0]["message"]
    content = message.get("content") or ""
    if content.strip():
        return content
    # Fallback: some responses spend the whole token budget on
    # reasoning_content and never emit a separate content field. Scan the
    # reasoning trace for a JSON object as a last resort.
    return message.get("reasoning_content") or ""


def _extract_json(text: str) -> dict:
    """Pull the first {...} JSON object out of a possibly-noisy LLM response."""
    if not text:
        raise ValueError("empty LLM response")
    # Strip reasoning/thinking tags some local models emit
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object found in LLM response: {text[:300]}")
    return json.loads(match.group(0))


def judge_fit(jd: dict, cv_text: str, regex_match: dict, max_jd_chars: int = 6000, max_cv_chars: int = 6000) -> dict:
    """
    Ask the local LLM to review the JD, CV, and regex match matrix, and
    return a corrected verdict. On any failure (model unreachable, bad
    JSON, timeout), returns {"judge_available": False, "error": "..."} so
    the caller can fall back to the regex-only score without crashing.

    max_tokens is generous (2500) because this is a reasoning model that
    spends tokens on a <think> block before the JSON answer — a tight
    budget truncates before any real content is emitted.
    """
    full_jd = (jd.get("full_jd") or "").strip()
    if not full_jd:
        # Fall back to whatever structured fields exist
        full_jd = json.dumps({
            k: jd.get(k) for k in ("title", "company", "required_skills", "secondary_skills")
            if jd.get(k)
        })
    full_jd = full_jd[:max_jd_chars]
    cv_excerpt = cv_text[:max_cv_chars]

    match_summary = []
    for m in (regex_match.get("match_details") or [])[:40]:
        if isinstance(m, dict):
            match_summary.append(f"{m.get('skill')}: {m.get('status')} ({m.get('evidence','')[:80]})")

    prompt = f"""JOB DESCRIPTION ({jd.get('company','?')} — {jd.get('title','?')}):
{full_jd}

CANDIDATE CV TEXT:
{cv_excerpt}

REGEX KEYWORD-MATCH HINTS (over-counts — use only as a starting point):
{chr(10).join(match_summary) if match_summary else "(no structured matches available)"}

Regex-based fit score for reference (do not just copy it): {regex_match.get('fit_score', 'UNKNOWN')}

Evaluate genuine fit and return the JSON object as instructed."""

    try:
        raw = _call_local_llm(prompt, max_tokens=1200)
        parsed = _extract_json(raw)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        return {"judge_available": False, "error": f"local LLM unreachable: {e}"}
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        return {"judge_available": False, "error": f"bad LLM response: {e}"}

    fit_pct = parsed.get("fit_pct")
    try:
        fit_pct = int(fit_pct)
        fit_pct = max(0, min(100, fit_pct))
    except (TypeError, ValueError):
        return {"judge_available": False, "error": f"LLM returned non-numeric fit_pct: {fit_pct}"}

    if fit_pct >= 75:
        fit_label = "HIGH"
    elif fit_pct >= 50:
        fit_label = "MEDIUM"
    else:
        fit_label = "LOW"

    return {
        "judge_available": True,
        "fit_pct": fit_pct,
        "fit_label": fit_label,
        "fit_score": f"{fit_label} ({fit_pct}%)",
        "strengths": parsed.get("strengths", [])[:5],
        "gaps": parsed.get("gaps", [])[:5],
        "verdict_note": parsed.get("verdict_note", ""),
        "model": LOCAL_LLM_MODEL,
    }


def main():
    parser = argparse.ArgumentParser(description="LLM-as-Judge JD-to-CV fit review")
    parser.add_argument("--jd-json", required=True)
    parser.add_argument("--cv", required=True, help="Path to CV .docx")
    parser.add_argument("--match", required=True, help="Path to match_result.json from match_to_cv.py")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    from docx import Document
    doc = Document(args.cv)
    cv_text = " ".join(p.text for p in doc.paragraphs)

    with open(args.jd_json) as f:
        jd = json.load(f)
    with open(args.match) as f:
        regex_match = json.load(f)

    result = judge_fit(jd, cv_text, regex_match)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    if not result.get("judge_available"):
        sys.exit(2)  # non-fatal signal to caller: judge degraded, use regex fallback


if __name__ == "__main__":
    main()
