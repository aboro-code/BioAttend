import cv2
import psycopg2
import numpy as np
import io
import uuid
from minio import Minio
from insightface.app import FaceAnalysis

# --- 1. CONFIGURATION ---
# Detection Confidence Threshold (from your PRD)
CONF_THRESHOLD = 0.85 

app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

minio_client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadminpassword",
    secure=False
)

def get_db_connection():
    return psycopg2.connect(host="localhost", database="face_recognition", user="admin", password="password123")

# --- 2. STREAMLINED REGISTRATION ---
def enroll_student():
    cap = cv2.VideoCapture(0)
    print("ENROLLMENT MODE: Press 's' to Save current face, or 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret: break

        # A. Detect faces for visual feedback
        faces = app.get(frame)
        
        for face in faces:
            bbox = face.bbox.astype(int)
            score = face.det_score
            # Color turns green if quality is high enough for registration
            color = (0, 255, 0) if score > CONF_THRESHOLD else (0, 0, 255)
            
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            cv2.putText(frame, f"Quality: {score:.2f}", (bbox[0], bbox[1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Enrollment - Press 's' to Register", frame)
        key = cv2.waitKey(1) & 0xFF

        # B. Registration Logic (on 's' key)
        if key == ord('s') and len(faces) > 0:
            best_face = faces[0]
            
            if best_face.det_score < CONF_THRESHOLD:
                print("❌ Quality too low. Please adjust lighting or position.")
                continue

            name = input("Enter Student Name: ")
            if not name: continue

            # Extract data
            student_id = str(uuid.uuid4())
            embedding = best_face.normed_embedding.tolist()

            # Upload to MinIO (directly from memory)
            _, img_encoded = cv2.imencode('.jpg', frame)
            img_bytes = io.BytesIO(img_encoded.tobytes())
            
            minio_client.put_object(
                "student-photos", f"{student_id}.jpg", img_bytes,
                length=len(img_encoded.tobytes()), content_type="image/jpeg"
            )

            # Save to Postgres
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO students (id, name, embedding, photo_url) VALUES (%s, %s, %s, %s)",
                (student_id, name, embedding, f"student-photos/{student_id}.jpg")
            )
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✅ Registered {name} successfully!")

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    enroll_student()