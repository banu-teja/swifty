from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import HttpUrl  # Import HttpUrl

from . import models, schemas, auth  # Import auth for password hashing

# --- User CRUD ---


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # Automatically create an empty profile for the new user
    create_user_profile(db, schemas.UserProfileCreate(), user_id=db_user.id)
    db.refresh(db_user)  # Refresh again to load the profile relationship
    return db_user


# --- UserProfile CRUD ---


def get_user_profile(db: Session, user_id: int) -> Optional[models.UserProfile]:
    return (
        db.query(models.UserProfile)
        .filter(models.UserProfile.user_id == user_id)
        .first()
    )


def create_user_profile(
    db: Session, profile: schemas.UserProfileCreate, user_id: int
) -> models.UserProfile:
    # Ensure a profile doesn't already exist for this user
    existing_profile = get_user_profile(db, user_id)
    if existing_profile:
        # Handle error or return existing profile? For now, let's raise an error or update.
        # Let's update instead of erroring if called internally during user creation.
        return update_user_profile(db, profile, user_id)

    db_profile = models.UserProfile(
        **profile.model_dump(exclude_unset=True), user_id=user_id
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def update_user_profile(
    db: Session, profile_update: schemas.UserProfileUpdate, user_id: int
) -> Optional[models.UserProfile]:
    db_profile = get_user_profile(db, user_id)
    if db_profile:
        update_data = profile_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            # Convert HttpUrl to string before setting attribute
            if isinstance(value, HttpUrl):
                setattr(db_profile, key, str(value))
            else:
                setattr(db_profile, key, value)
        db.commit()
        db.refresh(db_profile)
    return db_profile


# --- JobApplication CRUD ---


def get_job_application(
    db: Session, application_id: int, owner_id: int
) -> Optional[models.JobApplication]:
    """Gets a specific application only if it belongs to the owner."""
    return (
        db.query(models.JobApplication)
        .filter(
            models.JobApplication.id == application_id,
            models.JobApplication.owner_id == owner_id,
        )
        .first()
    )


def get_job_applications_by_user(
    db: Session, owner_id: int, skip: int = 0, limit: int = 100
) -> List[models.JobApplication]:
    """Gets all applications for a specific user."""
    return (
        db.query(models.JobApplication)
        .filter(models.JobApplication.owner_id == owner_id)
        .order_by(models.JobApplication.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_job_application(
    db: Session, application: schemas.JobApplicationCreate, owner_id: int
) -> models.JobApplication:
    """Creates a new job application."""
    application_data = application.model_dump()
    # Convert HttpUrl to string before creating the model instance
    if "job_url" in application_data and isinstance(
        application_data["job_url"], HttpUrl
    ):
        application_data["job_url"] = str(application_data["job_url"])

    db_application = models.JobApplication(
        **application_data,
        owner_id=owner_id,
        status=models.JobApplicationStatus.RECEIVED  # Initial status
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application


def update_job_application_status(
    db: Session,
    application_id: int,
    status: models.JobApplicationStatus,
    error_message: Optional[str] = None,
) -> Optional[models.JobApplication]:
    """Updates the status and optionally an error message of a job application."""
    db_application = (
        db.query(models.JobApplication)
        .filter(models.JobApplication.id == application_id)
        .first()
    )
    if db_application:
        db_application.status = status
        if error_message:
            db_application.error_message = error_message
        # Potentially update submission timestamp if status is SUBMITTED
        if status == models.JobApplicationStatus.SUBMITTED:
            from datetime import datetime

            db_application.submission_timestamp = (
                datetime.utcnow()
            )  # Or use timezone aware if needed

        db.commit()
        db.refresh(db_application)
    return db_application


# Add other specific update functions as needed, e.g., for extracted data
def update_job_application_details(
    db: Session,
    application_id: int,
    title: Optional[str] = None,
    company: Optional[str] = None,
) -> Optional[models.JobApplication]:
    db_application = (
        db.query(models.JobApplication)
        .filter(models.JobApplication.id == application_id)
        .first()
    )
    if db_application:
        if title:
            db_application.extracted_job_title = title
        if company:
            db_application.extracted_company_name = company
        db.commit()
        db.refresh(db_application)
    return db_application
