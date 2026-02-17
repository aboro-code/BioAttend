import cv2
import time
import numpy as np
import dependencies  # Import the entire module to maintain global state sync
from services.attendance_service import log_attendance


def force_release_camera():
    """Aggressively release camera with multiple attempts"""
    # Use the module reference to modify the global variables
    with dependencies.camera_lock:
        dependencies.stream_active = False

        if dependencies.camera is not None:
            try:
                dependencies.camera.release()
                print("📷 Camera released (attempt 1)")
            except Exception as e:
                print(f"Release error 1: {e}")

            time.sleep(0.3)

            try:
                if dependencies.camera:
                    dependencies.camera.release()
                    print("📷 Camera released (attempt 2)")
            except Exception as e:
                print(f"Release error 2: {e}")

            dependencies.camera = None
            time.sleep(0.5)
            print("✅ Camera fully released")


def generate_video_frames():
    """Generate video frames with face recognition using shared dependencies"""

    # --- 🚀 CRITICAL FIX: LAZY LOAD STUDENTS IF LIST IS EMPTY ---
    from utils.database import load_all_students

    if not dependencies.known_faces:
        print("🔄 Camera service detected empty faces list. Syncing now...")
        dependencies.known_faces = load_all_students()
    # -----------------------------------------------------------

    with dependencies.camera_lock:
        if dependencies.camera is None or not dependencies.camera.isOpened():
            dependencies.camera = cv2.VideoCapture(0)
            dependencies.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        dependencies.stream_active = True

    # This should now print "Checking against 1 faces"
    print(f"📹 Stream started. Checking against {len(dependencies.known_faces)} faces.")

    try:
        while dependencies.stream_active:
            with dependencies.camera_lock:
                if dependencies.camera is None or not dependencies.stream_active:
                    break
                success, frame = dependencies.camera.read()

            if not success:
                break

            faces = dependencies.face_app.get(frame)

            for face in faces:
                bbox = face.bbox.astype(int)
                live_embedding = face.embedding
                name, max_score = "Unknown", 0.0

                for known in dependencies.known_faces:
                    # Cosine Similarity
                    score = np.dot(live_embedding, known["embedding"]) / (
                        np.linalg.norm(live_embedding)
                        * np.linalg.norm(known["embedding"])
                    )

                    # Using your 0.20 threshold for testing
                    if score > 0.20 and score > max_score:
                        max_score, name = score, known["name"]

                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

                # Show name and score for debugging
                label = f"{name} ({max_score:.2f})"
                cv2.putText(
                    frame,
                    label,
                    (bbox[0], bbox[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

                if name != "Unknown":
                    log_attendance(name)

            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
            time.sleep(0.01)

    except GeneratorExit:
        print("📺 Web client disconnected")
    finally:
        force_release_camera()
