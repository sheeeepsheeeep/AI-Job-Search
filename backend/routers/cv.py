"""CV Upload and Profile Management Router."""

import os
import uuid
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import CandidateProfile
from services.cv_parser import extract_cv_text
from agents.cv_analysis import CVAnalysisAgent

router = APIRouter(prefix="/cv", tags=["CV & Profile"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class ProfileResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: Optional[List[Any]] = Field(default_factory=list)
    education: Optional[List[Any]] = Field(default_factory=list)
    certifications: Optional[List[Any]] = Field(default_factory=list)
    experience: Optional[List[Any]] = Field(default_factory=list)
    experience_years: Optional[int] = None
    summary: Optional[str] = None
    cv_file_path: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CV file (PDF/DOCX), parse, analyse with AI, and save profile."""

    # Validate file type
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, DOCX",
        )

    # Save uploaded file
    file_ext = os.path.splitext(file.filename or "cv")[1] or ".pdf"
    saved_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)

    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {e}",
        )

    # Extract text from CV
    try:
        cv_text = extract_cv_text(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract text from CV: {e}",
        )

    # Analyse with CV Analysis Agent
    try:
        agent = CVAnalysisAgent()
        analysis = await agent.analyze_cv(cv_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CV analysis failed: {e}",
        )

    # Save CandidateProfile to DB
    profile = CandidateProfile(
        name=analysis.get("name") or "Unknown",
        email=analysis.get("email"),
        phone=analysis.get("phone"),
        skills=analysis.get("skills", []),
        education=analysis.get("education", []),
        certifications=analysis.get("certifications", []),
        experience=analysis.get("experience", []),
        experience_years=analysis.get("experience_years"),
        summary=analysis.get("summary"),
        cv_file_path=file_path,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)

    return profile


@router.get("/profile", response_model=ProfileResponse)
async def get_latest_profile(db: AsyncSession = Depends(get_db)):
    """Get the most recently created candidate profile."""
    stmt = (
        select(CandidateProfile)
        .order_by(CandidateProfile.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidate profile found. Please upload a CV first.",
        )
    return profile


@router.get("/profile/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific candidate profile by ID."""
    stmt = select(CandidateProfile).where(CandidateProfile.id == profile_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID {profile_id} not found.",
        )
    return profile


@router.get("/recommendations/{profile_id}")
async def get_recommendations(profile_id: int, db: AsyncSession = Depends(get_db)):
    """Get AI-generated career recommendations for a candidate profile."""
    stmt = select(CandidateProfile).where(CandidateProfile.id == profile_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID {profile_id} not found.",
        )

    profile_dict = {
        "name": profile.name,
        "email": profile.email,
        "phone": profile.phone,
        "skills": profile.skills or [],
        "education": profile.education or [],
        "certifications": profile.certifications or [],
        "experience": profile.experience or [],
        "experience_years": profile.experience_years,
        "summary": profile.summary,
    }

    try:
        agent = CVAnalysisAgent()
        recommendations = await agent.get_career_recommendations(profile_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {e}",
        )

    return {"profile_id": profile.id, "recommendations": recommendations}
