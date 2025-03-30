import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB  # Use JSONB for PostgreSQL

from .database import Base


# --- Enums ---
class JobApplicationStatus(enum.Enum):
    RECEIVED = "RECEIVED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    PARSING_FAILED = "PARSING_FAILED"
    FILLING_FAILED = "FILLING_FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    SUBMITTED = "SUBMITTED"
    SUBMISSION_FAILED = "SUBMISSION_FAILED"


# --- Models ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    applications = relationship(
        "JobApplication", back_populates="owner", cascade="all, delete-orphan"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    phone = Column(String, nullable=True)
    address = Column(JSONB, nullable=True)  # Flexible structure for address
    linkedin_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    resume_path = Column(String, nullable=True)  # Path/reference to stored resume

    # Using JSONB for structured but flexible data
    work_experience = Column(JSONB, nullable=True)  # List of work experiences
    education = Column(JSONB, nullable=True)  # List of education entries
    skills = Column(JSONB, nullable=True)  # List or object of skills
    common_qna = Column(JSONB, nullable=True)  # {"question_hash": "answer"}

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="profile")


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_url = Column(String, nullable=False, index=True)
    status = Column(
        Enum(JobApplicationStatus),
        default=JobApplicationStatus.RECEIVED,
        nullable=False,
    )
    submission_timestamp = Column(DateTime(timezone=True), nullable=True)
    extracted_job_title = Column(String, nullable=True)
    extracted_company_name = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="applications")

    # Consider adding a unique constraint for (owner_id, job_url) if needed
    # from sqlalchemy import UniqueConstraint
    # __table_args__ = (UniqueConstraint('owner_id', 'job_url', name='_owner_job_uc'),)
