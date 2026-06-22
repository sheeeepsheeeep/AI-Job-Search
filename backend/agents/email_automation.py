"""
Email Automation Agent

Manages the sending of job-application emails (with optional attachments),
duplicate-application checks, and follow-up scheduling.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class EmailAutomationAgent:
    """Automates email-based job-application workflows."""

    def __init__(self, email_service: Any | None = None) -> None:
        """Initialise with an optional email-service instance.

        Parameters
        ----------
        email_service:
            An object that exposes ``async send_email(to, subject, body,
            attachments)`` and optionally ``async send_email_with_attachments``.
            When *None*, the agent will attempt to import
            ``services.email_service.EmailService`` at call time.
        """
        self.email_service = email_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send_application(
        self,
        to_email: str,
        subject: str,
        body: str,
        cv_path: str | None = None,
        cover_letter_path: str | None = None,
    ) -> dict[str, Any]:
        """Send a job-application email, optionally with CV and cover letter.

        Returns
        -------
        dict with keys ``success`` (bool) and ``message`` (str).
        """
        service = self._get_service()
        if service is None:
            return {
                "success": False,
                "message": "Email service is not available.",
            }

        # Build attachment list
        attachments: list[str] = []
        if cv_path:
            attachments.append(cv_path)
        if cover_letter_path:
            attachments.append(cover_letter_path)

        try:
            if attachments:
                await service.send_email_with_attachments(
                    to_email=to_email,
                    subject=subject,
                    body=body,
                    attachment_paths=attachments,
                )
            else:
                await service.send_email(
                    to_email=to_email,
                    subject=subject,
                    body=body,
                )

            logger.info("Application email sent to %s — subject: %s", to_email, subject)
            return {
                "success": True,
                "message": f"Application email sent successfully to {to_email}.",
            }
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to_email, exc, exc_info=True)
            return {
                "success": False,
                "message": f"Failed to send email: {exc}",
            }

    async def check_duplicate(
        self,
        email: str,
        job_title: str,
        db_session: Any,
    ) -> bool:
        """Check whether the candidate has already applied for this job.

        Queries the ``applications`` table (via SQLAlchemy async session)
        for a matching ``contact_email`` + ``job_title`` combination.
        Returns *True* if a duplicate exists.
        """
        try:
            from sqlalchemy import select
            from database.models import Application  # type: ignore[import-untyped]

            stmt = (
                select(Application)
                .where(Application.contact_email == email)
                .where(Application.job_title == job_title)
            )
            result = await db_session.execute(stmt)
            existing = result.scalars().first()
            if existing:
                logger.info(
                    "Duplicate application detected: %s — %s", email, job_title
                )
                return True
            return False
        except ImportError:
            logger.warning(
                "database.models.Application not available — skipping duplicate check."
            )
            return False
        except Exception as exc:
            logger.error("Duplicate check failed: %s", exc)
            return False

    async def get_follow_ups_due(
        self,
        db_session: Any,
        days_threshold: int = 7,
    ) -> list[dict[str, Any]]:
        """Return applications that need a follow-up email.

        An application is due for follow-up if:
        * Its status is ``applied`` or ``pending``.
        * It was submitted more than *days_threshold* days ago.
        * No follow-up has been recorded yet (``follow_up_date`` is null).
        """
        try:
            from sqlalchemy import select
            from database.models import Application  # type: ignore[import-untyped]

            cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)

            stmt = (
                select(Application)
                .where(Application.status.in_(["applied", "pending"]))
                .where(Application.applied_date <= cutoff)
                .where(Application.follow_up_date.is_(None))
            )
            result = await db_session.execute(stmt)
            rows = result.scalars().all()

            follow_ups: list[dict[str, Any]] = []
            for app in rows:
                follow_ups.append(
                    {
                        "id": app.id,
                        "job_title": app.job_title,
                        "company": app.company,
                        "contact_email": app.contact_email,
                        "applied_date": str(app.applied_date),
                        "days_since_applied": (
                            datetime.now(timezone.utc) - app.applied_date
                        ).days,
                    }
                )

            logger.info("Found %d applications due for follow-up.", len(follow_ups))
            return follow_ups
        except ImportError:
            logger.warning(
                "database.models.Application not available — "
                "cannot retrieve follow-ups."
            )
            return []
        except Exception as exc:
            logger.error("Follow-up retrieval failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_service(self) -> Any | None:
        """Lazy-load the email service if not injected."""
        if self.email_service is not None:
            return self.email_service
        try:
            from services.email_service import EmailService  # type: ignore[import-untyped]

            self.email_service = EmailService()
            return self.email_service
        except ImportError:
            logger.warning("services.email_service is not available.")
            return None
        except Exception as exc:
            logger.error("Failed to initialise EmailService: %s", exc)
            return None
