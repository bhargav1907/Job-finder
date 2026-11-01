from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlmodel import Session, select

from ..db import get_session
from ..models import Job
from ..schemas import JobList, JobRead

router = APIRouter()


@router.get("/jobs", response_model=JobList)
def list_jobs(
    q: str | None = Query(None, description="Free text across title, company, description"),
    location: str | None = Query(None, description="Substring match, e.g. Bengaluru"),
    remote: bool | None = Query(None),
    seniority: str | None = Query(None, description="intern|junior|mid|senior|lead"),
    role_family: str | None = Query(None),
    salary_min: int | None = Query(None, ge=0, description="Annual, in the job's currency"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> JobList:
    stmt = select(Job)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Job.title.ilike(like), Job.company.ilike(like), Job.description.ilike(like))
        )
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location.strip()}%"))
    if remote is not None:
        stmt = stmt.where(Job.remote == remote)
    if seniority:
        stmt = stmt.where(Job.seniority == seniority)
    if role_family:
        stmt = stmt.where(Job.role_family == role_family)
    if salary_min:
        stmt = stmt.where(Job.salary_max >= salary_min)

    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(
        stmt.order_by(Job.posted_at.desc()).offset(offset).limit(limit)
    ).all()

    return JobList(
        items=[JobRead.model_validate(row) for row in rows],
        total=int(total),
        limit=limit,
        offset=offset,
    )
