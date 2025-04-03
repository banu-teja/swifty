import os
import os
import json
import shutil
import datetime
from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles  # Add StaticFiles import
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List

# Define the directory for uploads relative to this script
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
DATA_DIR = os.path.dirname(__file__)  # Save JSON in job_ui directory

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Job UI Form Handler",
    description="Simple API to handle job application form submissions from job_ui/index.html",
    version="0.1.0",
)

# Configure CORS to allow requests from the file:// protocol (local HTML file)
# or specific origins if hosted. Be cautious with "*" in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "null",
        "http://localhost",
        "http://127.0.0.1",
    ],  # "null" for file:// origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files - Serve files from the current directory (".") under "/static" path
# html=True is not needed here as we are not serving from root
app.mount("/static", StaticFiles(directory="."), name="static")


@app.post("/api/submit-application")  # Change path to /api/submit-application
async def submit_application(
    fullName: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    position: str = Form(...),
    # startDate: Optional[str] = Form(None), # Removed from form
    salary: Optional[str] = Form(None),
    linkedin: Optional[str] = Form(None),
    portfolio: Optional[str] = Form(None),
    experience: Optional[int] = Form(None),
    comments: Optional[str] = Form(None),
    resume: UploadFile = File(...),
    coverLetter: Optional[UploadFile] = File(None),
):
    """
    Receives job application data, saves uploaded files, and stores form data as JSON.
    """
    application_data = {
        "fullName": fullName,
        "email": email,
        "phone": phone,
        "position": position,
        # "startDate": startDate, # Removed from form
        "salary": salary,
        "linkedin": linkedin,
        "portfolio": portfolio,
        "experience": experience,
        "comments": comments,
        "resume": None,
        "coverLetter": None,
        "submissionTimestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }

    # --- Handle Resume File ---
    if resume and resume.filename:
        # Sanitize filename (basic example)
        safe_resume_filename = os.path.basename(resume.filename)
        resume_path = os.path.join(
            UPLOAD_DIR,
            f"{datetime.datetime.utcnow().timestamp()}_{safe_resume_filename}",
        )
        try:
            with open(resume_path, "wb") as buffer:
                shutil.copyfileobj(resume.file, buffer)
            application_data["resume"] = resume_path  # Store the path
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Could not save resume file: {e}"
            )
        finally:
            await resume.close()  # Close the file handle
    else:
        raise HTTPException(status_code=400, detail="Resume file is required.")

    # --- Handle Cover Letter File (Optional) ---
    if coverLetter and coverLetter.filename:
        safe_cl_filename = os.path.basename(coverLetter.filename)
        cl_path = os.path.join(
            UPLOAD_DIR, f"{datetime.datetime.utcnow().timestamp()}_{safe_cl_filename}"
        )
        try:
            with open(cl_path, "wb") as buffer:
                shutil.copyfileobj(coverLetter.file, buffer)
            application_data["coverLetter"] = cl_path  # Store the path
        except Exception as e:
            # Log error but don't fail the whole request if cover letter fails
            print(f"Warning: Could not save cover letter file: {e}")
        finally:
            await coverLetter.close()  # Close the file handle

    # --- Save Application Data as JSON ---
    timestamp_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    json_filename = f"application_{timestamp_str}.json"
    json_filepath = os.path.join(DATA_DIR, json_filename)

    try:
        with open(json_filepath, "w") as f:
            json.dump(application_data, f, indent=2)
    except Exception as e:
        # If JSON saving fails, we might want to clean up saved files, but for simplicity:
        raise HTTPException(
            status_code=500, detail=f"Could not save application data as JSON: {e}"
        )

    return {
        "message": "Application submitted successfully!",
        "application_file": json_filename,
    }


# Basic root endpoint for testing
@app.get("/")
async def root():
    return {"message": "Job UI Form Handler is running."}


# To run this server:
# cd job_ui
# uvicorn server:app --reload --port 8001
# Then access the UI at http://localhost:8001/static/index.html
