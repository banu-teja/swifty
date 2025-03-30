from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas, models, auth
from ..database import get_db

# Import the placeholder task - adjust path if needed when worker is fully defined
from ..worker.tasks import process_application_placeholder

router = APIRouter()


@router.post(
    "/", response_model=schemas.JobApplication, status_code=status.HTTP_201_CREATED
)
async def submit_job_application(
    application_in: schemas.JobApplicationCreate,
    background_tasks: BackgroundTasks,  # Use BackgroundTasks for simple cases, or integrate Celery directly
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Submit a new job application URL.
    - Creates a JobApplication record with RECEIVED status.
    - Adds a background task to process the application.
    """
    # Optional: Check if the user has already submitted this exact URL
    # existing_app = db.query(models.JobApplication).filter(
    #     models.JobApplication.owner_id == current_user.id,
    #     models.JobApplication.job_url == str(application_in.job_url) # Ensure URL comparison is robust
    # ).first()
    # if existing_app:
    #     raise HTTPException(
    #         status_code=status.HTTP_409_CONFLICT,
    #         detail="Application for this URL already submitted."
    #     )

    # Create the application entry in the database
    db_application = crud.create_job_application(
        db=db, application=application_in, owner_id=current_user.id
    )

    # Trigger the background task (Celery integration)
    # Use .delay() for Celery tasks
    process_application_placeholder.delay(db_application.id)

    # Alternatively, using FastAPI's BackgroundTasks for simpler, non-distributed tasks:
    # background_tasks.add_task(process_application_placeholder, db_application.id)
    # Note: BackgroundTasks run in the same process, not suitable for long-running or CPU-intensive tasks.
    # Celery is the better choice here as intended by the project setup.

    return db_application


@router.get("/", response_model=List[schemas.JobApplication])
def list_job_applications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Retrieve a list of job applications submitted by the current user.
    """
    applications = crud.get_job_applications_by_user(
        db, owner_id=current_user.id, skip=skip, limit=limit
    )
    return applications


@router.get("/{application_id}", response_model=schemas.JobApplication)
def read_job_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Retrieve the details of a specific job application by its ID.
    Ensures the application belongs to the current user.
    """
    db_application = crud.get_job_application(
        db, application_id=application_id, owner_id=current_user.id
    )
    if db_application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job application not found"
        )
    return db_application


# Potential future endpoints:
# DELETE /{application_id}: Cancel/delete an application (if allowed)
# POST /{application_id}/review: Endpoint for user to review and confirm submission after automated filling
