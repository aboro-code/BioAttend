import cv2
import time
import numpy as np
import dependencies  # Global state sync
from services.attendance_service import log_attendance
from utils.database import load_all_students  # Import the loader


def force_release_camera():
    with dependencies.camera_lock:
        dependencies.stream_active = False

        if dependencies.camera is not None:
            try:
                dependencies.camera.release()
                print("Camera released successfully")
            except Exception as e:
                print(f"Camera release error: {e}")
            finally:
                # Ensure the variable is reset even if release() throws an error
                dependencies.camera = None

        # A single short sleep is enough to let the OS hardware bus reset
        time.sleep(0.5)
        print("Camera system reset")


def generate_video_frames():
    """Generate video frames with face recognition using shared dependencies"""

    print("Syncing known faces from database...")
    dependencies.known_faces = load_all_students()

    with dependencies.camera_lock:
        if dependencies.camera is None or not dependencies.camera.isOpened():
            dependencies.camera = cv2.VideoCapture(0)
            dependencies.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        dependencies.stream_active = True

    print(f"Stream started. Checking against {len(dependencies.known_faces)} faces.")

    try:
        while dependencies.stream_active:
            with dependencies.camera_lock:
                if dependencies.camera is None or not dependencies.stream_active:
                    break
                success, frame = dependencies.camera.read()

            if not success:
                print("Failed to grab frame")
                break

            faces = dependencies.face_app.get(frame)

            for face in faces:
                bbox = face.bbox.astype(int)
                live_embedding = face.embedding
                name, max_score = "Unknown", 0.0

                # Recognition Loop
                for known in dependencies.known_faces:
                    # Cosine Similarity Calculation
                    score = np.dot(live_embedding, known["embedding"]) / (
                        np.linalg.norm(live_embedding)
                        * np.linalg.norm(known["embedding"])
                    )

                    if score > 0.45 and score > max_score:
                        max_score, name = score, known["name"]

                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

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

            # Small delay to prevent CPU maxing out
            time.sleep(0.01)

    except GeneratorExit:
        print("Web client disconnected from stream")
    except Exception as e:
        print(f"Streaming Error: {e}")
    finally:
        force_release_camera()
