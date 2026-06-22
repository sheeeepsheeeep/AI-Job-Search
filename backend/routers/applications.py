"""Application Tracking Router – create, list, update, stats, and insights."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import Application, CandidateProfile, User
from agents.application_tracking import ApplicationTrackingAgent
from routers.auth import get_current_user

router = APIRouter(prefix="/applications", tags=["Application Tracking"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────


class CreateApplicationRequest(BaseModel):
    candidate_id: int
    job_id: int
    company_name: str
    job_title: str
    email_address: Optional[str] = None
    cover_letter_id: Optional[int] = None
    notes: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None


class InsightsRequest(BaseModel):
    candidate_id: int


class ApplicationResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    cover_letter_id: Optional[int] = None
    company_name: str
    job_title: str
    email_address: Optional[str] = None
    date_sent: Optional[datetime] = None
    status: str = "Applied"
    follow_up_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Helper ────────────────────────────────────────────────────────────────────


def _application_to_dict(app: Application) -> dict:
    """Convert an Application ORM object to a plain dict for the agent."""
    return {
        "id": app.id,
        "candidate_id": app.candidate_id,
        "job_id": app.job_id,
        "cover_letter_id": app.cover_letter_id,
        "company_name": app.company_name,
        "company": app.company_name,
        "job_title": app.job_title,
        "email_address": app.email_address,
        "contact_email": app.email_address,
        "date_sent": str(app.date_sent) if app.date_sent else None,
        "applied_date": str(app.created_at) if app.created_at else None,
        "status": app.status,
        "follow_up_date": str(app.follow_up_date) if app.follow_up_date else None,
        "notes": app.notes,
        "created_at": str(app.created_at) if app.created_at else None,
        "updated_at": str(app.updated_at) if app.updated_at else None,
    }


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    body: CreateApplicationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new job application record."""
    application = Application(
        candidate_id=body.candidate_id,
        job_id=body.job_id,
        company_name=body.company_name,
        job_title=body.job_title,
        email_address=body.email_address,
        cover_letter_id=body.cover_letter_id,
        notes=body.notes,
        status="Applied",
        user_id=current_user.id,
    )
    db.add(application)
    await db.flush()
    await db.refresh(application)
    return application


@router.get("/stats")
async def get_application_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get application statistics using the AI tracking agent."""
    from sqlalchemy import func
    from database.models import JobListing

    result = await db.execute(
        select(Application)
        .where(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
    )
    applications = result.scalars().all()

    app_dicts = [_application_to_dict(app) for app in applications]

    agent = ApplicationTrackingAgent()
    try:
        stats = await agent.get_statistics(app_dicts)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute statistics: {str(e)}",
        )

    # Get total job listings count in the DB
    jobs_count_stmt = select(func.count(JobListing.id))
    jobs_count_result = await db.execute(jobs_count_stmt)
    total_jobs = jobs_count_result.scalar() or 0

    # Calculate average job match score from JobMatch table (user scoped)
    from database.models import JobMatch
    match_score_stmt = select(func.avg(JobMatch.match_score)).where(JobMatch.user_id == current_user.id)
    match_score_result = await db.execute(match_score_stmt)
    avg_match_score = match_score_result.scalar()

    # Map keys to match what Dashboard.jsx expects
    stats["total_applications"] = stats.get("total", 0)
    stats["success_rate"] = avg_match_score
    stats["active_jobs_count"] = total_jobs

    return stats


@router.post("/insights")
async def generate_insights(
    body: InsightsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate AI-powered strategic insights for a candidate's applications."""

    # Fetch candidate profile (user scoped)
    result = await db.execute(
        select(CandidateProfile).where(
            (CandidateProfile.id == body.candidate_id) & (CandidateProfile.user_id == current_user.id)
        )
    )
    candidate = result.scalars().first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile with ID {body.candidate_id} not found or unauthorized.",
        )

    # Fetch candidate's applications (user scoped)
    result = await db.execute(
        select(Application)
        .where((Application.candidate_id == body.candidate_id) & (Application.user_id == current_user.id))
        .order_by(Application.created_at.desc())
    )
    applications = result.scalars().all()

    app_dicts = [_application_to_dict(app) for app in applications]

    profile_dict = {
        "id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "skills": candidate.skills,
        "education": candidate.education,
        "certifications": candidate.certifications,
        "experience": candidate.experience,
        "experience_years": candidate.experience_years,
        "summary": candidate.summary,
    }

    agent = ApplicationTrackingAgent()
    try:
        insights = await agent.generate_insights(app_dicts, profile_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate insights: {str(e)}",
        )

    return insights


@router.get("/", response_model=List[ApplicationResponse])
async def list_applications(
    status_filter: Optional[str] = None,
    candidate_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all applications, optionally filtered by status and/or candidate_id."""
    stmt = select(Application).where(Application.user_id == current_user.id)
    if status_filter is not None:
        stmt = stmt.where(Application.status == status_filter)
    if candidate_id is not None:
        stmt = stmt.where(Application.candidate_id == candidate_id)
    stmt = stmt.order_by(Application.created_at.desc())

    result = await db.execute(stmt)
    applications = result.scalars().all()
    return applications


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific application by ID."""
    result = await db.execute(
        select(Application).where(
            (Application.id == application_id) & (Application.user_id == current_user.id)
        )
    )
    application = result.scalars().first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found or unauthorized.",
        )
    return application


@router.put("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: int,
    body: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the status (and optionally notes) of an application."""
    result = await db.execute(
        select(Application).where(
            (Application.id == application_id) & (Application.user_id == current_user.id)
        )
    )
    application = result.scalars().first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found or unauthorized.",
        )

    application.status = body.status
    if body.notes is not None:
        application.notes = body.notes

    await db.flush()
    await db.refresh(application)
    return application
