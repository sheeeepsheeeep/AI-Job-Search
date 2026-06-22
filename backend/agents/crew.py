"""
Crew Orchestration Module

Provides two ways to run the full job-search pipeline:

1. **JobSearchCrew** — uses CrewAI (Agent → Task → Crew) for structured
   multi-agent orchestration.
2. **run_full_pipeline()** — a simpler, sequential fallback that works
   without CrewAI installed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

# Local agent imports (always available)
from agents.cv_analysis import CVAnalysisAgent
from agents.job_discovery import JobDiscoveryAgent
from agents.job_matching import JobMatchingAgent
from agents.cover_letter import CoverLetterAgent
from agents.email_automation import EmailAutomationAgent
from agents.interview_prep import InterviewPrepAgent
from agents.application_tracking import ApplicationTrackingAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try importing CrewAI — it may not be installed in every environment
# ---------------------------------------------------------------------------

_CREWAI_AVAILABLE = False
try:
    from crewai import Agent as CrewAgent, Task, Crew, Process  # type: ignore[import-untyped]

    _CREWAI_AVAILABLE = True
except ImportError:
    logger.warning(
        "crewai package is not installed — JobSearchCrew will be unavailable. "
        "Use run_full_pipeline() as a fallback."
    )


# =========================================================================
# 1. CrewAI-based orchestration
# =========================================================================


class JobSearchCrew:
    """Wraps custom agent classes in CrewAI Agents / Tasks / Crew.

    Usage::

        crew = JobSearchCrew(api_key="sk-...", model="gpt-4o-mini")
        results = crew.kickoff({
            "cv_text": "...",
            "job_query": "Python developer",
            "location": "London",
        })
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        if not _CREWAI_AVAILABLE:
            raise ImportError(
                "crewai is not installed. Install it with: pip install crewai"
            )

        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

        # Instantiate custom agents
        self._cv_agent = CVAnalysisAgent(api_key=self.api_key, model=self.model)
        self._discovery_agent = JobDiscoveryAgent(api_key=self.api_key, model=self.model)
        self._matching_agent = JobMatchingAgent(api_key=self.api_key, model=self.model)
        self._cover_letter_agent = CoverLetterAgent(api_key=self.api_key, model=self.model)

        # Build CrewAI Agent wrappers
        self.crew_cv_analyst = CrewAgent(
            role="CV Analyst",
            goal="Parse the candidate's CV and extract a structured profile.",
            backstory=(
                "You are an expert résumé analyst with years of experience in "
                "talent acquisition. You can rapidly identify skills, experience, "
                "and qualifications from any CV format."
            ),
            verbose=True,
            allow_delegation=False,
        )

        self.crew_job_researcher = CrewAgent(
            role="Job Researcher",
            goal="Find and enhance relevant job listings for the candidate.",
            backstory=(
                "You are a meticulous job-market researcher who scours multiple "
                "sources to find the best opportunities and enriches each listing "
                "with actionable context."
            ),
            verbose=True,
            allow_delegation=False,
        )

        self.crew_matcher = CrewAgent(
            role="Job Matcher",
            goal="Score and rank job listings against the candidate profile.",
            backstory=(
                "You are a data-driven talent-matching specialist who provides "
                "objective, detailed fit analyses to guide candidates toward the "
                "best opportunities."
            ),
            verbose=True,
            allow_delegation=False,
        )

        self.crew_writer = CrewAgent(
            role="Cover Letter Writer",
            goal="Craft compelling, personalised cover letters and emails.",
            backstory=(
                "You are a professional career writer with a talent for "
                "translating candidate strengths into persuasive narratives "
                "that resonate with hiring managers."
            ),
            verbose=True,
            allow_delegation=False,
        )

    # ------------------------------------------------------------------
    # Task definitions
    # ------------------------------------------------------------------

    def _build_tasks(self, inputs: dict[str, Any]) -> list[Task]:
        """Create the sequential CrewAI tasks."""
        cv_text = inputs.get("cv_text", "")
        job_query = inputs.get("job_query", "")
        location = inputs.get("location", "")
        filters = inputs.get("filters", {})

        analyze_cv_task = Task(
            description=(
                f"Analyse the following CV text and extract a structured profile "
                f"including name, email, skills, experience, education, and "
                f"certifications.\n\nCV Text:\n{cv_text[:3000]}"
            ),
            expected_output=(
                "A JSON object with keys: name, email, phone, location, summary, "
                "skills, education, certifications, experience, experience_years, languages."
            ),
            agent=self.crew_cv_analyst,
        )

        search_jobs_task = Task(
            description=(
                f"Search for job listings matching the query '{job_query}' "
                f"in location '{location}'. Apply any relevant filters: "
                f"{json.dumps(filters)}. Enhance the listings with requirements "
                f"and relevance notes."
            ),
            expected_output=(
                "A JSON array of enhanced job listings, each with title, company, "
                "location, url, description, requirements, benefits, salary_range."
            ),
            agent=self.crew_job_researcher,
        )

        match_jobs_task = Task(
            description=(
                "For each discovered job listing, calculate a match score against "
                "the candidate profile extracted in Step 1. Identify matching and "
                "missing skills, and provide recommendations."
            ),
            expected_output=(
                "A JSON array of match results, each with match_score, "
                "matching_skills, missing_skills, recommendations, analysis."
            ),
            agent=self.crew_matcher,
        )

        cover_letter_task = Task(
            description=(
                "For the top 3 matched jobs, generate a personalised cover letter "
                "and professional application email. Highlight the candidate's "
                "most relevant experience and skills."
            ),
            expected_output=(
                "A JSON array of objects, each with cover_letter, email_subject, "
                "email_body, and the associated job title."
            ),
            agent=self.crew_writer,
        )

        return [analyze_cv_task, search_jobs_task, match_jobs_task, cover_letter_task]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def kickoff(self, inputs: dict[str, Any]) -> Any:
        """Build the Crew and execute the pipeline.

        Parameters
        ----------
        inputs:
            Dict with keys: cv_text, job_query, location, filters (optional).

        Returns the CrewAI Crew output.
        """
        tasks = self._build_tasks(inputs)

        crew = Crew(
            agents=[
                self.crew_cv_analyst,
                self.crew_job_researcher,
                self.crew_matcher,
                self.crew_writer,
            ],
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        logger.info("Kicking off JobSearchCrew pipeline …")
        result = crew.kickoff()
        logger.info("JobSearchCrew pipeline complete.")
        return result


# =========================================================================
# 2. Standalone sequential pipeline (no CrewAI dependency)
# =========================================================================


async def run_full_pipeline(
    cv_text: str,
    job_query: str,
    location: str = "",
    filters: dict[str, Any] | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Execute the entire job-search pipeline sequentially.

    This function does **not** require CrewAI and can be used as a
    standalone orchestrator or as a fallback.

    Returns
    -------
    dict with keys: profile, recommendations, jobs, matches,
    cover_letters, and metadata.
    """
    _api = api_key or os.getenv("GROQ_API_KEY", "")
    _model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    cv_agent = CVAnalysisAgent(api_key=_api, model=_model)
    discovery_agent = JobDiscoveryAgent(api_key=_api, model=_model)
    matching_agent = JobMatchingAgent(api_key=_api, model=_model)
    cover_letter_agent = CoverLetterAgent(api_key=_api, model=_model)

    results: dict[str, Any] = {"metadata": {"status": "running"}}

    # Step 1 — Analyse CV
    logger.info("[Pipeline] Step 1/4: Analysing CV …")
    profile = await cv_agent.analyze_cv(cv_text)
    results["profile"] = profile

    # Step 1b — Career recommendations (runs concurrently with step 2)
    recommendations_task = asyncio.create_task(
        cv_agent.get_career_recommendations(profile)
    )

    # Step 2 — Discover jobs
    logger.info("[Pipeline] Step 2/4: Searching for jobs …")
    jobs = await discovery_agent.search_jobs(
        query=job_query, location=location, filters=filters or {}
    )
    results["jobs"] = jobs

    # Await recommendations
    results["recommendations"] = await recommendations_task

    if not jobs:
        logger.warning("[Pipeline] No jobs found — pipeline ending early.")
        results["matches"] = []
        results["cover_letters"] = []
        results["metadata"]["status"] = "completed_no_jobs"
        return results

    # Step 2b — Rank jobs by relevance
    ranked_jobs = await discovery_agent.rank_jobs(jobs, profile)
    results["jobs"] = ranked_jobs

    # Step 3 — Match top jobs
    logger.info("[Pipeline] Step 3/4: Matching candidate to jobs …")
    matches: list[dict[str, Any]] = []
    for job in ranked_jobs[:10]:
        match = await matching_agent.calculate_match(profile, job)
        match["job"] = job
        matches.append(match)

    matches.sort(key=lambda m: m.get("match_score", 0), reverse=True)
    results["matches"] = matches

    # Step 4 — Generate cover letters for top 3
    logger.info("[Pipeline] Step 4/4: Generating cover letters …")
    cover_letters: list[dict[str, Any]] = []
    top_matches = [m for m in matches if m.get("match_score", 0) >= 50][:3]
    if not top_matches:
        top_matches = matches[:3]

    for match in top_matches:
        job = match.get("job", {})
        cl = await cover_letter_agent.generate_cover_letter(profile, job)
        cl["job_title"] = job.get("title", "Unknown")
        cl["company"] = job.get("company", "Unknown")
        cl["match_score"] = match.get("match_score", 0)
        cover_letters.append(cl)

    results["cover_letters"] = cover_letters
    results["metadata"]["status"] = "completed"
    logger.info("[Pipeline] Pipeline finished — %d matches, %d cover letters.",
                len(matches), len(cover_letters))
    return results


def run_full_pipeline_sync(
    cv_text: str,
    job_query: str,
    location: str = "",
    filters: dict[str, Any] | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Synchronous wrapper around :func:`run_full_pipeline`.

    Convenience function for scripts and notebooks that don't have a
    running event loop.
    """
    return asyncio.run(
        run_full_pipeline(
            cv_text=cv_text,
            job_query=job_query,
            location=location,
            filters=filters,
            api_key=api_key,
            model=model,
        )
    )
