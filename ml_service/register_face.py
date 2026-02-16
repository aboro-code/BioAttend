import cv2
import psycopg2
from minio import Minio
from insightface.app import FaceAnalysis
import io
import uuid

# --- 1. CONFIGURATION ---
app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider'])
# Creates face analysis engine using buffalo_l model
# Uses CUDAExecutionProvider to run on CUDA GPU
app.prepare(ctx_id=0, det_size=(640, 640))
# ctx_id=0 means use GPU 0 (first GPU)
# det_size=(640, 640) is the detection resolution

# MinIO Client (Storage)
minio_client = Minio(
    "localhost:9000",  # MinIO server address
    access_key="minioadmin",  # Username
    secret_key="minioadminpassword",  # Password
    secure=False  # Not using HTTPS (fine for local development)
)
# This creates a client to store photos in MinIO (object storage)

# PostgreSQL Connection (Database)
def get_db_connection():
    return psycopg2.connect(
        host="localhost", # database is on same machine 
        database="face_recognition", #DB name
        user="admin",
        password="password123" 
    )

# --- 2. INITIALIZATION ---
def init_storage():
    # Create MinIO Bucket if missing
    if not minio_client.bucket_exists("student-photos"):
        minio_client.make_bucket("student-photos")
        print("📁 Created bucket: student-photos")

    # Create Database Table if missing
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            embedding vector(512),
            photo_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("🗄️ Database table initialized.")

# --- 3. REGISTRATION LOGIC ---
def register_student(name, image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Error: Could not find image at {image_path}")
        return

    # A. Use 4060 to extract the Face Embedding
    faces = app.get(img)
    if len(faces) == 0:
        print(f"❌ No face detected in {image_path}. Try another photo.")
        return
    
    # We take the most prominent face
    embedding = faces[0].normed_embedding.tolist()
    student_id = str(uuid.uuid4())
    file_extension = image_path.split('.')[-1]
    object_name = f"{student_id}.{file_extension}"

    # B. Upload Photo to MinIO
    _, img_encoded = cv2.imencode(f'.{file_extension}', img)
    img_bytes = io.BytesIO(img_encoded.tobytes())
    minio_client.put_object(
        "student-photos", 
        object_name, 
        img_bytes, 
        length=len(img_encoded.tobytes()), 
        content_type="image/jpeg"
    )

    # C. Save Data to PostgreSQL
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (id, name, embedding, photo_url) VALUES (%s, %s, %s, %s)",
        (student_id, name, embedding, f"student-photos/{object_name}")
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ SUCCESS: {name} registered with ID {student_id}")

if __name__ == "__main__":
    init_storage()
    register_student("Rongu", "rongu.jpg")