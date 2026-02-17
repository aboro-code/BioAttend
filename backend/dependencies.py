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

# Face Analysis App
face_app = FaceAnalysis(
    name=settings.FACE_MODEL,
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
)
face_app.prepare(ctx_id=0, det_size=settings.DETECTION_SIZE)

# Camera State
camera = None
camera_lock = threading.Lock()
stream_active = False
known_faces = []


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=settings.DB_HOST,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
