import cv2
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from minio import Minio
import pandas as pd
import io
import json
from datetime import datetime
from insightface.app import FaceAnalysis
import base64
import time
import threading
import uuid


app = FastAPI(title="VisionGuard AI Backend")

# --- 1. CONFIGURATION ---
minio_client = Minio(
    "localhost:9000", 
    access_key="minioadmin", 
    secret_key="minioadminpassword", 
    secure=False
)

# Initialize AI
face_app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(640, 640))

# Global states
camera = None
camera_lock = threading.Lock()
stream_active = False
known_faces = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    return psycopg2.connect(
        host="localhost", 
        database="face_recognition", 
        user="admin", 
        password="password123"
    )

# --- 2. CAMERA MANAGER ---
def force_release_camera():
    """Aggressively release camera with multiple attempts"""
    global camera, stream_active
    
    with camera_lock:
        stream_active = False  # Signal streaming to stop
        
        if camera is not None:
            try:
                camera.release()
                print("📷 Camera released (attempt 1)")
            except:
                pass
            
            # Wait a moment for OS to process
            time.sleep(0.3)
            
            # Second release attempt (for Windows stubbornness)
            try:
                camera.release()
                print("📷 Camera released (attempt 2)")
            except:
                pass
            
            camera = None
            
            # Additional wait for Windows to fully release hardware
            time.sleep(0.5)
            print("✅ Camera fully released for frontend")

# --- 3. DATA LOADERS ---
@app.on_event("startup")
def load_known_faces():
    global known_faces
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT name, embedding FROM students")
        rows = cur.fetchall()
        
        known_faces = []
        for row in rows:
            emb_str = row['embedding']
            if isinstance(emb_str, str):
                clean_str = emb_str.replace("np.str_('", "").replace("')", "")
                emb_list = json.loads(clean_str)
                embedding = np.array(emb_list).astype(np.float32)
            else:
                embedding = np.array(emb_str).astype(np.float32)
            known_faces.append({"name": row['name'], "embedding": embedding})
            
        cur.close()
        conn.close()
        print(f"✅ Loaded {len(known_faces)} students.")
    except Exception as e:
        print(f"❌ Startup Error: {e}")

# --- 4. CORE LOGIC ---
def log_attendance(student_name):
    now = datetime.now()
    today = now.date()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM students WHERE name = %s", (student_name,))
        res = cur.fetchone()
        if res:
            student_id = res[0]
            cur.execute("""
                SELECT id FROM attendance_logs 
                WHERE student_id = %s AND log_time::date = %s
            """, (student_id, today))
            existing = cur.fetchone()
            if existing:
                cur.execute("UPDATE attendance_logs SET log_time = %s WHERE id = %s", (now, existing[0]))
            else:
                cur.execute("INSERT INTO attendance_logs (student_id, status, log_time) VALUES (%s, 'Present', %s)", (student_id, now))
            conn.commit()
        cur.close()
        conn.close()
    except Exception as e: 
        print(f"❌ DB Error: {e}")

def gen_frames():
    global camera, stream_active
    
    with camera_lock:
        if camera is None or not camera.isOpened():
            camera = cv2.VideoCapture(0)
            # Windows-specific: set buffer size to 1 for faster release
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        stream_active = True
    
    print("📹 Stream started")
    
    try:
        while stream_active:
            with camera_lock:
                if camera is None or not stream_active:
                    break
                success, frame = camera.read()
            
            if not success:
                break
            
            faces = face_app.get(frame)
            for face in faces:
                bbox = face.bbox.astype(int)
                live_embedding = face.embedding
                name, max_score = "Unknown", 0.0
                
                for known in known_faces:
                    score = np.dot(live_embedding, known['embedding']) / (
                        np.linalg.norm(live_embedding) * np.linalg.norm(known['embedding'])
                    )
                    if score > 0.45 and score > max_score:
                        max_score, name = score, known['name']
                
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                cv2.putText(frame, f"{name}", (bbox[0], bbox[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                if name != "Unknown": 
                    log_attendance(name)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    except GeneratorExit:
        print("📺 Client disconnected")
    finally:
        force_release_camera()

# --- 5. ENDPOINTS ---

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.post("/camera/release")
async def release_camera_endpoint():
    """Explicit endpoint to force camera release"""
    force_release_camera()
    return {"status": "Camera released", "timestamp": datetime.now().isoformat()}

@app.get("/camera/status")
async def camera_status():
    """Check if backend camera is active"""
    global stream_active
    return {
        "active": stream_active,
        "camera_object_exists": camera is not None
    }

@app.get("/attendance/today")
async def get_today_attendance():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT s.name, a.status, TO_CHAR(a.log_time, 'HH12:MI AM') as time 
        FROM attendance_logs a 
        JOIN students s ON a.student_id = s.id 
        WHERE a.log_time::date = CURRENT_DATE 
        ORDER BY a.log_time DESC
    """)
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

@app.get("/students")
async def get_all_students():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, name, photo_url FROM students ORDER BY name ASC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

@app.get("/photo/{photo_name}")
async def get_student_photo(photo_name: str):
    try:
        response = minio_client.get_object("student-photos", photo_name)
        return Response(content=response.read(), media_type="image/jpeg")
    except:
        return {"error": "Photo not found"}

@app.post("/enroll")
async def enroll_student(data: dict):
    # Ensure camera is released
    force_release_camera()
    
    # Extra wait for Windows
    time.sleep(0.5)
    
    try:
        name = data.get("name")
        image_data = data.get("image").split(",")[1]
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        faces = face_app.get(img)
        if not faces:
            return {"success": False, "message": "No face detected"}
        
        embedding = faces[0].embedding.tolist()
        
        # Generate UUID for student
        import uuid
        student_id = str(uuid.uuid4())
        
        photo_name = f"{student_id}.jpg"  # Use UUID as filename for uniqueness
        
        # Save to MinIO
        _, encoded_img = cv2.imencode('.jpg', img)
        minio_client.put_object(
            "student-photos", photo_name, 
            io.BytesIO(encoded_img.tobytes()), len(encoded_img.tobytes()), 
            "image/jpeg"
        )

        # Save to DB with ID
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO students (id, name, embedding, photo_url) VALUES (%s, %s, %s, %s)",
            (student_id, name, json.dumps(embedding), photo_name)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        load_known_faces()  # Update memory
        return {"success": True, "message": f"Registered {name}!"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    
    
@app.get("/attendance/export")
async def export_attendance():
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT s.name, a.status, a.log_time 
        FROM attendance_logs a 
        JOIN students s ON a.student_id = s.id 
        ORDER BY a.log_time DESC;
    """, conn)
    conn.close()
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    return StreamingResponse(
        iter([stream.getvalue()]), 
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance.csv"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)