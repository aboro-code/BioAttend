import cv2
import psycopg2
import numpy as np
from insightface.app import FaceAnalysis
from datetime import datetime

# --- 1. CONFIGURATION ---
THRESHOLD = 0.45  # Minimum similarity score to be considered a match
LOG_INTERVAL_MINUTES = 60 # Only log attendance once every hour

app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

def get_db_connection():
    return psycopg2.connect(
        host="localhost", 
        database="face_recognition", 
        user="admin", 
        password="password123"
    )

# --- 2. ATTENDANCE LOGGING LOGIC ---
def log_attendance(student_id, student_name, conn):
    """Logs attendance to the DB only if the last log was > LOG_INTERVAL_MINUTES ago."""
    try:
        cur = conn.cursor()
        
        # Check for recent logs
        cur.execute("""
            SELECT log_time FROM attendance_logs 
            WHERE student_id = %s 
            AND log_time > NOW() - INTERVAL '%s minutes'
            ORDER BY log_time DESC LIMIT 1;
        """, (student_id, LOG_INTERVAL_MINUTES))
        
        already_logged = cur.fetchone()

        if not already_logged:
            cur.execute(
                "INSERT INTO attendance_logs (student_id, status) VALUES (%s, %s)",
                (student_id, 'Present')
            )
            conn.commit()
            print(f">>> ATTENDANCE RECORDED: {student_name} at {datetime.now().strftime('%H:%M:%S')}")
        
        cur.close()
    except Exception as e:
        print(f"Logging Error: {e}")
        conn.rollback()

# --- 3. RECOGNITION LOGIC ---
def recognize_face():
    cap = cv2.VideoCapture(0)
    print("Starting Real-Time Recognition... Press 'q' or 'esc' to quit.")

    # Open connection once at the start
    conn = get_db_connection()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret: 
                break

            # A. Detect faces (Using RTX 4060)
            faces = app.get(frame)

            for face in faces:
                embedding = face.normed_embedding.tolist()
                
                # B. Search PostgreSQL for the closest match
                cur = conn.cursor()
                
                # 1 - (embedding <=> %s) calculates Cosine Similarity
                cur.execute("""
                    SELECT id, name, 1 - (embedding <=> %s::vector) AS similarity 
                    FROM students 
                    ORDER BY similarity DESC 
                    LIMIT 1;
                """, (embedding,))
                
                result = cur.fetchone()
                cur.close()

                # C. Determine if it's a match
                name = "Unknown"
                color = (0, 0, 255) # Red for unknown
                
                if result and result[2] > THRESHOLD:
                    student_id = result[0]
                    student_name = result[1]
                    similarity = result[2]
                    
                    name = f"{student_name} ({similarity:.2f})"
                    color = (0, 255, 0) # Green for match
                    
                    # D. Attempt to log attendance
                    log_attendance(student_id, student_name, conn)

                # E. Draw on the frame
                bbox = face.bbox.astype(int)
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                cv2.putText(frame, name, (bbox[0], bbox[1] - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

            # Show the video feed
            cv2.imshow("RTX 4060 Attendance System", frame)

            # Exit keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

    finally:
        # Cleanup
        print("Closing connections...")
        cap.release()
        cv2.destroyAllWindows()
        conn.close()

if __name__ == "__main__":
    recognize_face()