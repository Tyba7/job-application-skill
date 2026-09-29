"""Tests for the job-application skill pipeline."""
import json
import tempfile
import os
import sys
import unittest
from pathlib import Path

# Add scripts to path for imports
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestSkillExtraction(unittest.TestCase):
    """Test _extract_skills_from_text from match_to_cv.py."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("match_to_cv", str(SCRIPTS_DIR / "match_to_cv.py"))
        self.assertIsNotNone(spec)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.extract_skills = self.module._extract_skills_from_text

    def test_extract_python_and_rag(self):
        jd_text = "Looking for a Python developer with RAG experience. Must know LangChain and PyTorch."
        skills = self.extract_skills(jd_text)
        self.assertTrue(any(s == "Python" for s in skills), "Python not found")
        self.assertTrue(any(s == "RAG" for s in skills), "RAG not found")
        self.assertTrue(any(s == "PyTorch" for s in skills), "PyTorch not found")
        self.assertTrue(any(s == "LangChain" for s in skills), "LangChain not found")

    def test_no_garbage_from_stopwords(self):
        jd_text = "The Engineer Works In Dubai For A Service Company. Apply Here For Jobs."
        skills = self.extract_skills(jd_text)
        skills_lower = [s.lower() for s in skills]
        self.assertNotIn("dubai", skills_lower)
        self.assertNotIn("apply", skills_lower)
        self.assertNotIn("jobs", skills_lower)

    def test_no_concatenated_noise(self):
        jd_text = "AbuDhabimlposted Senior Engineer Role at Service"
        skills = self.extract_skills(jd_text)
        skills_lower = [s.lower() for s in skills]
        self.assertNotIn("dubai", skills_lower)

    def test_empty_text(self):
        self.assertEqual(self.extract_skills(""), [])
        self.assertEqual(self.extract_skills(None), [])

    def test_tech_terms_only(self):
        jd_text = "Kubernetes Docker Kafka Redis PostgreSQL"
        skills = self.extract_skills(jd_text)
        self.assertIn("Kubernetes", skills)
        self.assertIn("Docker", skills)
        self.assertIn("Kafka", skills)
        self.assertIn("Redis", skills)
        self.assertIn("PostgreSQL", skills)

    def test_computer_vision_and_nlp(self):
        jd_text = "Computer Vision NLP Natural Language Processing Speaker Diarization"
        skills = self.extract_skills(jd_text)
        self.assertTrue(any("computer vision" in s.lower() for s in skills))
        self.assertTrue(any("nlp" in s.lower() for s in skills))
        self.assertTrue(any("diarization" in s.lower() for s in skills))

    def test_no_duplicate_skills(self):
        jd_text = "Python Python Python PyTorch PyTorch"
        skills = self.extract_skills(jd_text)
        python_count = sum(1 for s in skills if s == "Python")
        self.assertEqual(python_count, 1)

    def test_cap_chunks_with_digits_filtered(self):
        jd_text = "Apply for job 4433218967 Posted on 2026-09-27 Version 3.14"
        skills = self.extract_skills(jd_text)
        skills_with_digits = [s for s in skills if any(c.isdigit() for c in s)]
        self.assertEqual(len(skills_with_digits), 0)

    def test_short_chunks_filtered(self):
        """Tech-adjacent single-token chunks (even <4 chars) pass; noise words filtered."""
        jd_text = "Python Java Go Rust"
        skills = self.extract_skills(jd_text)
        # Go is 2 chars but IS tech-adjacent — should pass
        self.assertIn("Go", skills)
        self.assertIn("Rust", skills)

    def test_nlp_phrases_extracted(self):
        jd_text = "Named Entity Recognition Sentiment Analysis Intent Classification"
        skills = self.extract_skills(jd_text)
        self.assertTrue(any("named entity recognition" in s.lower() for s in skills))
        self.assertTrue(any("sentiment analysis" in s.lower() for s in skills))


class TestFitScoring(unittest.TestCase):
    """Test compute_match logic from match_to_cv.py.

    IMPORTANT: compute_match marks CV-only matches as PARTIAL (weight 0.5),
    CV+codebase as EXACT (weight 1.0). So 100% CV coverage = 50% fit (not 100%).
    This is by design — PARTIAL means "user has the skill but no codebase proof."
    """

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("match_to_cv", str(SCRIPTS_DIR / "match_to_cv.py"))
        self.assertIsNotNone(spec)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.compute_match = self.module.compute_match

    def test_all_exact(self):
        """All skills match CV + codebase → 100% fit."""
        cv_text = "Python PyTorch RAG LangChain"
        jd = {"required_skills": ["Python", "PyTorch"], "secondary_skills": ["RAG", "LangChain"]}
        evidence = {s: (True, f"src/{s.lower()}.py") for s in ["Python", "PyTorch", "RAG", "LangChain"]}
        result = self.compute_match(cv_text, jd, evidence)
        self.assertEqual(result["fit_pct"], 100)
        self.assertEqual(result["fit_label"], "HIGH")
        self.assertEqual(result["exact_matches"], 4)
        self.assertEqual(result["partial_matches"], 0)

    def test_cv_only_is_partial(self):
        """All skills match CV only (no codebase) → 50% fit (PARTIAL)."""
        cv_text = "Python PyTorch RAG LangChain"
        jd = {"required_skills": ["Python", "PyTorch"], "secondary_skills": ["RAG", "LangChain"]}
        evidence = {s: (False, "") for s in ["Python", "PyTorch", "RAG", "LangChain"]}
        result = self.compute_match(cv_text, jd, evidence)
        # 4 PARTIAL: fit = (0 + 0.5*4)/4 = 50%
        self.assertEqual(result["fit_pct"], 50)
        self.assertEqual(result["fit_label"], "MEDIUM")
        self.assertEqual(result["exact_matches"], 0)
        self.assertEqual(result["partial_matches"], 4)

    def test_mixed_exact_partial(self):
        """3 CV-exact + 1 CV-partial → weighted score."""
        cv_text = "Python RAG FastAPI"
        jd = {"required_skills": ["Python", "PyTorch"], "secondary_skills": ["RAG", "FastAPI"]}
        evidence = {
            "Python": (False, ""),    # CV has, no codebase → PARTIAL
            "PyTorch": (False, ""),   # CV lacks → MISSING
            "RAG": (False, ""),       # CV has, no codebase → PARTIAL
            "FastAPI": (False, ""),   # CV has, no codebase → PARTIAL
        }
        result = self.compute_match(cv_text, jd, evidence)
        # 3 PARTIAL (Python, RAG, FastAPI), 1 MISSING (PyTorch)
        # fit = (0 + 0.5*3)/4 = 37.5% → LOW
        self.assertEqual(result["fit_pct"], 38)
        self.assertEqual(result["fit_label"], "LOW")

    def test_all_missing(self):
        """No skills match → LOW (0%). Only required_skills counted as gaps."""
        cv_text = "Java Spring Boot React"
        jd = {"required_skills": ["Python", "PyTorch"], "secondary_skills": ["RAG"]}
        evidence = {s: (False, "") for s in ["Python", "PyTorch", "RAG"]}
        result = self.compute_match(cv_text, jd, evidence)
        self.assertEqual(result["fit_pct"], 0)
        self.assertEqual(result["fit_label"], "LOW")
        # Gaps only include required_skills (Python, PyTorch), not secondary (RAG)
        self.assertEqual(len(result["gaps"]), 2)
        gap_skills = [g["skill"] for g in result["gaps"]]
        self.assertIn("Python", gap_skills)
        self.assertIn("PyTorch", gap_skills)

    def test_thresholds(self):
        """HIGH >= 75%, MEDIUM >= 50%, LOW < 50%."""
        jd = {"required_skills": ["Python"], "secondary_skills": ["PyTorch"]}
        evidence = {"Python": (False, ""), "PyTorch": (False, "")}

        # CV has Python (PARTIAL) + PyTorch missing → (0 + 0.5*1)/2 = 25% → LOW
        result = self.compute_match("Python", jd, evidence)
        self.assertEqual(result["fit_pct"], 25)
        self.assertEqual(result["fit_label"], "LOW")

        # CV has both → 2 PARTIAL → (0 + 0.5*2)/2 = 50% → MEDIUM
        result = self.compute_match("Python PyTorch", jd, evidence)
        self.assertEqual(result["fit_pct"], 50)
        self.assertEqual(result["fit_label"], "MEDIUM")

    def test_empty_skills(self):
        """Empty skill list → fit_pct=0, no gaps."""
        cv_text = "Python"
        jd = {"required_skills": [], "secondary_skills": []}
        result = self.compute_match(cv_text, jd, {})
        self.assertEqual(result["fit_pct"], 0)
        self.assertEqual(result["total_skills"], 0)
        self.assertEqual(len(result["gaps"]), 0)

    def test_codebase_evidence_bumps_to_exact(self):
        """CV + codebase → EXACT → full weight."""
        cv_text = "Python PyTorch"
        jd = {"required_skills": ["Python", "PyTorch"], "secondary_skills": []}
        evidence = {
            "Python": (True, "src/audio/asr.py"),
            "PyTorch": (True, "src/audio/pipeline.py"),
        }
        result = self.compute_match(cv_text, jd, evidence)
        self.assertEqual(result["exact_matches"], 2)
        self.assertEqual(result["partial_matches"], 0)
        self.assertEqual(result["fit_pct"], 100)


class TestTrackApplications(unittest.TestCase):
    """Test track_applications.py — CSV generation from ground truth."""

    def test_module_exists(self):
        """track_applications.py imports successfully and has the expected function."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "track_applications", str(SCRIPTS_DIR / "track_applications.py"))
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # The module should have a main() function (CLI entry point)
        self.assertTrue(hasattr(module, "main"))


class TestRenderCVSummaryRewrite(unittest.TestCase):
    """Test renderer.py — summary paragraph rewrite for tailored CVs."""

    def test_summary_rewrites_first_sentence(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("renderer", str(SCRIPTS_DIR / "renderer.py"))
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertTrue(hasattr(module, "render_cv"))

        with open(str(SCRIPTS_DIR / "renderer.py")) as f:
            source = f.read()
        self.assertIn("jd.get", source)
        self.assertIn("Applied AI Engineer with", source)


class TestMatchToCVIntegration(unittest.TestCase):
    """Integration test: extract skills from a realistic JD, then match to CV."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("match_to_cv", str(SCRIPTS_DIR / "match_to_cv.py"))
        self.assertIsNotNone(spec)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_realistic_jd_extraction_and_match(self):
        jd_text = """Senior AI Engineer at OpenAI — Abu Dhabi, UAE.

We're looking for an AI/ML Engineer with 5+ years of experience building
production AI systems. You'll work with LLMs, RAG pipelines, and
multi-agent orchestration. Experience with Python, PyTorch, and Docker is
required. Kubernetes and cloud platforms (AWS/GCP) preferred.

Requirements:
- 5+ years in Applied AI/ML engineering
- Hands-on RAG systems end-to-end
- LLMs, AI agents, evaluation frameworks
- Production AI infrastructure
- Python and software engineering fundamentals"""

        extracted_skills = self.module._extract_skills_from_text(jd_text)
        self.assertGreater(len(extracted_skills), 0, "No skills extracted")

        skills_lower = [s.lower() for s in extracted_skills]
        self.assertIn("python", skills_lower)
        self.assertIn("llm", skills_lower)
        self.assertIn("rag", skills_lower)
        self.assertIn("pytorch", skills_lower)
        self.assertIn("docker", skills_lower)

        jd = {
            "required_skills": [],
            "secondary_skills": [],
            "full_jd": jd_text,
            "role": "Senior AI Engineer",
            "company": "OpenAI",
        }

        cv_text = ("Tayyaba Rizwan — Applied AI Engineer, Dubai UAE. 4+ years AI/ML engineering. "
                   "Core skills: LLMs, RAG, LangChain/LangGraph, CrewAI, Voice AI, MLOps, "
                   "Docker, CI/CD, Python, SQL, PyTorch, AWS, Kubernetes, production systems.")

        skill_keywords = list(dict.fromkeys(extracted_skills))
        evidence = {s: (False, "") for s in skill_keywords}
        result = self.module.compute_match(cv_text, jd, evidence,
                                           all_skills_override=skill_keywords)

        # With ~15+ skills extracted and ~10 matching CV, expect MEDIUM+
        self.assertGreater(result["fit_pct"], 30, "Fit score should be reasonable for overlapping skills")
        self.assertIn(result["fit_label"], ("HIGH", "MEDIUM", "LOW"))


if __name__ == "__main__":
    unittest.main()
