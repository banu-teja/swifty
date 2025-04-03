import asyncio
import logging
import os
import sys
import tempfile
import re  # For parsing GCS URI

# Standard library imports should generally come first, but this needs to run early.
from dotenv import load_dotenv

load_dotenv()

# Third-party imports
from browser_use import Agent, Browser, BrowserConfig, Controller, SystemPrompt
from browser_use.agent.views import ActionResult
from browser_use.browser.context import BrowserContext
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from google.cloud import storage  # Import GCS client
from google.cloud.exceptions import NotFound, GoogleCloudError

# TODO: Consider restructuring the project to avoid sys.path manipulation.
# This line assumes 'auto_apply.ipynb' is two levels up from the script's directory.
# If the project structure allows, relative imports or proper packaging are preferred.
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Commenting out if not needed


logger = logging.getLogger(__name__)


# --- GCS Helper Function ---
def download_gcs_file(gcs_uri: str) -> str:
    """Downloads a file from GCS to a temporary local path."""
    match = re.match(r"gs://([^/]+)/(.+)", gcs_uri)
    if not match:
        raise ValueError(f"Invalid GCS URI format: {gcs_uri}")

    bucket_name, blob_name = match.groups()
    logger.info(f"Attempting to download gs://{bucket_name}/{blob_name}")

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Create a temporary file to download into
        # Suffix helps identify the file type if needed, preserve original extension
        original_filename = os.path.basename(blob_name)
        suffix = (
            os.path.splitext(original_filename)[1] if "." in original_filename else None
        )
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix
        )  # Keep file after close initially

        logger.info(f"Downloading GCS file to temporary path: {temp_file.name}")
        blob.download_to_filename(temp_file.name)
        temp_file.close()  # Close the file handle
        logger.info(f"Successfully downloaded GCS file to {temp_file.name}")
        return temp_file.name  # Return the path

    except NotFound:
        logger.error(f"GCS file not found: {gcs_uri}")
        raise FileNotFoundError(f"GCS file not found: {gcs_uri}")
    except GoogleCloudError as e:
        logger.error(f"GCS download error for {gcs_uri}: {e}")
        raise ConnectionError(f"Failed to download from GCS: {e}")
    except Exception as e:
        logger.error(f"Unexpected error downloading {gcs_uri}: {e}")
        raise RuntimeError(f"Unexpected error during GCS download: {e}")


class ApplicationStatus(BaseModel):
    job_title: str
    job_company: str
    is_success: bool
    reason: str


controller = Controller(output_model=ApplicationStatus)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",  # gemini-2.5-pro-exp-03-25
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # other params...
)

config = BrowserConfig(headless=True, disable_security=True)

browser = Browser(config=config)


@controller.action(
    "Upload file to interactive element with file path ",
)
async def upload_file(
    index: int, path: str, browser: BrowserContext, available_file_paths: list[str]
):
    if path not in available_file_paths:
        return ActionResult(error=f"File path {path} is not available")

    if not os.path.exists(path):
        return ActionResult(error=f"File {path} does not exist")

    dom_el = await browser.get_dom_element_by_index(index)

    file_upload_dom_el = dom_el.get_file_upload_element()

    if file_upload_dom_el is None:
        msg = f"No file upload element found at index {index}"
        logger.info(msg)
        return ActionResult(error=msg)

    file_upload_el = await browser.get_locate_element(file_upload_dom_el)

    if file_upload_el is None:
        msg = f"No file upload element found at index {index}"
        logger.info(msg)
        return ActionResult(error=msg)

    try:
        await file_upload_el.set_input_files(path)
        msg = f"Successfully uploaded file to index {index}"
        logger.info(msg)
        return ActionResult(extracted_content=msg, include_in_memory=True)
    except Exception as e:
        msg = f"Failed to upload file to index {index}: {str(e)}"
        logger.info(msg)
        return ActionResult(error=msg)


class MySystemPrompt(SystemPrompt):
    """
    A SystemPrompt specifically designed for web browsing tasks,
    adding relevant instructions automatically via get_system_message.
    """

    # Define the specific message for this class
    _SPECIFIC_EXTENSION = "IMPORTANT RULE: Cancel the task if you can't find relevant data required to fill the application. But fill the details that you find relevant but do not submit."

    # Parent __init__ is sufficient here.

    def get_system_message(self):
        """
        Get the system prompt, appending specific task instructions.

        Returns:
            SystemMessage: Formatted system prompt with added instructions.
        """
        # 1. Get the original SystemMessage from the parent class method
        original_message = super().get_system_message()

        # 2. Get the content of the original message
        original_content = original_message.content

        # 3. Append the specific extension for this class
        extended_content = original_content + "\n\n" + self._SPECIFIC_EXTENSION

        # 4. Create and return a *new* SystemMessage with the extended content
        return SystemMessage(content=extended_content)


async def execute_browser(task, sensitive_data, link):
    initial_actions = [{"open_tab": {"url": link}}]
    temp_resume_path = None
    final_available_paths = []

    try:
        # Check for GCS resume path and download if necessary
        gcs_resume_uri = sensitive_data.get("resume_path")
        if gcs_resume_uri and gcs_resume_uri.startswith("gs://"):
            try:
                logger.info(f"Found GCS resume path: {gcs_resume_uri}. Downloading...")
                temp_resume_path = download_gcs_file(gcs_resume_uri)
                sensitive_data["resume_path"] = (
                    temp_resume_path  # Update sensitive data with temp path
                )
                final_available_paths = [temp_resume_path]
                logger.info(f"Using temporary resume path: {temp_resume_path}")
            except (FileNotFoundError, ConnectionError, ValueError, RuntimeError) as e:
                logger.warning(
                    f"Failed to download resume from GCS ({gcs_resume_uri}): {e}. Proceeding without resume."
                )
                # Keep sensitive_data['resume_path'] as the GCS URI or remove it?
                # Let's keep it as is, but ensure available_paths is empty.
                final_available_paths = []
            except Exception as e:
                logger.error(
                    f"Unexpected error processing GCS path {gcs_resume_uri}: {e}"
                )
                final_available_paths = []
        else:
            logger.info(
                "No GCS resume path found in sensitive data or path is not a GCS URI."
            )
            final_available_paths = (
                []
            )  # Ensure it's empty if no GCS path or download failed

        agent = Agent(
            task=task,
            initial_actions=initial_actions,
            controller=controller,
            llm=llm,
            browser=browser,
            retry_delay=20,
            max_actions_per_step=15,
            sensitive_data=sensitive_data,  # Now potentially contains the temp path
            available_file_paths=final_available_paths,  # Use the determined paths
            system_prompt_class=MySystemPrompt,
            # generate_gif=True,
        )

        result = await agent.run()
        res = result.final_result()
        parsed: ApplicationStatus = ApplicationStatus.model_validate_json(res)
        print(parsed)
        return parsed

    finally:
        # Clean up the temporary file if it was created
        if temp_resume_path and os.path.exists(temp_resume_path):
            try:
                os.remove(temp_resume_path)
                logger.info(
                    f"Successfully removed temporary resume file: {temp_resume_path}"
                )
            except OSError as e:
                logger.error(
                    f"Failed to remove temporary resume file {temp_resume_path}: {e}"
                )


if __name__ == "__main__":
    asyncio.run(
        execute_browser(
            "Complete the application",
            sensitive_data={
                "first_name": "magnus",
                "last_name": "Carlson",
                "email": "abc@cb.com",
                "phone": "1255532",
                "available_from": "April 5, 2025",
                "desired_salary": "20k $",
                "resume_path": "/home/xai/projects/ai-playground/browser/tmp.txt",
                "years_of_experience": "5",
            },
            link="http://localhost:8001/static/index.html",
        )
    )
