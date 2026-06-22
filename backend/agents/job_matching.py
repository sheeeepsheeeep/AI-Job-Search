"""
Job Matching Agent

Compares a candidate profile against a job listing's requirements and
produces a detailed match analysis with a numeric score.
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

JOB_MATCH_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a professional talent-matching analyst. Compare the "
                "candidate profile against the job listing and produce a detailed "
                "match analysis.\n\n"
                "Return ONLY valid JSON — no markdown fences — with this schema:\n"
                "{{\n"
                '  "match_score": <float 0-100>,\n'
                '  "matching_skills": ["skill1", ...],\n'
                '  "missing_skills": ["skill1", ...],\n'
                '  "experience_match": {{\n'
                '    "required_years": <int or null>,\n'
                '    "candidate_years": <int or null>,\n'
                '    "meets_requirement": <bool>\n'
                "  }},\n"
                '  "education_match": {{\n'
                '    "required": "degree or null",\n'
                '    "candidate_has": "degree or null",\n'
                '    "meets_requirement": <bool>\n'
                "  }},\n"
                '  "recommendations": [\n'
                '    "Actionable suggestion 1",\n'
                '    "Actionable suggestion 2"\n'
                "  ],\n"
                '  "analysis": "A 3-5 sentence narrative analysis of the match"\n'
                "}}\n\n"
                "Scoring guidelines:\n"
                "• 90-100: Near-perfect match — candidate exceeds requirements.\n"
                "• 70-89: Strong match — meets most requirements, minor gaps.\n"
                "• 50-69: Moderate match — several gaps but transferable skills.\n"
                "• 30-49: Weak match — significant skill or experience gaps.\n"
                "• 0-29: Poor match — fundamentally different profile."
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


class JobMatchingAgent:
    """Scores and analyses the fit between a candidate and a job."""

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

    async def calculate_match(
        self,
        candidate_profile: dict[str, Any],
        job_listing: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute a match-score and detailed analysis.

        Returns
        -------
        dict with keys: match_score, matching_skills, missing_skills,
        experience_match, education_match, recommendations, analysis.
        """
        chain = JOB_MATCH_PROMPT | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "profile_json": json.dumps(candidate_profile, default=str),
                    "job_json": json.dumps(job_listing, default=str),
                }
            )
            content: str = response.content  # type: ignore[union-attr]
            result = self._parse_json(content)
            result["match_score"] = self._clamp(
                float(result.get("match_score", 0)), 0.0, 100.0
            )
            logger.info(
                "Match score %.1f for %s @ %s",
                result["match_score"],
                job_listing.get("title", "?"),
                job_listing.get("company", "?"),
            )
            return result
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse match JSON: %s", exc)
            return self._error_result(str(exc))
        except Exception as exc:
            logger.error("Match calculation failed: %s", exc, exc_info=True)
            return self._error_result(str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    @staticmethod
    def _error_result(reason: str) -> dict[str, Any]:
        return {
            "match_score": 0.0,
            "matching_skills": [],
            "missing_skills": [],
            "experience_match": {
                "required_years": None,
                "candidate_years": None,
                "meets_requirement": False,
            },
            "education_match": {
                "required": None,
                "candidate_has": None,
                "meets_requirement": False,
            },
            "recommendations": [f"Analysis failed: {reason}"],
            "analysis": f"Unable to perform match analysis — {reason}",
        }

    @staticmethod
    def _parse_json(text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -len("```")]
        return json.loads(cleaned.strip())
