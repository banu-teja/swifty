from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from typing import Optional

from .. import crud, schemas, models, auth
from ..database import get_db
from ..services.storage import upload_file_to_gcs  # Import the GCS upload service

router = APIRouter()


@router.get("/", response_model=schemas.UserProfile)
def read_user_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Retrieve the profile for the currently authenticated user.
    """
    profile = crud.get_user_profile(db, user_id=current_user.id)
    if profile is None:
        # This shouldn't happen if profile is created upon user registration
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found"
        )
    return profile


@router.put("/", response_model=schemas.UserProfile)
def update_user_profile(
    profile_update: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Update the profile for the currently authenticated user.
    Allows partial updates (PATCH-like behavior with PUT).
    """
    updated_profile = crud.update_user_profile(
        db, profile_update=profile_update, user_id=current_user.id
    )
    if updated_profile is None:
        # This might happen if the profile somehow didn't exist, though unlikely
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found, cannot update",
        )
    return updated_profile


@router.put("/resume", response_model=schemas.UserProfile)
async def upload_user_resume(
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Upload or replace the resume for the currently authenticated user.
    The resume is stored in GCS, and the path is saved in the user profile.
    """
    if not resume.content_type or not resume.content_type.startswith("application/pdf"):
        # Example: Restrict to PDF only. Adjust as needed.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF resumes are accepted.",
        )

    # Upload file to GCS
    gcs_resume_path = await upload_file_to_gcs(file=resume, user_id=current_user.id)

    if not gcs_resume_path:
        # The upload_file_to_gcs function raises HTTPException on failure,
        # but we add a check here for robustness.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get GCS path after upload.",
        )

    # Update the user profile with the new resume path
    profile_update = schemas.UserProfileUpdate(resume_path=gcs_resume_path)
    updated_profile = crud.update_user_profile(
        db, profile_update=profile_update, user_id=current_user.id
    )

    if updated_profile is None:
        # Should not happen if user exists and profile was created
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found, cannot update resume path.",
        )

    return updated_profile


# Consider adding a PATCH endpoint if strict PATCH semantics are preferred over PUT for partial updates.
# FastAPI typically handles partial updates gracefully with PUT when using Pydantic models with optional fields.
