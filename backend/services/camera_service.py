import cv2
import time
import numpy as np
import dependencies  # Global state sync
from services.attendance_service import log_attendance
from utils.database import load_all_students  # Import the loader


def force_release_camera():
    """Aggressively release camera with multiple attempts"""
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
                # Double check to ensure release
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

    # --- 🚀 ALWAYS SYNC ON START ---
    # We refresh every time the stream is requested to catch new enrollments
    print("🔄 Syncing known faces from database...")
    dependencies.known_faces = load_all_students()
    # -------------------------------

    with dependencies.camera_lock:
        if dependencies.camera is None or not dependencies.camera.isOpened():
            # Open default camera
            dependencies.camera = cv2.VideoCapture(0)
            # Prevent frame lag
            dependencies.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        dependencies.stream_active = True

    print(f"📹 Stream started. Checking against {len(dependencies.known_faces)} faces.")

    try:
        while dependencies.stream_active:
            with dependencies.camera_lock:
                if dependencies.camera is None or not dependencies.stream_active:
                    break
                success, frame = dependencies.camera.read()

            if not success:
                print("❌ Failed to grab frame")
                break

            # AI Detection
            faces = dependencies.face_app.get(frame)

            for face in faces:
                bbox = face.bbox.astype(int)
                live_embedding = face.embedding
                name, max_score = "Unknown", 0.0

                # Recognition Loop
                for known in dependencies.known_faces:
                    # Cosine Similarity Calculation
                    # Formula: (A . B) / (||A|| * ||B||)
                    score = np.dot(live_embedding, known["embedding"]) / (
                        np.linalg.norm(live_embedding)
                        * np.linalg.norm(known["embedding"])
                    )

                    # Threshold logic (0.35 is recommended, 0.20 is very loose for testing)
                    if score > 0.35 and score > max_score:
                        max_score, name = score, known["name"]

                # UI Feedback
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

                # Draw Box
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

                # Draw Label with Score for debugging
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

                # Log to DB if recognized
                if name != "Unknown":
                    log_attendance(name)

            # Encode for Web
            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )

            # Small delay to prevent CPU maxing out
            time.sleep(0.01)

    except GeneratorExit:
        print("📺 Web client disconnected from stream")
    except Exception as e:
        print(f"Streaming Error: {e}")
    finally:
        # Ensure camera is freed for other processes/enrollment
        force_release_camera()
