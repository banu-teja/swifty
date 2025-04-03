import time
import logging
import asyncio  # Import asyncio
from sqlalchemy.orm import Session
from typing import Optional, Any, Union


from app.services.browser import execute_browser, ApplicationStatus

from .celery_app import celery_app
from ..database import SessionLocal  # Import the session factory
from sqlalchemy.orm import joinedload
from .. import crud, models, schemas  # Import crud functions, models, and schemas

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 1. Define the recursive conversion function
def stringify_values(data: Any) -> Any:
    """Recursively converts all values in a dict or list to strings."""
    if isinstance(data, dict):
        # If it's a dictionary, apply recursively to each value
        return {k: stringify_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        # If it's a list, apply recursively to each element
        return [stringify_values(item) for item in data]
    elif data is None:
        # Decide how to handle None (e.g., empty string or 'None')
        return ""  # Or return "None" if you prefer
    else:
        # Base case: convert the value to string
        return str(data)


@celery_app.task(bind=True)
def process_application_placeholder(self, application_id: int):
    """
    Placeholder task to process a job application.
    - Fetches the application from the DB.
    - Updates status to QUEUED initially.
    - Simulates some processing time.
    - In a real scenario, this task would:
        1. Update status to PROCESSING.
        2. Use web scraping/automation tools (like Selenium, Playwright, or requests-html)
           to navigate to the job_url.
        3. Parse the application form fields.
        4. Fetch the user's profile data.
        5. Fill the form fields.
        6. Handle potential errors (PARSING_FAILED, FILLING_FAILED).
        7. Update status to NEEDS_REVIEW or SUBMITTED (or SUBMISSION_FAILED).
        8. Store extracted job title/company.
    """
    logger.info(f"Received task for application ID: {application_id}")
    db: Session = SessionLocal()  # Create a new session for this task
    try:
        # 1. Fetch Application and User Profile Data
        logger.info(f"Fetching data for application ID: {application_id}")
        application = (
            db.query(models.JobApplication)
            .options(
                joinedload(models.JobApplication.owner).joinedload(models.User.profile)
            )  # Eager load owner and profile
            .filter(models.JobApplication.id == application_id)
            .first()
        )

        if not application:
            logger.error(f"Application ID: {application_id} not found in DB.")
            return  # Exit if application not found

        if not application.owner or not application.owner.profile:
            logger.error(
                f"User or User Profile not found for application ID: {application_id}"
            )
            crud.update_job_application_status(
                db,
                application_id,
                models.JobApplicationStatus.PROCESSING_FAILED,
                error_message="User profile data missing.",
            )
            return  # Exit if profile data is missing

        user_profile_data = schemas.UserProfile.model_validate(
            application.owner.profile
        )
        job_url = application.job_url

        # 2. Update Status to PROCESSING
        crud.update_job_application_status(
            db, application_id, models.JobApplicationStatus.PROCESSING
        )
        logger.info(f"Application ID: {application_id} status updated to PROCESSING.")

        # --- START: Your Automation Logic ---
        logger.info(
            f"Starting automation for application ID: {application_id} at URL: {job_url}"
        )
        automation_success = False
        automation_error_message = None
        extracted_title = None
        extracted_company = None
        needs_review = False

        try:
            # TODO: Implement your browser automation logic here (e.g., using Playwright, Selenium, browser-use)
            # You have access to:
            # - job_url: The URL of the job application page (string)
            # - user_profile_data: The user's profile information (Pydantic model: schemas.UserProfile)
            #   Access fields like: user_profile_data.first_name, user_profile_data.email (via application.owner.email),
            #   user_profile_data.work_experience (list of dicts/WorkExperienceItem),
            #   user_profile_data.education (list of dicts/EducationItem),
            #   user_profile_data.skills (list), user_profile_data.resume_path (string), etc.

            user_original = user_profile_data.model_dump()
            user_stringified = stringify_values(user_original)

            # Run the async function using asyncio.run()
            result_model = asyncio.run(
                execute_browser(
                    task="Fill and submit the job application",
                    link=job_url,
                    sensitive_data=user_stringified,
                )
            )
            print(user_profile_data)

            logger.info(f"Simulating automation steps for {job_url}...")
            # Example: Simulate parsing and filling
            time.sleep(10)  # Replace with actual browser interaction time

            # Example: Simulate extracting data from the job page
            extracted_title = result_model.job_title
            extracted_company = result_model.job_company

            # Example: Simulate successful form submission
            automation_success = result_model.is_success
            logger.info(
                f"Simulated successful submission for application ID: {application_id}"
            )

            # Example: Or simulate a case where user review is needed
            # needs_review = True
            # logger.info(f"Simulated application needs review for ID: {application_id}")

            # Example: Or simulate a failure during filling
            # raise ValueError("Could not find the submit button")

        except Exception as auto_error:
            logger.error(
                f"Automation failed for application ID {application_id}: {auto_error}",
                exc_info=True,
            )
            automation_success = False
            automation_error_message = f"Automation Error: {str(auto_error)}"
            # Determine specific failure status based on error type if needed
            # e.g., if parsing failed vs. filling failed

        # --- END: Your Automation Logic ---

        # 3. Update Application Status and Details based on automation outcome
        final_status = (
            models.JobApplicationStatus.SUBMISSION_FAILED
        )  # Default to failure
        if automation_success:
            if needs_review:
                final_status = models.JobApplicationStatus.NEEDS_REVIEW
            else:
                final_status = models.JobApplicationStatus.SUBMITTED
        elif automation_error_message:
            # You could map specific errors to PARSING_FAILED, FILLING_FAILED etc.
            final_status = models.JobApplicationStatus.FILLING_FAILED  # Example

        crud.update_job_application_status(
            db,
            application_id,
            final_status,
            error_message=automation_error_message,  # Store error if any
        )
        logger.info(
            f"Application ID: {application_id} final status updated to {final_status.value}."
        )

        # Update extracted details if available
        if extracted_title or extracted_company:
            crud.update_job_application_details(
                db,
                application_id,
                title=extracted_title,
                company=extracted_company,
            )
            logger.info(
                f"Updated extracted details for application ID: {application_id}."
            )

    except Exception as e:
        # General error handling for issues outside the automation block (e.g., DB connection)
        logger.error(
            f"Error processing application ID {application_id}: {e}", exc_info=True
        )
        # Update status to a failure state
        try:
            # Check if application still exists before updating status
            application_exists = (
                db.query(models.JobApplication.id)
                .filter(models.JobApplication.id == application_id)
                .scalar()
                is not None
            )
            if application_exists:
                crud.update_job_application_status(
                    db,
                    application_id,
                    models.JobApplicationStatus.PROCESSING_FAILED,
                    error_message=str(e),
                )  # Or a more specific error status
                logger.warning(
                    f"Application ID: {application_id} status updated to PROCESSING_FAILED due to error."
                )
            else:
                logger.error(
                    f"Application ID: {application_id} not found when trying to log error status."
                )
        except Exception as db_error:
            logger.error(
                f"Failed to update error status for application ID {application_id}: {db_error}",
                exc_info=True,
            )
            # Handle potential issues writing the error status back to the DB
        # Optional: Retry the task based on the exception type
        # raise self.retry(exc=e, countdown=60) # Example retry after 60 seconds
    finally:
        db.close()  # Ensure the session is closed


# You can add more tasks here as needed, e.g., tasks for sending notifications, etc.
