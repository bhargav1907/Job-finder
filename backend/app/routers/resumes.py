from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlmodel import Session

from ..config import get_settings
from ..db import get_session
from ..models import Resume
from ..schemas import ResumeRead
from ..services.resume_text import SUPPORTED_SUFFIXES, EmptyResume, UnsupportedFormat
from ..services.resumes import create_resume

router = APIRouter()


@router.post("/resumes", response_model=ResumeRead)
def upload_resume(
    response: Response,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ResumeRead:
    settings = get_settings()
    filename = file.filename or "resume"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported resume format: {suffix or 'unknown'}",
        )

    data = file.file.read(settings.resume_max_bytes + 1)
    if len(data) > settings.resume_max_bytes:
        raise HTTPException(status_code=413, detail="Resume file is too large")
    if not data:
        raise HTTPException(status_code=422, detail="Resume file is empty")

    try:
        row, created = create_resume(session, filename, data)
    except UnsupportedFormat as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except EmptyResume as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    response.status_code = 201 if created else 200
    return ResumeRead.model_validate(row)


@router.get("/resumes/{resume_id}", response_model=ResumeRead)
def get_resume(
    resume_id: int,
    session: Session = Depends(get_session),
) -> ResumeRead:
    row = session.get(Resume, resume_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return ResumeRead.model_validate(row)
