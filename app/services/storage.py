import logging
import uuid
from google.cloud import storage
from google.api_core.exceptions import NotFound
from fastapi import UploadFile, HTTPException, status
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize GCS client
# Authentication is typically handled by the environment (GOOGLE_APPLICATION_CREDENTIALS)
# or Application Default Credentials (ADC) when running on GCP.
try:
    storage_client = storage.Client()
    bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
except NotFound as e:
    logger.error(f"Failed to initialize GCS client or bucket: {e}")
    # Depending on the application's needs, you might want to raise an error
    # or handle this case gracefully if GCS is optional for some operations.
    storage_client = None
    bucket = None
except Exception as e:
    logger.error(f"Unexpected error initializing GCS: {e}")
    storage_client = None
    bucket = None


async def upload_file_to_gcs(
    file: UploadFile, user_id: int, destination_folder: str = settings.GCS_RESUME_FOLDER
) -> Optional[str]:
    """
    Uploads a file to Google Cloud Storage.

    Args:
        file: The file uploaded via FastAPI's UploadFile.
        user_id: The ID of the user uploading the file, used for path structuring.
        destination_folder: The base folder within the GCS bucket.

    Returns:
        The full GCS path (gs://bucket/folder/filename) of the uploaded file, or None if upload fails.
    """
    if not bucket or not storage_client:
        logger.error("GCS bucket not initialized. Cannot upload file.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service is not configured or available.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided."
        )

    # Create a unique filename to avoid collisions
    file_extension = file.filename.split(".")[-1] if "." in file.filename else ""
    unique_filename = (
        f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
    )

    # Construct the full path in GCS
    blob_name = f"{destination_folder}/{user_id}/{unique_filename}"
    blob = bucket.blob(blob_name)

    try:
        # Read file content asynchronously
        content = await file.read()
        # Upload the file content
        blob.upload_from_string(content, content_type=file.content_type)
        logger.info(f"File {file.filename} uploaded to GCS as {blob_name}")

        # Return the GCS URI (gs://bucket-name/path/to/blob)
        return f"gs://{settings.GCS_BUCKET_NAME}/{blob_name}"

    except NotFound as e:
        logger.error(f"GCS Upload Error for {blob_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to storage: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during GCS upload for {blob_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during file upload.",
        )
    finally:
        # Ensure the file cursor is closed if applicable (FastAPI handles this for UploadFile)
        await file.close()
