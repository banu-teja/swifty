# Swifty - Job Application Automator API

## Description

Swifty is a backend API designed to streamline the job application process. It allows users to store their application details (resume info, experience, education, etc.) and then submit job posting URLs. The system queues these applications for automated processing (currently a placeholder, intended for integration with browser automation tools like Playwright or Selenium).

This project is built with Python using the FastAPI framework, SQLAlchemy for database interaction with PostgreSQL, Celery for background task processing, and Redis as the message broker.

## Features

- **User Authentication:** Secure user registration and login using JWT tokens.
- **Profile Management:** Store and manage detailed user profile information necessary for job applications (e.g., contact info, work experience, education, skills, resume path). Uses PostgreSQL's JSONB for flexible data storage.
- **Job Application Submission:** Submit job posting URLs via a dedicated API endpoint.
- **Background Processing:** Applications are queued and processed asynchronously using Celery workers.
- **Status Tracking:** Monitor the status of each submitted job application (e.g., Received, Queued, Processing, Needs Review, Submitted, Failed).
- **Database Migrations:** Uses Alembic to manage database schema changes.
- **Dockerized:** Includes `Dockerfile` and `docker-compose.yml` for easy setup and deployment.

## Technology Stack

- **Backend Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Asynchronous Tasks:** Celery
- **Message Broker:** Redis
- **Authentication:** python-jose (JWT), passlib (bcrypt)
- **Validation:** Pydantic
- **Containerization:** Docker, Docker Compose
- **Language:** Python 3

## Setup and Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/banu-teja/swifty.git
    cd swifty
    ```

2.  **Environment Variables:**

    - Create a `.env` file in the project root directory.
    - Populate it with necessary environment variables based on `app/config.py`. Key variables include:
      - `DATABASE_URL` (e.g., `postgresql://user:password@db:5432/appdb`)
      - `SECRET_KEY` (for JWT)
      - `ALGORITHM` (e.g., `HS256`)
      - `ACCESS_TOKEN_EXPIRE_MINUTES` (e.g., `30`)
      - `CELERY_BROKER_URL` (e.g., `redis://redis:6379/0`)
      - `CELERY_RESULT_BACKEND` (e.g., `redis://redis:6379/0`)
    - _Ensure the database name, user, and password match your PostgreSQL setup or Docker Compose configuration._

3.  **Option A: Using Docker (Recommended)**

    - Make sure you have Docker and Docker Compose installed.
    - Build and run the services:
      ```bash
      docker-compose up --build -d
      ```
    - Apply database migrations:
      ```bash
      docker-compose exec api alembic upgrade head
      ```

4.  **Option B: Manual Setup (Requires Python 3.8+, PostgreSQL, Redis)**
    - Create and activate a virtual environment:
      ```bash
      python -m venv venv
      source venv/bin/activate # On Windows use `venv\Scripts\activate`
      ```
    - Install dependencies:
      ```bash
      pip install -r requirements.txt
      ```
    - Ensure PostgreSQL and Redis servers are running and accessible.
    - Apply database migrations:
      ```bash
      alembic upgrade head
      ```

## Running the Application

- **Using Docker:**

  - The application (API, worker, database, Redis) will be running after `docker-compose up`.
  - API accessible at `http://localhost:8000` (or the port mapped in `docker-compose.yml`).
  - API docs (Swagger UI) at `http://localhost:8000/docs`.
  - API docs (ReDoc) at `http://localhost:8000/redoc`.

- **Manual Setup:**
  - **Run FastAPI API Server:**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
  - **Run Celery Worker:**
    ```bash
    celery -A app.worker.celery_app worker --loglevel=info
    ```

## API Endpoints Overview

- **Authentication (`/auth`)**
  - `POST /token`: Login and get JWT token.
  - `POST /register`: Create a new user.
- **User Profile (`/api/profile`)**
  - `GET /`: Get the current user's profile details.
  - `PUT /`: Update the current user's profile details.
- **Job Applications (`/api/applications`)**
  - `POST /`: Submit a new job application URL.
  - `GET /`: List all job applications for the current user.
  - `GET /{application_id}`: Get details of a specific job application.

## Project Status & Tasks

- [x] User Authentication (Register, Login, JWT)
- [x] User Profile Model (Flexible JSONB storage)
- [x] User Profile CRUD Operations
- [x] User Profile API Endpoints (`GET`, `PUT`)
- [x] Job Application Model (Status tracking)
- [x] Job Application CRUD Operations
- [x] Job Application API Endpoints (`POST`, `GET`)
- [x] Celery Setup (Worker, Broker integration)
- [x] Background Task Placeholder for Application Processing
- [x] Database Migrations (Alembic setup)
- [x] Docker Configuration (`Dockerfile`, `docker-compose.yml`)
- [ ] **Implement Browser Automation Logic:** Replace the placeholder in `app/worker/tasks.py` with actual web scraping/form filling using Playwright, Selenium, or similar tools.
- [ ] **Error Handling & Retries:** Enhance error handling within the Celery task for specific automation failures.
- [ ] **Frontend UI:** Develop a user interface to interact with the API (A basic UI exists in `job_ui/` but may need expansion).
- [ ] **Testing:** Add comprehensive unit and integration tests.
- [ ] **Security Enhancements:** Review security aspects (input validation, dependency checks, etc.).
- [ ] **Deployment Strategy:** Define a clear deployment process for production.

## License

This project is licensed under the [MIT License](LICENSE).
