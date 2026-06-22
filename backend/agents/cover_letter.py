"""
Cover Letter Agent

Generates personalised cover letters and professional email templates
tailored to a specific job listing and candidate profile.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

COVER_LETTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a professional career writer who specialises in crafting "
                "compelling cover letters and application emails.\n\n"
                "Given the candidate profile and job listing, produce:\n"
                "1. A full cover letter (3-4 paragraphs, written in the requested tone).\n"
                "2. A concise email subject line for the application.\n"
                "3. A professional email body (shorter than the cover letter) "
                "suitable for sending via email, with the cover letter as an "
                "attachment.\n\n"
                "Guidelines for the cover letter:\n"
                "• Address the hiring manager by name if available, otherwise "
                "use 'Dear Hiring Manager'.\n"
                "• Opening paragraph: express enthusiasm and state the role.\n"
                "• Body paragraphs: highlight the candidate's most relevant "
                "skills, experience, and achievements. Tie them directly to "
                "the job requirements.\n"
                "• Closing paragraph: reiterate interest, mention availability, "
                "and include a call to action.\n"
                "• Tone constraint: Write the cover letter in a {tone} tone (e.g. professional, creative, casual, bold).\n"
                "• Focus areas: Make sure to emphasize these aspects of the candidate: {focus_areas}.\n"
                "• Additional instructions/notes: Incorporate these notes/context: {additional_notes}.\n\n"
                "Guidelines for the email body:\n"
                "• 2-3 short paragraphs.\n"
                "• Match the tone requested ({tone}).\n"
                "• Mention the role, a key qualification, and that the cover "
                "letter and CV are attached.\n\n"
                "Return ONLY valid JSON — no markdown fences:\n"
                "{{\n"
                '  "cover_letter": "...",\n'
                '  "email_subject": "...",\n'
                '  "email_body": "..."\n'
                "}}"
            ),
        ),
        (
            "human",
            (
                "Candidate profile:\n{profile_json}\n\n"
                "Job listing:\n{job_json}"
            ),
        ),
    ]
)


class CoverLetterAgent:
    """Generates cover letters and application email templates."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.llm = ChatGroq(
            api_key=self.api_key,
            model=self.model,
            temperature=0.7,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_cover_letter(
        self,
        candidate_profile: dict[str, Any],
        job_listing: dict[str, Any],
        tone: str = "professional",
        focus_areas: list[str] | None = None,
        additional_notes: str | None = None,
    ) -> dict[str, str]:
        """Generate a cover letter and email template.

        Returns
        -------
        dict with keys: cover_letter, email_subject, email_body.
        """
        chain = COVER_LETTER_PROMPT | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "profile_json": json.dumps(candidate_profile, default=str),
                    "job_json": json.dumps(job_listing, default=str),
                    "tone": tone,
                    "focus_areas": ", ".join(focus_areas) if focus_areas else "None specified",
                    "additional_notes": additional_notes or "None specified",
                }
            )
            content: str = response.content  # type: ignore[union-attr]
            result = self._parse_json(content)

            # Ensure all expected keys are present
            for key in ("cover_letter", "email_subject", "email_body"):
                if key not in result:
                    result[key] = ""

            logger.info(
                "Cover letter generated for %s at %s with tone %s",
                job_listing.get("title", "unknown role"),
                job_listing.get("company", "unknown company"),
                tone,
            )
            return result
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse cover-letter JSON: %s", exc)
            return self._fallback(candidate_profile, job_listing, str(exc))
        except Exception as exc:
            logger.error("Cover letter generation failed: %s", exc, exc_info=True)
            return self._fallback(candidate_profile, job_listing, str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback(
        profile: dict[str, Any],
        job: dict[str, Any],
        error: str,
    ) -> dict[str, str]:
        name = profile.get("name", "Candidate")
        title = job.get("title", "the open position")
        company = job.get("company", "your organisation")
        return {
            "cover_letter": (
                f"Dear Hiring Manager,\n\n"
                f"I am writing to express my interest in the {title} position "
                f"at {company}. Please find my CV attached for your review.\n\n"
                f"Sincerely,\n{name}"
            ),
            "email_subject": f"Application for {title} — {name}",
            "email_body": (
                f"Dear Hiring Manager,\n\n"
                f"Please find attached my application for the {title} role at "
                f"{company}.\n\n"
                f"Best regards,\n{name}\n\n"
                f"[Auto-generated fallback — LLM error: {error}]"
            ),
        }

    @staticmethod
    def _parse_json(text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -len("```")]
        return json.loads(cleaned.strip(), strict=False)
