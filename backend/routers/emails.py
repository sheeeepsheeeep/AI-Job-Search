"""Email Management Router."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import Application, EmailLog
from agents.email_automation import EmailAutomationAgent

router = APIRouter(prefix="/emails", tags=["Email Management"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class SendEmailRequest(BaseModel):
    application_id: Optional[int] = None
    recipient_email: str
    subject: Optional[str] = None
    body: Optional[str] = None


class EmailLogResponse(BaseModel):
    id: int
    application_id: Optional[int] = None
    email_type: str
    recipient: str
    subject: Optional[str] = None
    body: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/send", response_model=dict, status_code=status.HTTP_200_OK)
async def send_application_email(
    payload: SendEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send an application email.

    If subject/body are not provided they are auto-generated from the
    application details.
    """
    application = None
    if payload.application_id is not None:
        # Fetch the application
        result = await db.execute(
            select(Application).where(Application.id == payload.application_id)
        )
        application = result.scalars().first()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application {payload.application_id} not found.",
            )

    # Auto-generate subject / body when not supplied
    if application:
        subject = payload.subject or f"Application for {application.job_title} at {application.company_name}"
        body = payload.body or (
            f"Dear Hiring Manager,\n\n"
            f"I am writing to express my interest in the {application.job_title} "
            f"position at {application.company_name}.\n\n"
            f"Please find my application materials attached.\n\n"
            f"Best regards"
        )
    else:
        subject = payload.subject or "Job Application"
        body = payload.body or (
            f"Dear Hiring Manager,\n\n"
            f"I am writing to express my interest in the open position at your company.\n\n"
            f"Please find my application materials attached.\n\n"
            f"Best regards"
        )

    # Create a pending email log
    email_log = EmailLog(
        application_id=application.id if application else None,
        email_type="application",
        recipient=payload.recipient_email,
        subject=subject,
        body=body,
        status="pending",
    )
    db.add(email_log)
    await db.flush()  # get the id assigned

    # Send via the agent
    agent = EmailAutomationAgent()
    send_result = await agent.send_application(
        to_email=payload.recipient_email,
        subject=subject,
        body=body,
        cv_path=None,
        cover_letter_path=None,
    )

    # Update the log based on outcome
    if send_result.get("success"):
        email_log.status = "sent"
        email_log.sent_at = datetime.now(timezone.utc)
    else:
        email_log.status = "failed"
        email_log.error_message = send_result.get("message", "Unknown error")

    return {
        "email_log_id": email_log.id,
        "success": send_result.get("success", False),
        "message": send_result.get("message", ""),
    }


@router.get("/history", response_model=List[EmailLogResponse])
async def list_email_history(
    application_id: Optional[int] = Query(None, description="Filter by application ID"),
    db: AsyncSession = Depends(get_db),
):
    """List email logs, optionally filtered by application_id."""
    stmt = select(EmailLog).order_by(EmailLog.created_at.desc())
    if application_id is not None:
        stmt = stmt.where(EmailLog.application_id == application_id)

    result = await db.execute(stmt)
    logs = result.scalars().all()
    return logs


@router.post("/follow-up/{application_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def send_follow_up_email(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Send a follow-up email for an application."""
    # Fetch application
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalars().first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found.",
        )

    subject = f"Follow-up: {application.job_title} at {application.company_name}"
    body = (
        f"Dear Hiring Manager,\n\n"
        f"I hope this message finds you well. I am following up on my application "
        f"for the {application.job_title} position at {application.company_name}.\n\n"
        f"I remain very interested in this opportunity and would welcome the chance "
        f"to discuss how my skills and experience align with your needs.\n\n"
        f"Thank you for your time and consideration.\n\n"
        f"Best regards"
    )

    recipient = application.email_address
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application has no email_address on file.",
        )

    # Create a pending email log
    email_log = EmailLog(
        application_id=application.id,
        email_type="follow_up",
        recipient=recipient,
        subject=subject,
        body=body,
        status="pending",
    )
    db.add(email_log)
    await db.flush()

    # Send via agent
    agent = EmailAutomationAgent()
    send_result = await agent.send_application(
        to_email=recipient,
        subject=subject,
        body=body,
    )

    if send_result.get("success"):
        email_log.status = "sent"
        email_log.sent_at = datetime.now(timezone.utc)
        # Update follow_up_date on the application
        application.follow_up_date = datetime.now(timezone.utc)
    else:
        email_log.status = "failed"
        email_log.error_message = send_result.get("message", "Unknown error")

    return {
        "email_log_id": email_log.id,
        "success": send_result.get("success", False),
        "message": send_result.get("message", ""),
    }
