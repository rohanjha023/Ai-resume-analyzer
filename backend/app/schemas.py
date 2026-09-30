"""Pydantic request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _clamp(value) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


class SectionScores(BaseModel):
    skills: int = 0
    experience: int = 0
    education: int = 0
    keywords: int = 0

    @field_validator("*", mode="before")
    @classmethod
    def _clamp_scores(cls, v):
        return _clamp(v)


class AnalysisResult(BaseModel):
    match_score: int
    verdict: str = ""
    summary: str = ""
    section_scores: SectionScores = Field(default_factory=SectionScores)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    ats_keywords: list[str] = Field(default_factory=list)

    @field_validator("match_score", mode="before")
    @classmethod
    def _clamp_match(cls, v):
        return _clamp(v)


class AnalysisResponse(BaseModel):
    id: int
    filename: str
    job_title: str
    created_at: datetime
    result: AnalysisResult


class HistoryItem(BaseModel):
    id: int
    filename: str
    job_title: str
    match_score: int
    created_at: datetime
