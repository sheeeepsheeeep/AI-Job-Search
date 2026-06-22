"""Job Search and Matching Router."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import CandidateProfile, JobListing, JobMatch, User
from agents.job_discovery import JobDiscoveryAgent
from agents.job_matching import JobMatchingAgent
from routers.auth import get_current_user

router = APIRouter(prefix="/jobs", tags=["Job Search & Matching"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class SearchFilters(BaseModel):
    remote: Optional[bool] = None
    experience_level: Optional[str] = None
    salary_min: Optional[int] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Job search query")
    location: Optional[str] = Field("", description="Location filter")
    filters: Optional[SearchFilters] = None


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: Optional[str] = None
    salary_range: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[List[Any]] = Field(default_factory=list)
    url: Optional[str] = None
    source: Optional[str] = None
    remote_status: Optional[str] = None
    industry: Optional[str] = None
    experience_level: Optional[str] = None
    date_found: Optional[datetime] = None

    class Config:
        from_attributes = True


class MatchRequest(BaseModel):
    candidate_id: int


class MatchResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    match_score: Optional[float] = None
    overall_score: Optional[float] = None
    matching_skills: Optional[List[Any]] = Field(default_factory=list)
    missing_skills: Optional[List[Any]] = Field(default_factory=list)
    recommendations: Optional[List[Any]] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    skill_match: Optional[float] = None
    experience_match: Optional[float] = None
    education_match: Optional[float] = None

    class Config:
        from_attributes = True


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/search", response_model=List[JobResponse])
async def search_jobs(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search for jobs using the AI Job Discovery Agent and save results."""

    filters_dict: dict[str, Any] | None = None
    if request.filters:
        filters_dict = request.filters.model_dump(exclude_none=True)

    try:
        agent = JobDiscoveryAgent()
        results = await agent.search_jobs(
            query=request.query,
            location=request.location or "",
            filters=filters_dict,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job search failed: {e}",
        )

    # Save discovered jobs to DB
    saved_jobs: list[JobListing] = []
    for job_data in results:
        # Check for duplicate by title + company
        stmt = select(JobListing).where(
            JobListing.title == job_data.get("title"),
            JobListing.company == job_data.get("company"),
        )
        dup_result = await db.execute(stmt)
        existing = dup_result.scalar_one_or_none()

        if existing:
            saved_jobs.append(existing)
            continue

        job = JobListing(
            title=job_data.get("title", "Untitled"),
            company=job_data.get("company", "Unknown"),
            location=job_data.get("location"),
            salary_range=job_data.get("salary_range"),
            description=job_data.get("description"),
            requirements=job_data.get("requirements", []),
            url=job_data.get("url"),
            source=job_data.get("source"),
            remote_status=job_data.get("remote_status"),
            industry=job_data.get("industry"),
            experience_level=job_data.get("experience_level"),
        )
        db.add(job)
        saved_jobs.append(job)

    await db.flush()
    for job in saved_jobs:
        await db.refresh(job)

    return saved_jobs


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all saved job listings."""
    stmt = (
        select(JobListing)
        .order_by(JobListing.date_found.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single job listing by ID."""
    stmt = select(JobListing).where(JobListing.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job listing with ID {job_id} not found.",
        )
    return job


@router.post("/{job_id}/match", response_model=MatchResponse)
async def match_job(
    job_id: int,
    body: Optional[MatchRequest] = None,
    profile_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Match a job listing against a candidate profile."""

    # Fetch job
    stmt = select(JobListing).where(JobListing.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job listing with ID {job_id} not found.",
        )

    # Determine candidate ID
    cid = None
    if body and body.candidate_id:
        cid = body.candidate_id
    elif profile_id:
        cid = profile_id

    # Fetch candidate
    if cid:
        stmt = select(CandidateProfile).where(
            (CandidateProfile.id == cid) & (CandidateProfile.user_id == current_user.id)
        )
        result = await db.execute(stmt)
        candidate = result.scalar_one_or_none()
    else:
        # Fallback to latest profile of this user
        stmt = (
            select(CandidateProfile)
            .where(CandidateProfile.user_id == current_user.id)
            .order_by(CandidateProfile.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidate profile found. Please upload a CV first.",
        )

    # Build dicts for the agent
    candidate_dict = {
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "skills": candidate.skills or [],
        "education": candidate.education or [],
        "certifications": candidate.certifications or [],
        "experience": candidate.experience or [],
        "experience_years": candidate.experience_years,
        "summary": candidate.summary,
    }
    job_dict = {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary_range": job.salary_range,
        "description": job.description,
        "requirements": job.requirements or [],
        "url": job.url,
        "source": job.source,
        "remote_status": job.remote_status,
        "industry": job.industry,
        "experience_level": job.experience_level,
    }

    # Run match analysis
    try:
        agent = JobMatchingAgent()
        match_result = await agent.calculate_match(
            candidate_profile=candidate_dict,
            job_listing=job_dict,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Match calculation failed: {e}",
        )

    # Save JobMatch to DB
    job_match = JobMatch(
        candidate_id=candidate.id,
        job_id=job.id,
        match_score=match_result.get("match_score"),
        matching_skills=match_result.get("matching_skills", []),
        missing_skills=match_result.get("missing_skills", []),
        recommendations=match_result.get("recommendations", []),
        user_id=current_user.id,
    )
    db.add(job_match)
    await db.flush()
    await db.refresh(job_match)

    # Calculate extra stats for frontend breakdown
    num_matching = len(job_match.matching_skills or [])
    num_missing = len(job_match.missing_skills or [])
    total_skills = num_matching + num_missing
    skill_match_val = 100.0 * num_matching / total_skills if total_skills > 0 else 100.0

    exp_meets = True
    if isinstance(match_result.get("experience_match"), dict):
        exp_meets = match_result["experience_match"].get("meets_requirement", True)
    exp_match_val = 100.0 if exp_meets else 50.0

    edu_meets = True
    if isinstance(match_result.get("education_match"), dict):
        edu_meets = match_result["education_match"].get("meets_requirement", True)
    edu_match_val = 100.0 if edu_meets else 50.0

    response_data = {
        "id": job_match.id,
        "candidate_id": job_match.candidate_id,
        "job_id": job_match.job_id,
        "match_score": job_match.match_score,
        "overall_score": job_match.match_score,
        "matching_skills": job_match.matching_skills,
        "missing_skills": job_match.missing_skills,
        "recommendations": job_match.recommendations,
        "created_at": job_match.created_at,
        "skill_match": skill_match_val,
        "experience_match": exp_match_val,
        "education_match": edu_match_val,
    }
    return response_data
