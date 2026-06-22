"""
Interview Preparation Agent

Generates tailored interview questions, evaluates candidate answers,
and produces overall performance feedback.
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

QUESTION_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a senior interview coach. Generate exactly 10 interview "
                "questions tailored to the job listing and candidate profile.\n\n"
                "Interview type: {interview_type}\n\n"
                "For HR / behavioural interviews, focus on:\n"
                "• Behavioural questions (STAR format)\n"
                "• Situational / hypothetical scenarios\n"
                "• Cultural fit and soft-skill assessment\n"
                "• Motivation and career-goal alignment\n\n"
                "For Technical interviews, focus on:\n"
                "• Coding and problem-solving questions\n"
                "• System design and architecture\n"
                "• Domain-specific knowledge\n"
                "• Debugging and optimisation scenarios\n\n"
                "Return ONLY a valid JSON array of 10 objects — no markdown fences:\n"
                "[\n"
                "  {{\n"
                '    "question": "The interview question",\n'
                '    "difficulty": "easy | medium | hard",\n'
                '    "category": "e.g. behavioural, system_design, coding ...",\n'
                '    "tips": "Advice on how to answer this question well"\n'
                "  }}\n"
                "]"
            ),
        ),
        (
            "human",
            (
                "Job listing:\n{job_json}\n\n"
                "Candidate profile:\n{profile_json}"
            ),
        ),
    ]
)

ANSWER_EVALUATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a strict but fair interview evaluator. "
                "Evaluate the candidate's answer to an interview question.\n\n"
                "Return ONLY valid JSON — no markdown fences:\n"
                "{{\n"
                '  "score": <int 1-10>,\n'
                '  "feedback": "Detailed constructive feedback",\n'
                '  "ideal_answer": "What an ideal answer would look like",\n'
                '  "strengths": ["strength1", ...],\n'
                '  "improvements": ["improvement1", ...]\n'
                "}}\n\n"
                "Scoring guide:\n"
                "9-10: Exceptional — demonstrates deep expertise and clarity.\n"
                "7-8: Strong — well-structured with good examples.\n"
                "5-6: Adequate — covers basics but lacks depth or specifics.\n"
                "3-4: Below average — vague, missing key points.\n"
                "1-2: Poor — irrelevant or fundamentally incorrect."
            ),
        ),
        (
            "human",
            (
                "Job context:\n{job_context_json}\n\n"
                "Question: {question}\n\n"
                "Candidate's answer:\n{answer}"
            ),
        ),
    ]
)

OVERALL_FEEDBACK_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a senior interview coach providing a comprehensive "
                "debrief after a mock interview session.\n\n"
                "You will receive the list of questions, the candidate's answers, "
                "and the individual scores.\n\n"
                "Return ONLY valid JSON — no markdown fences:\n"
                "{{\n"
                '  "overall_score": <float 1.0-10.0>,\n'
                '  "summary": "A 3-5 sentence overall assessment",\n'
                '  "strengths": ["strength1", ...],\n'
                '  "weaknesses": ["weakness1", ...],\n'
                '  "recommendations": [\n'
                '    "Specific, actionable recommendation 1",\n'
                '    "Specific, actionable recommendation 2"\n'
                "  ]\n"
                "}}"
            ),
        ),
        (
            "human",
            (
                "Questions:\n{questions_json}\n\n"
                "Answers:\n{answers_json}\n\n"
                "Scores:\n{scores_json}"
            ),
        ),
    ]
)


class InterviewPrepAgent:
    """Generates questions, evaluates answers, and provides interview feedback."""

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
            temperature=0.5,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_questions(
        self,
        job_listing: dict[str, Any],
        candidate_profile: dict[str, Any],
        interview_type: str = "hr",
    ) -> list[dict[str, str]]:
        """Generate 10 interview questions tailored to the role.

        Parameters
        ----------
        job_listing:
            Job description / requirements.
        candidate_profile:
            Structured candidate profile.
        interview_type:
            ``"hr"`` for behavioural/situational or ``"technical"`` for
            coding/system-design questions.

        Returns a list of dicts with keys: question, difficulty, category, tips.
        """
        interview_type_label = (
            "HR / Behavioural" if interview_type.lower() in ("hr", "behavioral", "behavioural")
            else "Technical"
        )

        chain = QUESTION_GENERATION_PROMPT | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "interview_type": interview_type_label,
                    "job_json": json.dumps(job_listing, default=str),
                    "profile_json": json.dumps(candidate_profile, default=str),
                }
            )
            questions = self._parse_json(response.content)  # type: ignore[union-attr]
            if not isinstance(questions, list):
                questions = [questions]
            logger.info(
                "Generated %d %s questions for %s",
                len(questions),
                interview_type_label,
                job_listing.get("title", "unknown"),
            )
            return questions
        except Exception as exc:
            logger.error("Question generation failed: %s", exc)
            return [
                {
                    "question": "Tell me about yourself.",
                    "difficulty": "easy",
                    "category": "general",
                    "tips": "Keep it concise — 2 minutes, focused on relevant experience.",
                }
            ]

    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        job_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a single candidate answer.

        Returns a dict with keys: score, feedback, ideal_answer,
        strengths, improvements.
        """
        chain = ANSWER_EVALUATION_PROMPT | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "job_context_json": json.dumps(job_context, default=str),
                    "question": question,
                    "answer": answer,
                }
            )
            result = self._parse_json(response.content)  # type: ignore[union-attr]
            result["score"] = max(1, min(10, int(result.get("score", 5))))
            return result
        except Exception as exc:
            logger.error("Answer evaluation failed: %s", exc)
            return {
                "score": 5,
                "feedback": f"Evaluation could not be completed: {exc}",
                "ideal_answer": "",
                "strengths": [],
                "improvements": ["Unable to evaluate — please try again."],
            }

    async def generate_overall_feedback(
        self,
        questions: list[str],
        answers: list[str],
        scores: list[int],
    ) -> dict[str, Any]:
        """Produce an overall interview performance report.

        Returns a dict with keys: overall_score, summary, strengths,
        weaknesses, recommendations.
        """
        chain = OVERALL_FEEDBACK_PROMPT | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "questions_json": json.dumps(questions, default=str),
                    "answers_json": json.dumps(answers, default=str),
                    "scores_json": json.dumps(scores, default=str),
                }
            )
            result = self._parse_json(response.content)  # type: ignore[union-attr]
            result["overall_score"] = round(
                max(1.0, min(10.0, float(result.get("overall_score", 5.0)))), 1
            )
            return result
        except Exception as exc:
            logger.error("Overall feedback generation failed: %s", exc)
            avg = round(sum(scores) / max(len(scores), 1), 1)
            return {
                "overall_score": avg,
                "summary": f"Automatic summary unavailable ({exc}). "
                f"Average score: {avg}/10.",
                "strengths": [],
                "weaknesses": [],
                "recommendations": ["Review individual question feedback."],
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -len("```")]
        return json.loads(cleaned.strip())
