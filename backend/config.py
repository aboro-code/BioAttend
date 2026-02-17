"""
Application configuration
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DB_HOST: str = "localhost"
    DB_NAME: str = "face_recognition"
    DB_USER: str = "admin"
    DB_PASSWORD: str = "password123"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadminpassword"
    MINIO_BUCKET: str = "student-photos"

    # Face Recognition
    RECOGNITION_THRESHOLD: float = 0.45
    DETECTION_SIZE: tuple = (640, 640)
    FACE_MODEL: str = "buffalo_l"

    # API
    CORS_ORIGINS: list = ["*"]

    class Config:
        case_sensitive = True


settings = Settings()
