# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Set PLAYWRIGHT_BROWSERS_PATH to a writable location within the container
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright

# Set the working directory in the container
WORKDIR /app

# Install curl (needed by Playwright installer sometimes)
# Clean up apt cache afterwards
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser(s) and their dependencies
# This command downloads the browser binaries and installs necessary system libs
RUN playwright install --with-deps chromium

# Copy the rest of the application code into the container at /app
COPY . .

# The command to run the application will be specified in docker-compose.yml
# Example for web: CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# Example for worker: CMD ["celery", "-A", "app.worker.celery_app", "worker", "--loglevel=info"]
