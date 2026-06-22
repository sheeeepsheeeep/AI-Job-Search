"""
CV Analysis Agent

Parses CV / résumé text and extracts structured profile data using an LLM.
Also generates career-path recommendations based on the extracted profile.
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
# Prompt templates
# ---------------------------------------------------------------------------

CV_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert CV / résumé analyst. "
                "Extract structured information from the CV text provided by the user. "
                "Return ONLY valid JSON — no markdown fences, no commentary.\n\n"
                "Required JSON schema:\n"
                "{{\n"
                '  "name": "Full name of the candidate",\n'
                '  "email": "Email address or null",\n'
                '  "phone": "Phone number or null",\n'
                '  "location": "City / Country or null",\n'
                '  "summary": "A 2-3 sentence professional summary",\n'
                '  "skills": ["skill1", "skill2", ...],\n'
                '  "education": [\n'
                "    {{\n"
                '      "degree": "Degree title",\n'
                '      "institution": "University / School",\n'
                '      "year": "Graduation year or null",\n'
                '      "field": "Field of study or null"\n'
                "    }}\n"
                "  ],\n"
                '  "certifications": ["cert1", "cert2", ...],\n'
                '  "experience": [\n'
                "    {{\n"
                '      "title": "Job title",\n'
                '      "company": "Company name",\n'
                '      "duration": "e.g. Jan 2020 – Dec 2022",\n'
                '      "description": "Brief description of responsibilities and achievements"\n'
                "    }}\n"
                "  ],\n"
                '  "experience_years": 0,\n'
                '  "languages": ["English", ...]\n'
                "}}\n\n"
                "If a field cannot be determined from the CV, use null or an empty list."
            ),
        ),
        ("human", "Here is the CV text:\n\n{cv_text}"),
    ]
)

CAREER_RECOMMENDATIONS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert career advisor. "
                "Based on the candidate profile JSON provided, generate a list of "
                "career recommendations. Each recommendation should be a JSON object "
                "with the keys: role, reason, growth_potential (high/medium/low), "
                "and required_upskilling (list of skills to learn).\n\n"
                "Return ONLY a valid JSON array — no markdown fences."
            ),
        ),
        ("human", "Candidate profile:\n\n{profile_json}"),
    ]
)


class CVAnalysisAgent:
    """Analyses CV text and produces structured profile data."""

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
            temperature=0.1,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_cv(self, cv_text: str) -> dict[str, Any]:
        """Parse CV text and return structured profile data.

        Returns a dict with keys: name, email, phone, location, summary,
        skills, education, certifications, experience, experience_years,
        languages.
        """
        if not cv_text or not cv_text.strip():
            raise ValueError("CV text is empty — nothing to analyse.")

        chain = CV_ANALYSIS_PROMPT | self.llm

        try:
            response = await chain.ainvoke({"cv_text": cv_text})
            content: str = response.content  # type: ignore[union-attr]
            profile = self._parse_json(content)
            logger.info("CV analysis complete for candidate: %s", profile.get("name"))
            return profile
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON response: %s", exc)
            return self._fallback_profile(cv_text)
        except Exception as exc:
            logger.error("CV analysis failed: %s", exc, exc_info=True)
            raise

    async def get_career_recommendations(
        self, profile: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate career-path recommendations from a profile dict."""
        chain = CAREER_RECOMMENDATIONS_PROMPT | self.llm

        try:
            response = await chain.ainvoke(
                {"profile_json": json.dumps(profile, default=str)}
            )
            content: str = response.content  # type: ignore[union-attr]
            recommendations = self._parse_json(content)
            if not isinstance(recommendations, list):
                recommendations = [recommendations]
            return recommendations
        except Exception as exc:
            logger.error("Career recommendation generation failed: %s", exc)
            return [
                {
                    "role": "Unable to generate recommendations",
                    "reason": str(exc),
                    "growth_potential": "unknown",
                    "required_upskilling": [],
                }
            ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(text: str) -> Any:
        """Strip markdown fences if present and parse JSON."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -len("```")]
        return json.loads(cleaned.strip())

    @staticmethod
    def _fallback_profile(cv_text: str) -> dict[str, Any]:
        """Return a minimal profile when the LLM response cannot be parsed."""
        return {
            "name": None,
            "email": None,
            "phone": None,
            "location": None,
            "summary": cv_text[:300],
            "skills": [],
            "education": [],
            "certifications": [],
            "experience": [],
            "experience_years": 0,
            "languages": [],
        }
