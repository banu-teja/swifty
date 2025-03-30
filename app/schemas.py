from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import enum

from .models import JobApplicationStatus  # Import enum from models


# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    # profile: Optional['UserProfile'] = None # Avoid circular dependency if needed later

    class Config:
        # Pydantic V1: orm_mode = True
        # Pydantic V2: from_attributes = True
        from_attributes = True


# --- UserProfile Schemas ---
# Define structures for nested JSON data if desired, or use Dict/Any
class WorkExperienceItem(BaseModel):
    title: str
    company: str
    start_date: str  # Or date/datetime
    end_date: Optional[str] = None  # Or date/datetime
    description: Optional[str] = None


class EducationItem(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_date: str  # Or date/datetime
    end_date: Optional[str] = None  # Or date/datetime


class UserProfileBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Dict[str, Any]] = (
        None  # Example: {"street": "123 Main St", "city": "Anytown", ...}
    )
    linkedin_url: Optional[HttpUrl] = None
    portfolio_url: Optional[HttpUrl] = None
    resume_path: Optional[str] = None
    work_experience: Optional[List[WorkExperienceItem]] = None
    education: Optional[List[EducationItem]] = None
    skills: Optional[List[str]] = None  # Or Dict[str, List[str]] for categories
    common_qna: Optional[Dict[str, str]] = None  # {"question_hash_or_text": "answer"}


class UserProfileCreate(UserProfileBase):
    # No extra fields needed for creation initially, inherits all optional fields
    pass


class UserProfileUpdate(UserProfileBase):
    # Allows partial updates, all fields are optional
    pass


class UserProfile(UserProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Update User schema to include profile after UserProfile is defined
# User.model_rebuild() # Pydantic V2
# User.update_forward_refs() # Pydantic V1


# --- JobApplication Schemas ---
class JobApplicationBase(BaseModel):
    job_url: HttpUrl


class JobApplicationCreate(JobApplicationBase):
    pass  # Only job_url is needed to create


class JobApplicationUpdate(BaseModel):
    # Fields that might be updated internally by the worker
    status: Optional[JobApplicationStatus] = None
    submission_timestamp: Optional[datetime] = None
    extracted_job_title: Optional[str] = None
    extracted_company_name: Optional[str] = None
    error_message: Optional[str] = None


class JobApplication(JobApplicationBase):
    id: int
    owner_id: int
    status: JobApplicationStatus
    submission_timestamp: Optional[datetime] = None
    extracted_job_title: Optional[str] = None
    extracted_company_name: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        # Pydantic V2 needs this to serialize Enum correctly
        use_enum_values = True
