"""
AI Job Search Agent System — Agent Package

Exports all agent classes for the multi-agent job-search pipeline.
"""

from agents.cv_analysis import CVAnalysisAgent
from agents.job_discovery import JobDiscoveryAgent
from agents.job_matching import JobMatchingAgent
from agents.cover_letter import CoverLetterAgent
from agents.email_automation import EmailAutomationAgent
from agents.interview_prep import InterviewPrepAgent
from agents.application_tracking import ApplicationTrackingAgent

__all__ = [
    "CVAnalysisAgent",
    "JobDiscoveryAgent",
    "JobMatchingAgent",
    "CoverLetterAgent",
    "EmailAutomationAgent",
    "InterviewPrepAgent",
    "ApplicationTrackingAgent",
]
