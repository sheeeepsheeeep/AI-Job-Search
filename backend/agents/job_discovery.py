"""
Job Discovery Agent

Searches for job opportunities using the web-scraper service,
then leverages an LLM to rank and enhance the raw listings.
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

JOB_ENHANCEMENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a job-market analyst. You will receive a list of raw job "
                "listings in JSON format and a search query. For each listing:\n"
                "1. Clean up the description.\n"
                "2. Extract key requirements, benefits, and salary range if mentioned.\n"
                "3. Add a relevance_note explaining why this job matches the query.\n\n"
                "Return ONLY a valid JSON array of enhanced job objects — no markdown "
                "fences. Each object must have:\n"
                '{{"title", "company", "location", "url", "description", '
                '"requirements": [...], "benefits": [...], "salary_range", '
                '"relevance_note"}}'
            ),
        ),
        (
            "human",
            "Search query: {query}\nLocation: {location}\n\nRaw listings:\n{jobs_json}",
        ),
    ]
)

JOB_RANKING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a career-matching expert. Given a candidate profile and a "
                "list of job listings, rank the jobs from most to least relevant for "
                "the candidate. Return ONLY a valid JSON array of objects with:\n"
                '{{"title", "company", "location", "url", "rank", '
                '"relevance_score": <0-100>, "match_reason"}}\n'
                "Sort by relevance_score descending."
            ),
        ),
        (
            "human",
            "Candidate profile:\n{profile_json}\n\nJobs:\n{jobs_json}",
        ),
    ]
)


class JobDiscoveryAgent:
    """Discovers, enhances, and ranks job listings."""

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
            temperature=0.2,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search_jobs(
        self,
        query: str,
        location: str = "",
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for jobs using the web-scraper service, then enhance via LLM.

        Parameters
        ----------
        query:
            Job title / keyword search string.
        location:
            Optional geographic filter.
        filters:
            Optional dict of extra filters (e.g. remote, salary_min).

        Returns a list of enhanced job-listing dicts.
        """
        raw_jobs = await self._fetch_jobs(query, location, filters)

        if not raw_jobs:
            logger.warning("No raw jobs returned for query=%s location=%s", query, location)
            return []

        # Enhance via LLM (only send first 20 to avoid token overflow)
        batch = raw_jobs[:20]
        chain = JOB_ENHANCEMENT_PROMPT | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "query": query,
                    "location": location,
                    "jobs_json": json.dumps(batch, default=str),
                }
            )
            enhanced = self._parse_json(response.content)  # type: ignore[union-attr]
            if not isinstance(enhanced, list):
                enhanced = [enhanced]
            logger.info("Enhanced %d jobs for query=%s", len(enhanced), query)
            return enhanced
        except Exception as exc:
            logger.error("LLM enhancement failed, returning raw jobs: %s", exc)
            return raw_jobs

    async def rank_jobs(
        self,
        jobs: list[dict[str, Any]],
        candidate_profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Rank a list of jobs by relevance to the candidate profile."""
        if not jobs:
            return []

        chain = JOB_RANKING_PROMPT | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "profile_json": json.dumps(candidate_profile, default=str),
                    "jobs_json": json.dumps(jobs[:20], default=str),
                }
            )
            ranked = self._parse_json(response.content)  # type: ignore[union-attr]
            if not isinstance(ranked, list):
                ranked = [ranked]
            ranked.sort(key=lambda j: j.get("relevance_score", 0), reverse=True)
            return ranked
        except Exception as exc:
            logger.error("Job ranking failed: %s", exc)
            return jobs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _fetch_jobs(
        self,
        query: str,
        location: str,
        filters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Fetch raw job listings from the web-scraper service.

        Attempts to import and use ``services.web_scraper``. If unavailable
        or the call fails, returns an empty list so the agent degrades
        gracefully.
        """
        try:
            from services.web_scraper import scrape_jobs

            # scrape_jobs is a synchronous function that returns a list
            results = scrape_jobs(
                query=query,
                location=location,
                filters=filters or {},
            )
            return results
        except ImportError:
            logger.warning(
                "services.web_scraper is not available — returning empty list."
            )
            return []
        except Exception as exc:
            logger.error("Web-scraper fetch failed: %s", exc)
            return []

    @staticmethod
    def _parse_json(text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -len("```")]
        return json.loads(cleaned.strip())
