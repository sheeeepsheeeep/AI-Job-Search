"""Cover Letters Router – generate, list, retrieve, and download as PDF."""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import CandidateProfile, CoverLetter, JobListing
from agents.cover_letter import CoverLetterAgent
from services.pdf_generator import generate_cover_letter_pdf

router = APIRouter(prefix="/cover-letters", tags=["Cover Letters"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Pydantic Schemas ──────────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    candidate_id: Optional[int] = None
    profile_id: Optional[int] = None
    job_id: int
    tone: Optional[str] = "professional"
    focus_areas: Optional[List[str]] = None
    additional_notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def set_candidate_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "profile_id" in data and "candidate_id" not in data:
                data["candidate_id"] = data["profile_id"]
        return data


class CoverLetterResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    content: Optional[str] = None
    email_template: Optional[str] = None
    pdf_path: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerateResponse(BaseModel):
    cover_letter: CoverLetterResponse
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_201_CREATED)
async def generate_cover_letter(body: GenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate a cover letter for a candidate/job pair using AI."""

    cid = body.candidate_id or body.profile_id
    if not cid:
        # Fallback to latest profile
        stmt = select(CandidateProfile).order_by(CandidateProfile.created_at.desc()).limit(1)
        result = await db.execute(stmt)
        candidate = result.scalars().first()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No candidate profile found. Please upload a CV first.",
            )
        cid = candidate.id
    else:
        # Fetch candidate profile
        result = await db.execute(
            select(CandidateProfile).where(CandidateProfile.id == cid)
        )
        candidate = result.scalars().first()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate profile with ID {cid} not found.",
            )

    # Fetch job listing
    result = await db.execute(
        select(JobListing).where(JobListing.id == body.job_id)
    )
    job = result.scalars().first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job listing with ID {body.job_id} not found.",
        )

    # Build dicts for the agent
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

    job_dict = {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary_range": job.salary_range,
        "description": job.description,
        "requirements": job.requirements,
        "url": job.url,
        "source": job.source,
        "remote_status": job.remote_status,
        "industry": job.industry,
        "experience_level": job.experience_level,
    }

    # Generate via AI agent
    agent = CoverLetterAgent()
    try:
        ai_result = await agent.generate_cover_letter(
            profile_dict,
            job_dict,
            tone=body.tone or "professional",
            focus_areas=body.focus_areas,
            additional_notes=body.additional_notes,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cover letter generation failed: {str(e)}",
        )

    # Save to database
    cover_letter = CoverLetter(
        candidate_id=body.candidate_id,
        job_id=body.job_id,
        content=ai_result.get("cover_letter", ""),
        email_template=ai_result.get("email_body", ""),
    )
    db.add(cover_letter)
    await db.flush()
    await db.refresh(cover_letter)

    return GenerateResponse(
        cover_letter=CoverLetterResponse(
            id=cover_letter.id,
            candidate_id=cover_letter.candidate_id,
            job_id=cover_letter.job_id,
            content=cover_letter.content,
            email_template=cover_letter.email_template,
            pdf_path=cover_letter.pdf_path,
            created_at=cover_letter.created_at,
        ),
        email_subject=ai_result.get("email_subject"),
        email_body=ai_result.get("email_body"),
    )


@router.get("/", response_model=List[CoverLetterResponse])
async def list_cover_letters(
    candidate_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all cover letters, optionally filtered by candidate_id."""
    stmt = select(CoverLetter)
    if candidate_id is not None:
        stmt = stmt.where(CoverLetter.candidate_id == candidate_id)
    stmt = stmt.order_by(CoverLetter.created_at.desc())

    result = await db.execute(stmt)
    cover_letters = result.scalars().all()
    return cover_letters


@router.get("/{cover_letter_id}", response_model=CoverLetterResponse)
async def get_cover_letter(cover_letter_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific cover letter by ID."""
    result = await db.execute(
        select(CoverLetter).where(CoverLetter.id == cover_letter_id)
    )
    cover_letter = result.scalars().first()
    if not cover_letter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cover letter with ID {cover_letter_id} not found.",
        )
    return cover_letter


@router.get("/{cover_letter_id}/pdf")
async def download_cover_letter_pdf(
    cover_letter_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Generate a PDF for the cover letter and return it as a file download."""

    # Fetch cover letter
    result = await db.execute(
        select(CoverLetter).where(CoverLetter.id == cover_letter_id)
    )
    cover_letter = result.scalars().first()
    if not cover_letter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cover letter with ID {cover_letter_id} not found.",
        )

    if not cover_letter.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cover letter has no content to generate a PDF from.",
        )

    # Fetch candidate name
    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.id == cover_letter.candidate_id)
    )
    candidate = result.scalars().first()
    candidate_name = candidate.name if candidate else "Candidate"

    # Fetch job company
    result = await db.execute(
        select(JobListing).where(JobListing.id == cover_letter.job_id)
    )
    job = result.scalars().first()
    company_name = job.company if job else "Company"

    # Generate PDF
    pdf_filename = f"cover_letter_{cover_letter_id}.pdf"
    output_path = os.path.join(UPLOAD_DIR, pdf_filename)

    try:
        pdf_path = generate_cover_letter_pdf(
            content=cover_letter.content,
            candidate_name=candidate_name,
            company_name=company_name,
            output_path=output_path,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(e)}",
        )

    # Update the cover letter record with the PDF path
    cover_letter.pdf_path = pdf_path
    await db.flush()

    return FileResponse(
        path=pdf_path,
        filename=pdf_filename,
        media_type="application/pdf",
    )
