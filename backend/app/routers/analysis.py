"""Resume analysis and history endpoints."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Analysis
from app.schemas import AnalysisResponse, AnalysisResult, HistoryItem
from app.services import llm, parser

router = APIRouter(prefix="/api", tags=["analysis"])

MIN_JD_LENGTH = 50


def _to_response(row: Analysis) -> AnalysisResponse:
    return AnalysisResponse(
        id=row.id,
        filename=row.filename,
        job_title=row.job_title,
        created_at=row.created_at,
        result=AnalysisResult.model_validate_json(row.result_json),
    )


@router.post("/analyze", response_model=AnalysisResponse, summary="Analyze a resume against a job description")
def analyze(
    resume: UploadFile = File(..., description="Resume file (PDF, DOCX or TXT)"),
    job_description: str = Form(..., description="Full job description text"),
    job_title: str = Form("", description="Optional target role"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    settings = get_settings()
    filename = resume.filename or "resume"

    job_description = job_description.strip()
    if len(job_description) < MIN_JD_LENGTH:
        raise HTTPException(422, f"The job description must be at least {MIN_JD_LENGTH} characters long.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = resume.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"The file is too large. Maximum size is {settings.max_upload_mb} MB.")

    try:
        resume_text = parser.extract_text(filename, data)
    except parser.ParseError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        result = llm.analyze_resume(
            resume_text[: settings.max_text_chars], job_description[: settings.max_text_chars]
        )
    except llm.LLMError as exc:
        raise HTTPException(502, str(exc)) from exc

    row = Analysis(
        filename=filename[:255],
        job_title=job_title.strip()[:255],
        match_score=result.match_score,
        result_json=result.model_dump_json(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.get("/history", response_model=list[HistoryItem], summary="List previous analyses")
def history(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = select(Analysis).order_by(Analysis.created_at.desc(), Analysis.id.desc()).limit(limit)
    return db.scalars(stmt).all()


@router.get("/history/{analysis_id}", response_model=AnalysisResponse, summary="Get one analysis")
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    row = db.get(Analysis, analysis_id)
    if row is None:
        raise HTTPException(404, "Analysis not found.")
    return _to_response(row)


@router.delete("/history/{analysis_id}", status_code=204, summary="Delete an analysis")
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)) -> None:
    row = db.get(Analysis, analysis_id)
    if row is None:
        raise HTTPException(404, "Analysis not found.")
    db.delete(row)
    db.commit()
