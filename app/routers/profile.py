from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, models, auth
from ..database import get_db

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


# Consider adding a PATCH endpoint if strict PATCH semantics are preferred over PUT for partial updates.
# FastAPI typically handles partial updates gracefully with PUT when using Pydantic models with optional fields.
