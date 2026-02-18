from fastapi import APIRouter, Response
from typing import List
import uuid
import json
import io
import cv2
from dependencies import get_db_connection, minio_client, known_faces
from models.schemas import (
    EnrollRequest,
    EnrollResponse,
    StudentResponse,
    DeleteResponse,
)
from services.face_service import detect_face_from_base64
from services.camera_service import force_release_camera
from utils.database import load_all_students
from psycopg2.extras import RealDictCursor
import time

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=List[StudentResponse])
async def get_all_students():
    """Get all registered students"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, name, photo_url FROM students ORDER BY name ASC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res


@router.post("/enroll", response_model=EnrollResponse)
async def enroll_student(data: EnrollRequest):
    """Enroll a new student"""
    global known_faces

    # Release camera first
    force_release_camera()
    time.sleep(0.5)

    try:
        # Detect face and get embedding
        success, embedding, error = detect_face_from_base64(data.image)

        if not success:
            return EnrollResponse(
                success=False, message=error or "Face detection failed"
            )

        # Generate IDs
        student_id = str(uuid.uuid4())
        photo_name = f"{student_id}.jpg"

        # Decode and save image to MinIO
        image_data = data.image.split(",")[1]
        import base64
        import numpy as np

        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        _, encoded_img = cv2.imencode(".jpg", img)
        minio_client.put_object(
            "student-photos",
            photo_name,
            io.BytesIO(encoded_img.tobytes()),
            len(encoded_img.tobytes()),
            "image/jpeg",
        )

        # Save to database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO students (id, name, embedding, photo_url) VALUES (%s, %s, %s, %s)",
            (student_id, data.name, json.dumps(embedding), photo_name),
        )
        conn.commit()
        cur.close()
        conn.close()

        # Reload known faces
        known_faces = load_all_students()

        return EnrollResponse(
            success=True, message=f"Registered {data.name}!", student_id=student_id
        )

    except Exception as e:
        return EnrollResponse(success=False, message=str(e))


@router.delete("/{student_id}", response_model=DeleteResponse)
async def delete_student(student_id: str):
    """Delete a student"""
    global known_faces

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT photo_url FROM students WHERE id = %s", (student_id,))
        row = cur.fetchone()

        if not row:
            return DeleteResponse(success=False, message="Student not found")

        filename = row["photo_url"]

        # Delete from database
        cur.execute("DELETE FROM students WHERE id = %s", (student_id,))

        # Delete from MinIO
        try:
            minio_client.remove_object("student-photos", filename)
        except:
            pass  # Continue if file missing

        conn.commit()
        cur.close()
        conn.close()

        # Reload known faces
        known_faces = load_all_students()

        return DeleteResponse(success=True, message="Student deleted")

    except Exception as e:
        return DeleteResponse(success=False, message=str(e))


@router.get("/photo/{photo_name}")
async def get_student_photo(photo_name: str):
    """Retrieve student photo from MinIO"""
    try:
        response = minio_client.get_object("student-photos", photo_name)
        return Response(content=response.read(), media_type="image/jpeg")
    except:
        return Response(status_code=404)
