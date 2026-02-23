from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime  # ADD THIS
from config import settings
from dependencies import known_faces
from utils.database import load_all_students

# Import routers
from routers import camera, students, attendance
from routers import sessions  # NEW

# Initialize FastAPI app
app = FastAPI(
    title="BioAttend AI Backend",
    description="Face Recognition Attendance System with Multi-Factor Verification",
    version="2.0.0",
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
    print("🚀 BioAttend Backend Started (v2.0.0 - Session-Based)")
    print(f"✅ Loaded {len(known_faces)} students")
    print(f"🔒 Multi-factor verification enabled")
    print(f"📍 Geofencing: {settings.DEFAULT_GEOFENCE_RADIUS_METERS}m radius")
    print(f"📱 QR refresh: Every {settings.QR_TOKEN_VALIDITY_SECONDS}s")


# Include routers
app.include_router(camera.router)
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(sessions.router)  # NEW


# Health check
@app.get("/")
async def root():
    return {
        "message": "BioAttend API v2.0",
        "status": "running",
        "version": "2.0.0",
        "features": {
            "session_based_attendance": True,
            "multi_factor_verification": True,
            "geofencing": True,
            "dynamic_qr": True,
            "liveness_detection": settings.LIVENESS_ENABLED,
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "students_loaded": len(known_faces),
        "active_sessions_count": "N/A",  # TODO: Add session count
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
