"""
SQLAlchemy ORM models for the AI Job Search Agent.
All models use async-compatible column types and include full relationship definitions.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, relationship

from database.database import Base


# ---------------------------------------------------------------------------
# User & Session
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = Column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = Column(String, nullable=False)
    salt: Mapped[str] = Column(String, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, server_default=func.now())

    # Relationships
    profiles: Mapped[List["CandidateProfile"]] = relationship(
        "CandidateProfile", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="user", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[List["CoverLetter"]] = relationship(
        "CoverLetter", back_populates="user", cascade="all, delete-orphan"
    )
    job_matches: Mapped[List["JobMatch"]] = relationship(
        "JobMatch", back_populates="user", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="user", cascade="all, delete-orphan"
    )
    email_logs: Mapped[List["EmailLog"]] = relationship(
        "EmailLog", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = Column(String, primary_key=True)  # UUID token
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = Column(DateTime, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session(id='{self.id}', user_id={self.user_id})>"


# ---------------------------------------------------------------------------
# CandidateProfile
# ---------------------------------------------------------------------------

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String, nullable=False)
    email: Mapped[Optional[str]] = Column(String, nullable=True)
    phone: Mapped[Optional[str]] = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)  # list[str]
    education = Column(JSON, nullable=True)  # list[{degree, institution, year}]
    certifications = Column(JSON, nullable=True)  # list[str]
    experience = Column(JSON, nullable=True)  # list[{title, company, duration, description}]
    experience_years: Mapped[Optional[int]] = Column(Integer, nullable=True)
    summary: Mapped[Optional[str]] = Column(Text, nullable=True)
    cv_file_path: Mapped[Optional[str]] = Column(String, nullable=True)
    user_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = Column(DateTime, onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="profiles")
    job_matches: Mapped[List["JobMatch"]] = relationship(
        "JobMatch", back_populates="candidate", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="candidate", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[List["CoverLetter"]] = relationship(
        "CoverLetter", back_populates="candidate", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="candidate", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CandidateProfile(id={self.id}, name='{self.name}')>"


# ---------------------------------------------------------------------------
# JobListing
# ---------------------------------------------------------------------------

class JobListing(Base):
    __tablename__ = "job_listings"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = Column(String, nullable=False)
    company: Mapped[str] = Column(String, nullable=False)
    location: Mapped[Optional[str]] = Column(String, nullable=True)
    salary_range: Mapped[Optional[str]] = Column(String, nullable=True)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    requirements = Column(JSON, nullable=True)  # list[str]
    url: Mapped[Optional[str]] = Column(String, nullable=True)
    source: Mapped[Optional[str]] = Column(String, nullable=True)  # portal name
    remote_status: Mapped[Optional[str]] = Column(String, nullable=True)  # remote / hybrid / onsite
    industry: Mapped[Optional[str]] = Column(String, nullable=True)
    experience_level: Mapped[Optional[str]] = Column(String, nullable=True)
    date_found: Mapped[datetime] = Column(DateTime, server_default=func.now())

    # Relationships
    job_matches: Mapped[List["JobMatch"]] = relationship(
        "JobMatch", back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[List["CoverLetter"]] = relationship(
        "CoverLetter", back_populates="job", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<JobListing(id={self.id}, title='{self.title}', company='{self.company}')>"


# ---------------------------------------------------------------------------
# JobMatch
# ---------------------------------------------------------------------------

class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    job_id: Mapped[int] = Column(Integer, ForeignKey("job_listings.id"), nullable=False)
    match_score: Mapped[Optional[float]] = Column(Float, nullable=True)
    matching_skills = Column(JSON, nullable=True)  # list[str]
    missing_skills = Column(JSON, nullable=True)  # list[str]
    recommendations = Column(JSON, nullable=True)  # list[str]
    user_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="job_matches")
    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="job_matches"
    )
    job: Mapped["JobListing"] = relationship(
        "JobListing", back_populates="job_matches"
    )

    def __repr__(self) -> str:
        return f"<JobMatch(id={self.id}, score={self.match_score})>"


# ---------------------------------------------------------------------------
# CoverLetter
# ---------------------------------------------------------------------------

class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    job_id: Mapped[int] = Column(Integer, ForeignKey("job_listings.id"), nullable=False)
    content: Mapped[Optional[str]] = Column(Text, nullable=True)
    email_template: Mapped[Optional[str]] = Column(Text, nullable=True)
    pdf_path: Mapped[Optional[str]] = Column(String, nullable=True)
    user_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="cover_letters")
    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="cover_letters"
    )
    job: Mapped["JobListing"] = relationship(
        "JobListing", back_populates="cover_letters"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="cover_letter"
    )

    def __repr__(self) -> str:
        return f"<CoverLetter(id={self.id})>"


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    job_id: Mapped[int] = Column(Integer, ForeignKey("job_listings.id"), nullable=False)
    cover_letter_id: Mapped[Optional[int]] = Column(
        Integer, ForeignKey("cover_letters.id"), nullable=True
    )
    company_name: Mapped[str] = Column(String, nullable=False)
    job_title: Mapped[str] = Column(String, nullable=False)
    email_address: Mapped[Optional[str]] = Column(String, nullable=True)
    date_sent: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    status: Mapped[str] = Column(String, default="Applied")
    follow_up_date: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    user_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = Column(DateTime, onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="applications")
    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="applications"
    )
    job: Mapped["JobListing"] = relationship(
        "JobListing", back_populates="applications"
    )
    cover_letter: Mapped[Optional["CoverLetter"]] = relationship(
        "CoverLetter", back_populates="applications"
    )
    email_logs: Mapped[List["EmailLog"]] = relationship(
        "EmailLog", back_populates="application", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Application(id={self.id}, company='{self.company_name}', "
            f"status='{self.status}')>"
        )


# ---------------------------------------------------------------------------
# InterviewSession
# ---------------------------------------------------------------------------

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    job_id: Mapped[Optional[int]] = Column(
        Integer, ForeignKey("job_listings.id"), nullable=True
    )
    interview_type: Mapped[Optional[str]] = Column(String, nullable=True)  # 'hr' or 'technical'
    questions = Column(JSON, nullable=True)  # list[str]
    answers_json = Column(JSON, nullable=True)  # list[str] - raw answers stored as JSON
    scores = Column(JSON, nullable=True)  # list[{question, score, feedback}]
    overall_score: Mapped[Optional[float]] = Column(Float, nullable=True)
    feedback: Mapped[Optional[str]] = Column(Text, nullable=True)
    recommendations = Column(JSON, nullable=True)  # list[str]
    user_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="interview_sessions")
    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="interview_sessions"
    )
    job: Mapped[Optional["JobListing"]] = relationship(
        "JobListing", back_populates="interview_sessions"
    )
    answer_records: Mapped[List["InterviewAnswer"]] = relationship(
        "InterviewAnswer", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<InterviewSession(id={self.id}, type='{self.interview_type}', "
            f"score={self.overall_score})>"
        )


# ---------------------------------------------------------------------------
# EmailLog
# ---------------------------------------------------------------------------

class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("applications.id"), nullable=True)
    user_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("users.id"), nullable=True)
    email_type: Mapped[str] = Column(String, nullable=False, default="application")  # application / follow_up
    recipient: Mapped[str] = Column(String, nullable=False)
    subject: Mapped[Optional[str]] = Column(String, nullable=True)
    body: Mapped[Optional[str]] = Column(Text, nullable=True)
    status: Mapped[str] = Column(String, default="pending")  # pending / sent / failed
    sent_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = Column(Text, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="email_logs"
    )
    application: Mapped[Optional["Application"]] = relationship(
        "Application", back_populates="email_logs"
    )

    def __repr__(self) -> str:
        return f"<EmailLog(id={self.id}, type='{self.email_type}', status='{self.status}')>"


# ---------------------------------------------------------------------------
# InterviewAnswer
# ---------------------------------------------------------------------------

class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    question_index: Mapped[int] = Column(Integer, nullable=False)
    question_text: Mapped[Optional[str]] = Column(Text, nullable=True)
    answer: Mapped[Optional[str]] = Column(Text, nullable=True)
    score: Mapped[Optional[float]] = Column(Float, nullable=True)
    feedback: Mapped[Optional[str]] = Column(Text, nullable=True)
    ideal_answer: Mapped[Optional[str]] = Column(Text, nullable=True)
    strengths = Column(JSON, nullable=True)
    improvements = Column(JSON, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, server_default=func.now())

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="answer_records"
    )

    def __repr__(self) -> str:
        return f"<InterviewAnswer(id={self.id}, session={self.session_id}, q={self.question_index})>"
