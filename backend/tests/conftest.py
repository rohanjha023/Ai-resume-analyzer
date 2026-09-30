import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["GEMINI_API_KEY"] = "test-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.schemas import AnalysisResult  # noqa: E402
from app.services import llm  # noqa: E402

SAMPLE = AnalysisResult(
    match_score=82,
    verdict="Strong Match",
    summary="Solid Python and RAG background.",
    section_scores={"skills": 85, "experience": 70, "education": 90, "keywords": 80},
    matched_skills=["Python", "FastAPI"],
    missing_skills=["Docker"],
    strengths=["Relevant projects"],
    weaknesses=["No cloud experience"],
    suggestions=["Add Docker experience"],
    ats_keywords=["LangChain"],
)

RESUME = b"Jane Doe. Python developer with FastAPI, SQL and machine learning project experience. " * 3
JD = "We are hiring an AI engineer with Python, FastAPI, Docker and LangChain experience. " * 2


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(llm, "analyze_resume", lambda resume, jd: SAMPLE)
    with TestClient(app) as c:
        yield c
