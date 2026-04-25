from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # ============= DATABASE =============
    DB_HOST: str = "localhost"
    DB_NAME: str = "face_recognition"
    DB_USER: str = "admin"
    DB_PASSWORD: str = "password123"
    DB_PORT: int = 5432

    # ============= MINIO =============
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadminpassword"
    MINIO_BUCKET: str = "student-photos"
    MINIO_SECURE: bool = False

    # ============= FACE RECOGNITION =============
    RECOGNITION_THRESHOLD: float = 0.45
    DETECTION_SIZE: tuple = (640, 640)
    FACE_MODEL: str = "buffalo_l"

    # ============= SESSION MANAGEMENT =============
    OTP_LENGTH: int = 6
    DEFAULT_GEOFENCE_RADIUS_METERS: int = 50

    # ============= LOCATION VERIFICATION =============
    # Score-based system (total must be >= 70)
    SCORE_GPS_MATCH: int = 60
    SCORE_DEVICE_LEGITIMATE: int = 40
    MINIMUM_VERIFICATION_SCORE: int = 70

    # ============= LIVENESS DETECTION =============
    LIVENESS_ENABLED: bool = True
    BLINK_THRESHOLD: float = 0.25  # EAR threshold for blink detection
    MINIMUM_BLINKS_REQUIRED: int = 2
    HEAD_ROTATION_THRESHOLD_DEGREES: int = 20
    LIVENESS_VIDEO_DURATION_SECONDS: int = 3
    LIVENESS_FPS: int = 30

    # ============= SECURITY =============
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ============= API =============
    CORS_ORIGINS: List[str] = ["*"]
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_URL: Optional[str] = "http://localhost:3000"  # NEW

    # ============= RATE LIMITING =============
    RATE_LIMIT_ENROLLMENT: str = "5/minute"
    RATE_LIMIT_ATTENDANCE: str = "10/minute"
    RATE_LIMIT_SESSION_CREATE: str = "10/hour"

    class Config:
        case_sensitive = True
        env_file = ".env"


# Create global settings instance
settings = Settings()


# Validation on startup
def validate_settings():
    """Validate critical settings"""
    assert settings.OTP_LENGTH == 6, "OTP must be 6 digits"
    assert (
        settings.RECOGNITION_THRESHOLD > 0 and settings.RECOGNITION_THRESHOLD < 1
    ), "Threshold must be between 0 and 1"
    assert settings.MINIMUM_VERIFICATION_SCORE <= 100, "Score cannot exceed 100"
    assert (
        settings.SCORE_GPS_MATCH
        + settings.SCORE_DEVICE_LEGITIMATE
    ) >= settings.MINIMUM_VERIFICATION_SCORE, (
        "Maximum possible score must meet minimum requirement"
    )

    print("Configuration validated successfully")


# Validate on import
validate_settings()
