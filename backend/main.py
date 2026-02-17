"""
BioAttend - Face Recognition Attendance System
Main FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from dependencies import known_faces
from utils.database import load_all_students

# Import routers
from routers import camera, students, attendance

# Initialize FastAPI app
app = FastAPI(
    title="BioAttend AI Backend",
    description="Face Recognition Attendance System",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Load known faces on startup"""
    global known_faces
    known_faces = load_all_students()
    print("🚀 BioAttend Backend Started")


# Include routers
app.include_router(camera.router)
app.include_router(students.router)
app.include_router(attendance.router)


# Health check
@app.get("/")
async def root():
    return {"message": "BioAttend API", "status": "running", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
