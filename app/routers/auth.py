from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from .. import crud, schemas, auth, models
from ..database import get_db
from ..config import settings

router = APIRouter()


@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    - Checks if a user with the same email already exists.
    - Hashes the password before storing.
    - Creates an associated empty UserProfile.
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    new_user = crud.create_user(db=db, user=user)
    return new_user


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Authenticate user and return a JWT access token.
    - Uses OAuth2PasswordRequestForm for standard username/password form data.
    - Verifies user existence and password.
    - Creates an access token.
    """
    user = crud.get_user_by_email(
        db, email=form_data.username
    )  # form_data.username is the email
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Get the details of the currently authenticated user.
    """
    # The dependency get_current_active_user already fetches and validates the user
    return current_user


# Add logout endpoint if using session-based auth or token blocklisting.
# For simple JWT, logout is typically handled client-side by deleting the token.
