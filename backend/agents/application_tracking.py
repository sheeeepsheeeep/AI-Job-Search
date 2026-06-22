"""
Application Tracking Agent

Tracks job applications, computes statistics, generates strategic
insights, and identifies applications that need follow-up.
"""

from __future__ import annotations

import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

INSIGHTS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a career strategist analysing a candidate's job-application "
                "history. Based on the applications data and the candidate profile, "
                "provide strategic insights.\n\n"
                "Return ONLY valid JSON — no markdown fences:\n"
                "{{\n"
                '  "summary": "High-level 3-5 sentence assessment",\n'
                '  "patterns": [\n'
                '    "Observed pattern or trend 1",\n'
                '    "Observed pattern or trend 2"\n'
                "  ],\n"
                '  "strengths": ["What is working well 1", ...],\n'
                '  "weaknesses": ["What could be improved 1", ...],\n'
                '  "recommendations": [\n'
                '    "Actionable recommendation 1",\n'
                '    "Actionable recommendation 2"\n'
                "  ],\n"
                '  "target_companies": ["Company A", ...],\n'
                '  "suggested_roles": ["Role title 1", ...]\n'
                "}}"
            ),
        ),
        (
            "human",
            (
                "Candidate profile:\n{profile_json}\n\n"
                "Application statistics:\n{stats_json}\n\n"
                "Recent applications (last 20):\n{applications_json}"
            ),
        ),
    ]
)


class ApplicationTrackingAgent:
    """Tracks, analyses, and provides strategic insights on applications."""

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
            temperature=0.3,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_statistics(
        self, applications: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Compute descriptive statistics from a list of application dicts.

        Each application dict is expected to have at least:
        ``status``, ``applied_date``, and optionally ``response_date``.

        Returns a dict with keys: total, by_status, response_rate,
        avg_response_time_days, weekly_rate, most_applied_companies.
        """
        total = len(applications)
        if total == 0:
            return {
                "total": 0,
                "by_status": {},
                "response_rate": 0.0,
                "avg_response_time_days": 0.0,
                "weekly_rate": 0.0,
                "most_applied_companies": [],
            }

        # Status counts
        status_counter: Counter[str] = Counter()
        for app in applications:
            status_counter[app.get("status", "unknown")] += 1

        # Response rate
        responded_statuses = {"interview", "offered", "rejected", "accepted"}
        responded = sum(
            1
            for app in applications
            if app.get("status", "").lower() in responded_statuses
        )
        response_rate = round((responded / total) * 100, 1)

        # Average response time
        response_times: list[float] = []
        for app in applications:
            applied = self._parse_date(app.get("applied_date"))
            response = self._parse_date(app.get("response_date"))
            if applied and response and response >= applied:
                delta = (response - applied).total_seconds() / 86400
                response_times.append(delta)

        avg_response_time = (
            round(sum(response_times) / len(response_times), 1)
            if response_times
            else 0.0
        )

        # Weekly application rate
        dates = [
            self._parse_date(app.get("applied_date"))
            for app in applications
        ]
        valid_dates = sorted(d for d in dates if d is not None)
        if len(valid_dates) >= 2:
            span_days = max((valid_dates[-1] - valid_dates[0]).days, 1)
            weekly_rate = round(total / (span_days / 7), 1)
        else:
            weekly_rate = float(total)

        # Most applied companies
        company_counter: Counter[str] = Counter()
        for app in applications:
            company = app.get("company", "Unknown")
            if company:
                company_counter[company] += 1
        most_applied = [
            {"company": name, "count": count}
            for name, count in company_counter.most_common(5)
        ]

        stats = {
            "total": total,
            "by_status": dict(status_counter),
            "response_rate": response_rate,
            "avg_response_time_days": avg_response_time,
            "weekly_rate": weekly_rate,
            "most_applied_companies": most_applied,
        }
        logger.info("Computed stats for %d applications.", total)
        return stats

    async def generate_insights(
        self,
        applications: list[dict[str, Any]],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        """Use LLM to analyse application patterns and provide strategy.

        Returns a dict with keys: summary, patterns, strengths,
        weaknesses, recommendations, target_companies, suggested_roles.
        """
        stats = await self.get_statistics(applications)

        chain = INSIGHTS_PROMPT | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "profile_json": json.dumps(profile, default=str),
                    "stats_json": json.dumps(stats, default=str),
                    "applications_json": json.dumps(
                        applications[:20], default=str
                    ),
                }
            )
            insights = self._parse_json(response.content)  # type: ignore[union-attr]
            logger.info("Generated insights for %d applications.", len(applications))
            return insights
        except Exception as exc:
            logger.error("Insight generation failed: %s", exc)
            return {
                "summary": f"Unable to generate insights: {exc}",
                "patterns": [],
                "strengths": [],
                "weaknesses": [],
                "recommendations": ["Review your application history manually."],
                "target_companies": [],
                "suggested_roles": [],
            }

    async def suggest_follow_ups(
        self,
        applications: list[dict[str, Any]],
        days_threshold: int = 7,
    ) -> list[dict[str, Any]]:
        """Identify applications that need a follow-up.

        An application is flagged when:
        * Status is ``applied`` or ``pending``.
        * More than *days_threshold* days have passed since ``applied_date``.
        * No ``follow_up_date`` is recorded.
        """
        now = datetime.now(timezone.utc)
        follow_ups: list[dict[str, Any]] = []

        for app in applications:
            status = (app.get("status") or "").lower()
            if status not in ("applied", "pending"):
                continue

            applied_date = self._parse_date(app.get("applied_date"))
            if applied_date is None:
                continue

            days_since = (now - applied_date).days
            if days_since < days_threshold:
                continue

            if app.get("follow_up_date"):
                continue

            follow_ups.append(
                {
                    "id": app.get("id"),
                    "job_title": app.get("job_title", "Unknown"),
                    "company": app.get("company", "Unknown"),
                    "contact_email": app.get("contact_email"),
                    "applied_date": str(applied_date.date()),
                    "days_since_applied": days_since,
                    "urgency": (
                        "high" if days_since > 14 else "medium"
                    ),
                }
            )

        follow_ups.sort(key=lambda x: x["days_since_applied"], reverse=True)
        logger.info("Identified %d applications due for follow-up.", len(follow_ups))
        return follow_ups

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(value: Any) -> datetime | None:
        """Best-effort date parsing."""
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, str):
            for fmt in (
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ):
                try:
                    dt = datetime.strptime(value, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
        return None

    @staticmethod
    def _parse_json(text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -len("```")]
        return json.loads(cleaned.strip())
