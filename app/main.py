from fastapi import FastAPI

# Import database components - uncomment create_all if needed for initial setup
# from .database import engine, Base
# from . import models # Ensure models are imported so Base knows about them

# Import routers
from .routers import auth as auth_router
from .routers import profile as profile_router
from .routers import applications as applications_router

# models.Base.metadata.create_all(bind=engine)

# Create FastAPI app instance
app = FastAPI(
    title="Job Application Automator API",
    description="API for automating job applications.",
    version="0.1.0",
)

# Include routers
app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(profile_router.router, prefix="/api/profile", tags=["User Profile"])
app.include_router(
    applications_router.router, prefix="/api/applications", tags=["Job Applications"]
)


# Root endpoint
@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint providing a welcome message.
    """
    return {"message": "Welcome to the Job Application Automator API"}


# --- Add other global configurations or middleware if needed ---
# Example: CORS middleware
# from fastapi.middleware.cors import CORSMiddleware
# origins = [
#     "http://localhost",
#     "http://localhost:8080", # Example frontend origin
# ]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
