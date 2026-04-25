import psycopg2
from minio import Minio
from insightface.app import FaceAnalysis
from config import settings
import threading

# MinIO Client
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False,
)

# Face Analysis App (Initialized as None for Lazy Loading)
_face_app = None
face_app_lock = threading.Lock()

def get_face_app():
    """Lazy loader for FaceAnalysis to save startup memory"""
    global _face_app
    with face_app_lock:
        if _face_app is None:
            print("Loading Face Analysis Model (buffalo_s)...")
            _face_app = FaceAnalysis(
                name="buffalo_s",  # FORCED small model
                providers=["CPUExecutionProvider"],
            )
            _face_app.prepare(ctx_id=-1, det_size=(320, 320))
        return _face_app

# Camera State
camera = None
camera_lock = threading.Lock()
stream_active = False
known_faces = []


def get_db_connection():
    """Get database connection"""
    if settings.DATABASE_URL:
        return psycopg2.connect(settings.DATABASE_URL)
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
