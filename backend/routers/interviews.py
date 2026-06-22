"""Interview Preparation Router."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.database import get_db
from database.models import (
    CandidateProfile,
    InterviewAnswer,
    InterviewSession,
    JobListing,
    User,
)
from routers.auth import get_current_user
from agents.interview_prep import InterviewPrepAgent

router = APIRouter(prefix="/interviews", tags=["Interview Preparation"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    candidate_id: Optional[int] = None
    profile_id: Optional[int] = None
    job_id: Optional[int] = None
    interview_type: str = Field(default="hr", description="hr or technical")
    num_questions: int = Field(default=10, ge=1, le=30)


class SubmitAnswerRequest(BaseModel):
    question_index: int
    answer: str


class QuestionOut(BaseModel):
    question: str
    difficulty: Optional[str] = None
    category: Optional[str] = None
    tips: Optional[str] = None


class StartSessionResponse(BaseModel):
    session_id: int
    interview_type: Optional[str] = None
    questions: List[QuestionOut]


class AnswerEvalResponse(BaseModel):
    id: Optional[int] = None
    session_id: Optional[int] = None
    question_index: int
    score: Optional[float] = None
    feedback: Optional[str] = None
    ideal_answer: Optional[str] = None
    strengths: Optional[List[str]] = None
    improvements: Optional[List[str]] = None


class InterviewAnswerOut(BaseModel):
    id: int
    session_id: int
    question_index: int
    question_text: Optional[str] = None
    answer: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    ideal_answer: Optional[str] = None
    strengths: Optional[List[Any]] = None
    improvements: Optional[List[Any]] = None

    class Config:
        from_attributes = True


class SessionSummaryResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: Optional[int] = None
    interview_type: Optional[str] = None
    overall_score: Optional[float] = None
    feedback: Optional[str] = None
    questions: Optional[List[Any]] = None
    created_at: Optional[Any] = None

    class Config:
        from_attributes = True


class SessionDetailResponse(SessionSummaryResponse):
    interview_answers: List[InterviewAnswerOut] = []


class OverallFeedbackResponse(BaseModel):
    session_id: int
    overall_score: Optional[float] = None
    summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start", response_model=StartSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_interview_session(
    payload: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new interview session.

    Generates questions tailored to the candidate and optional job listing,
    then stores them in an InterviewSession.
    """
    cid = payload.candidate_id or payload.profile_id
    if not cid:
        # Fetch the latest profile of this user
        result = await db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == current_user.id).order_by(CandidateProfile.created_at.desc()).limit(1)
        )
        candidate = result.scalars().first()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No candidate profile found. Please upload a CV first.",
            )
        cid = candidate.id
    else:
        result = await db.execute(
            select(CandidateProfile).where((CandidateProfile.id == cid) & (CandidateProfile.user_id == current_user.id))
        )
        candidate = result.scalars().first()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {cid} not found or unauthorized.",
            )

    # Build candidate profile dict for the agent
    candidate_dict: Dict[str, Any] = {
        "name": candidate.name,
        "email": candidate.email,
        "skills": candidate.skills or [],
        "education": candidate.education or [],
        "experience": candidate.experience or [],
        "experience_years": candidate.experience_years,
        "summary": candidate.summary,
    }

    # Optionally fetch job listing
    job_dict: Dict[str, Any] = {}
    if payload.job_id is not None:
        result = await db.execute(
            select(JobListing).where(JobListing.id == payload.job_id)
        )
        job = result.scalars().first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job listing {payload.job_id} not found.",
            )
        job_dict = {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "requirements": job.requirements or [],
            "experience_level": job.experience_level,
        }

    # Generate questions via agent
    agent = InterviewPrepAgent()
    questions = await agent.generate_questions(
        job_listing=job_dict,
        candidate_profile=candidate_dict,
        interview_type=payload.interview_type,
    )

    # Trim to requested number
    questions = questions[: payload.num_questions]

    # Create session
    session_obj = InterviewSession(
        candidate_id=cid,
        job_id=payload.job_id,
        interview_type=payload.interview_type,
        questions=questions,
        scores=[],
        user_id=current_user.id,
    )
    db.add(session_obj)
    await db.flush()

    return StartSessionResponse(
        session_id=session_obj.id,
        interview_type=session_obj.interview_type,
        questions=[QuestionOut(**q) for q in questions],
    )


@router.post("/{session_id}/answer", response_model=AnswerEvalResponse)
async def submit_answer(
    session_id: int,
    payload: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit an answer to a question and receive an AI evaluation."""
    # Fetch session (user scoped)
    result = await db.execute(
        select(InterviewSession).where(
            (InterviewSession.id == session_id) & (InterviewSession.user_id == current_user.id)
        )
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session {session_id} not found or unauthorized.",
        )

    # Validate question_index
    stored_questions = session_obj.questions or []
    if payload.question_index < 0 or payload.question_index >= len(stored_questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"question_index {payload.question_index} out of range (0-{len(stored_questions) - 1}).",
        )

    question_data = stored_questions[payload.question_index]
    question_text = question_data.get("question", "") if isinstance(question_data, dict) else str(question_data)

    # Build job context for the agent
    job_context: Dict[str, Any] = {}
    if session_obj.job_id is not None:
        result = await db.execute(
            select(JobListing).where(JobListing.id == session_obj.job_id)
        )
        job = result.scalars().first()
        if job:
            job_context = {
                "title": job.title,
                "company": job.company,
                "description": job.description,
                "requirements": job.requirements or [],
            }

    # Evaluate via agent
    agent = InterviewPrepAgent()
    evaluation = await agent.evaluate_answer(
        question=question_text,
        answer=payload.answer,
        job_context=job_context,
    )

    # Save InterviewAnswer
    interview_answer = InterviewAnswer(
        session_id=session_id,
        question_index=payload.question_index,
        question_text=question_text,
        answer=payload.answer,
        score=evaluation.get("score"),
        feedback=evaluation.get("feedback"),
        ideal_answer=evaluation.get("ideal_answer"),
        strengths=evaluation.get("strengths"),
        improvements=evaluation.get("improvements"),
    )
    db.add(interview_answer)
    await db.flush()

    # Also update session scores list
    scores_list = list(session_obj.scores or [])
    scores_list.append({
        "question_index": payload.question_index,
        "score": evaluation.get("score"),
        "feedback": evaluation.get("feedback"),
    })
    session_obj.scores = scores_list

    return AnswerEvalResponse(
        answer_id=interview_answer.id,
        question_index=payload.question_index,
        score=evaluation.get("score"),
        feedback=evaluation.get("feedback"),
        ideal_answer=evaluation.get("ideal_answer"),
        strengths=evaluation.get("strengths"),
        improvements=evaluation.get("improvements"),
    )


@router.get("/{session_id}/feedback", response_model=OverallFeedbackResponse)
async def get_overall_feedback(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate overall feedback for a completed interview session."""
    # Fetch session (user scoped)
    result = await db.execute(
        select(InterviewSession).where(
            (InterviewSession.id == session_id) & (InterviewSession.user_id == current_user.id)
        )
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session {session_id} not found or unauthorized.",
        )

    # Fetch all answers for this session
    result = await db.execute(
        select(InterviewAnswer)
        .where(InterviewAnswer.session_id == session_id)
        .order_by(InterviewAnswer.question_index)
    )
    answer_rows = result.scalars().all()

    if not answer_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No answers submitted yet for this session.",
        )

    # Prepare data for the agent
    questions_list = [row.question_text or "" for row in answer_rows]
    answers_list = [row.answer or "" for row in answer_rows]
    scores_list = [int(row.score) if row.score is not None else 5 for row in answer_rows]

    agent = InterviewPrepAgent()
    feedback = await agent.generate_overall_feedback(
        questions=questions_list,
        answers=answers_list,
        scores=scores_list,
    )

    # Update session record
    session_obj.overall_score = feedback.get("overall_score")
    session_obj.feedback = feedback.get("summary")
    session_obj.recommendations = feedback.get("recommendations")

    return OverallFeedbackResponse(
        session_id=session_id,
        overall_score=feedback.get("overall_score"),
        summary=feedback.get("summary"),
        strengths=feedback.get("strengths"),
        weaknesses=feedback.get("weaknesses"),
        recommendations=feedback.get("recommendations"),
    )


@router.get("/history", response_model=List[SessionSummaryResponse])
async def list_interview_sessions(
    candidate_id: Optional[int] = Query(None, description="Filter by candidate ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List interview sessions, filtered by current user."""
    stmt = select(InterviewSession).where(InterviewSession.user_id == current_user.id).order_by(InterviewSession.created_at.desc())

    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return sessions


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_interview_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific interview session with all its answers."""
    # Eager-load the answers relationship (user scoped)
    result = await db.execute(
        select(InterviewSession)
        .where((InterviewSession.id == session_id) & (InterviewSession.user_id == current_user.id))
        .options(selectinload(InterviewSession.answer_records))
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session {session_id} not found or unauthorized.",
        )

    # Build response — the 'answers' relationship holds InterviewAnswer objects
    answer_out = [
        InterviewAnswerOut.model_validate(a)
        for a in session_obj.answer_records
    ]

    return SessionDetailResponse(
        id=session_obj.id,
        candidate_id=session_obj.candidate_id,
        job_id=session_obj.job_id,
        interview_type=session_obj.interview_type,
        overall_score=session_obj.overall_score,
        feedback=session_obj.feedback,
        questions=session_obj.questions,
        created_at=session_obj.created_at,
        interview_answers=answer_out,
    )
