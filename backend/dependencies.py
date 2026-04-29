import psycopg2
from minio import Minio
from config import settings
import threading
import os

# MinIO Client (Safe Initialization)
try:
    minio_client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
except Exception as e:
    print(f"⚠️ MinIO not available: {e}. Photo uploads will be skipped.")
    minio_client = None

# Face Analysis App (Initialized as None for Lazy Loading)
_face_app = None
face_app_lock = threading.Lock()

def get_face_app():
    """Lazy loader for FaceAnalysis with extreme memory optimizations"""
    global _face_app
    from insightface.app import FaceAnalysis
    import onnxruntime as ort
    import gc

    with face_app_lock:
        if _face_app is None:
            print("Loading Face Analysis Model (buffalo_s) with memory optimizations...")
            
            # Force ONNX to use less memory
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["MKL_NUM_THREADS"] = "1"
            
            _face_app = FaceAnalysis(
                name="buffalo_s",
                root="~/.insightface",
                providers=["CPUExecutionProvider"],
                allowed_modules=['detection', 'recognition', 'landmark_2d_106']
            )
            
            # Prepare with minimal detection size
            _face_app.prepare(ctx_id=-1, det_size=(320, 320))
            
            # Garbage collect after loading models
            gc.collect()
            print("✅ Model loaded successfully.")
            
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
