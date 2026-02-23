from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
from datetime import datetime
from psycopg2.extras import RealDictCursor
import json
from dependencies import get_db_connection, known_faces
from models.schemas import (
    AttendanceLog,
    LocationVerificationRequest,
    LocationVerificationResponse,
    SecureAttendanceRequest,
    SecureAttendanceResponse,
)
from services.export_service import generate_csv_export, generate_excel_export
from services.location_service import LocationService
from services.face_service import detect_face_from_base64
import numpy as np

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/today", response_model=List[AttendanceLog])
async def get_today_attendance():
    """Get today's attendance logs (legacy system)"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT s.name, a.status, TO_CHAR(a.log_time, 'HH12:MI AM') as time 
        FROM attendance_logs a 
        JOIN students s ON a.student_id = s.id 
        WHERE a.log_time::date = CURRENT_DATE 
        ORDER BY a.log_time DESC
    """
    )
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res


@router.post("/verify-location", response_model=LocationVerificationResponse)
async def verify_location(request: LocationVerificationRequest):
    """
    Step 1: Verify student location before allowing face capture
    Validates: WiFi, GPS, QR token, Device
    Returns score and whether student can proceed
    """
    try:
        # Get session by OTP
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT id, otp, course_name, classroom_lat, classroom_lon, 
                   geofence_radius, allowed_wifi_ssid, expires_at, is_active
            FROM attendance_sessions
            WHERE otp = %s AND is_active = TRUE AND expires_at > NOW()
        """,
            (request.otp,),
        )

        session = cur.fetchone()
        cur.close()
        conn.close()

        if not session:
            return LocationVerificationResponse(
                success=False,
                message="Invalid or expired OTP",
                total_score=0,
                required_score=0,
                passed=False,
                checks={},
            )

        # Calculate verification score
        verification_result = LocationService.calculate_verification_score(
            session=session,
            student_lat=request.latitude,
            student_lon=request.longitude,
            wifi_ssid=request.wifi_ssid,
            qr_token=request.qr_token,
            device_fingerprint=request.device_fingerprint,
        )

        return LocationVerificationResponse(
            success=True,
            message=(
                "Location verified"
                if verification_result["passed"]
                else "Location verification failed"
            ),
            total_score=verification_result["total_score"],
            required_score=verification_result["required_score"],
            passed=verification_result["passed"],
            checks=verification_result["checks"],
            session_id=str(session["id"]),
        )

    except Exception as e:
        print(f"❌ Location verification error: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.post("/mark-secure", response_model=SecureAttendanceResponse)
async def mark_attendance_secure(request: SecureAttendanceRequest):
    """
    Step 2: Mark attendance with full verification
    Requires: Valid session + Location verification + Face recognition
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Validate session
        cur.execute(
            """
            SELECT id, otp, course_name, classroom_lat, classroom_lon,
                   geofence_radius, allowed_wifi_ssid, expires_at, is_active
            FROM attendance_sessions
            WHERE id = %s AND otp = %s AND is_active = TRUE AND expires_at > NOW()
        """,
            (request.session_id, request.otp),
        )

        session = cur.fetchone()

        if not session:
            return SecureAttendanceResponse(
                success=False, message="Invalid session or OTP"
            )

        # 2. Verify location (score-based)
        verification_result = LocationService.calculate_verification_score(
            session=session,
            student_lat=request.latitude,
            student_lon=request.longitude,
            wifi_ssid=request.wifi_ssid,
            qr_token=request.qr_token,
            device_fingerprint=request.device_fingerprint,
        )

        if not verification_result["passed"]:
            return SecureAttendanceResponse(
                success=False,
                message=f"Location verification failed. Score: {verification_result['total_score']}/{verification_result['required_score']}",
                verification_summary=verification_result,
            )

        # 3. Face detection and recognition
        face_success, embedding, face_error = detect_face_from_base64(request.image)

        if not face_success:
            return SecureAttendanceResponse(
                success=False, message=face_error or "Face detection failed"
            )

        # 4. Match face with enrolled students
        if len(known_faces) == 0:
            return SecureAttendanceResponse(
                success=False, message="No students enrolled in system"
            )

        # Convert embedding to numpy array
        live_embedding = np.array(embedding).astype(np.float32)

        # Find best match
        best_match_name = None
        best_similarity = 0.0

        for known_face in known_faces:
            known_embedding = known_face["embedding"]

            # Cosine similarity
            similarity = np.dot(live_embedding, known_embedding) / (
                np.linalg.norm(live_embedding) * np.linalg.norm(known_embedding)
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_name = known_face["name"]

        # Check if similarity meets threshold
        from config import settings

        if best_similarity < settings.RECOGNITION_THRESHOLD:
            return SecureAttendanceResponse(
                success=False,
                message=f"Face not recognized. Confidence: {best_similarity:.2%}",
            )

        # 5. Get student ID
        cur.execute("SELECT id FROM students WHERE name = %s", (best_match_name,))
        student_row = cur.fetchone()

        if not student_row:
            return SecureAttendanceResponse(
                success=False, message="Student not found in database"
            )

        student_id = student_row["id"]

        # 6. Check if already marked in this session
        cur.execute(
            """
            SELECT id FROM session_attendance
            WHERE session_id = %s AND student_id = %s
        """,
            (request.session_id, student_id),
        )

        existing = cur.fetchone()

        if existing:
            return SecureAttendanceResponse(
                success=False,
                message=f"{best_match_name} has already marked attendance for this session",
            )

        # 7. Mark attendance
        marked_at = datetime.now()

        # Prepare data for storage
        device_info = {
            "fingerprint": request.device_fingerprint,
            "timestamp": marked_at.isoformat(),
        }

        location_data = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "wifi_ssid": request.wifi_ssid,
            "distance_from_classroom": verification_result["checks"]["gps"].get(
                "distance_meters"
            ),
        }

        verification_scores = {
            "total_score": verification_result["total_score"],
            "required_score": verification_result["required_score"],
            "wifi_score": verification_result["checks"]["wifi"]["score"],
            "gps_score": verification_result["checks"]["gps"]["score"],
            "qr_score": verification_result["checks"]["qr"]["score"],
            "device_score": verification_result["checks"]["device"]["score"],
        }

        # Determine verification method
        verification_method = "multi-factor"
        passed_checks = [
            k for k, v in verification_result["checks"].items() if v["passed"]
        ]
        verification_method = "+".join(passed_checks)

        # Insert attendance record
        cur.execute(
            """
            INSERT INTO session_attendance 
            (session_id, student_id, marked_at, device_info, location_data, 
             verification_scores, liveness_data, verification_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                request.session_id,
                student_id,
                marked_at,
                json.dumps(device_info),
                json.dumps(location_data),
                json.dumps(verification_scores),
                json.dumps(request.liveness_data) if request.liveness_data else None,
                verification_method,
            ),
        )

        conn.commit()
        cur.close()
        conn.close()

        # 8. Success response
        return SecureAttendanceResponse(
            success=True,
            message=f"Attendance marked successfully for {best_match_name}",
            student_id=str(student_id),
            student_name=best_match_name,
            marked_at=marked_at,
            verification_summary={
                "location_score": verification_result["total_score"],
                "face_confidence": float(best_similarity),
                "verification_method": verification_method,
                "checks_passed": passed_checks,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Secure attendance marking error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to mark attendance: {str(e)}"
        )


@router.get("/export/csv")
async def export_csv():
    """Export attendance as CSV"""
    try:
        content, filename = generate_csv_export()
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/export/excel")
async def export_excel():
    """Export attendance as Excel"""
    try:
        excel_file, filename = generate_excel_export()
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/session/{session_id}/summary")
async def get_session_attendance_summary(session_id: str):
    """
    Get attendance summary for a specific session
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get session info
        cur.execute(
            """
            SELECT course_name, professor_name, created_at, expires_at
            FROM attendance_sessions
            WHERE id = %s
        """,
            (session_id,),
        )

        session = cur.fetchone()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get attendance records with verification details
        cur.execute(
            """
            SELECT 
                st.name as student_name,
                sa.marked_at,
                sa.verification_method,
                sa.verification_scores,
                sa.location_data
            FROM session_attendance sa
            JOIN students st ON sa.student_id = st.id
            WHERE sa.session_id = %s
            ORDER BY sa.marked_at ASC
        """,
            (session_id,),
        )

        records = cur.fetchall()
        cur.close()
        conn.close()

        # Format records
        formatted_records = []
        for record in records:
            scores = (
                record["verification_scores"]
                if isinstance(record["verification_scores"], dict)
                else {}
            )
            location = (
                record["location_data"]
                if isinstance(record["location_data"], dict)
                else {}
            )

            formatted_records.append(
                {
                    "student_name": record["student_name"],
                    "marked_at": record["marked_at"].isoformat(),
                    "verification_method": record["verification_method"],
                    "location_score": scores.get("total_score", 0),
                    "wifi_ssid": location.get("wifi_ssid"),
                    "distance_meters": location.get("distance_from_classroom"),
                }
            )

        return {
            "session": {
                "course_name": session["course_name"],
                "professor_name": session["professor_name"],
                "created_at": session["created_at"].isoformat(),
                "expires_at": session["expires_at"].isoformat(),
            },
            "total_students": len(formatted_records),
            "attendance_records": formatted_records,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Session summary error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")
