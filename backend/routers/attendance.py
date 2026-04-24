from fastapi import APIRouter, Depends, HTTPException
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
    OTPValidationRequest,
    OTPValidationResponse,
    ScoreCalculationRequest,
    ScoreCalculationResponse,
    LivenessVerificationRequest,
    LivenessVerificationResponse,
    SecureAttendanceRequest,
    SecureAttendanceResponse,
)
from services.export_service import generate_csv_export, generate_excel_export
from services.location_service import LocationService
from services.face_service import detect_face_from_base64
from services.liveness_service import LivenessService
from config import settings
from auth_dependencies import require_role
import numpy as np

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _match_student_with_pgvector(cur, live_embedding: np.ndarray):
    """
    Try pgvector similarity search first. Returns (student_id, student_name, similarity)
    or (None, None, 0.0) when not found/unsupported.
    """
    try:
        # pgvector cosine distance: smaller is better
        embedding_str = "[" + ",".join(map(str, live_embedding.tolist())) + "]"
        cur.execute(
            """
            SELECT id, name, 1 - (embedding <=> %s::vector) AS similarity
            FROM students
            ORDER BY embedding <=> %s::vector
            LIMIT 1
        """,
            (embedding_str, embedding_str),
        )
        row = cur.fetchone()
        if not row:
            return None, None, 0.0
        return row["id"], row["name"], float(row["similarity"] or 0.0)
    except Exception:
        # Fallback path is handled by in-memory matching.
        return None, None, 0.0


@router.post(
    "/validate-otp",
    response_model=OTPValidationResponse,
)
async def validate_otp(request: OTPValidationRequest):
    """Validate OTP and return active session details for student flow bootstrap."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Ensure the student email exists (enrolled in system)
        cur.execute("SELECT 1 FROM students WHERE email = %s LIMIT 1", (request.email,))
        student_exists = cur.fetchone()
        if not student_exists:
            cur.close()
            conn.close()
            return OTPValidationResponse(
                success=False,
                message="Email not found in enrolled students",
            )

        cur.execute(
            """
            SELECT id, course_name, professor_name, classroom_location, expires_at,
                   geofence_radius, is_active
            FROM attendance_sessions
            WHERE otp = %s
            ORDER BY created_at DESC
            LIMIT 1
        """,
            (request.otp,),
        )
        session = cur.fetchone()
        cur.close()
        conn.close()

        if not session:
            return OTPValidationResponse(success=False, message="Invalid OTP")
        if not session["is_active"]:
            return OTPValidationResponse(success=False, message="Session is inactive")
        if session["expires_at"] <= datetime.now():
            return OTPValidationResponse(success=False, message="Session has expired")

        return OTPValidationResponse(
            success=True,
            message="OTP validated",
            session_id=str(session["id"]),
            course_name=session["course_name"],
            professor_name=session["professor_name"],
            classroom_location=session["classroom_location"],
            expires_at=session["expires_at"],
            geofence_radius=session["geofence_radius"],
            requires_liveness=settings.LIVENESS_ENABLED,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OTP validation failed: {str(e)}")


@router.post(
    "/calculate-score",
    response_model=ScoreCalculationResponse,
)
async def calculate_score(request: ScoreCalculationRequest):
    """Calculate browser-based verification score (GPS 60 + Device 40)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT id, otp, classroom_lat, classroom_lon, geofence_radius, expires_at, is_active
            FROM attendance_sessions
            WHERE id = %s AND otp = %s
        """,
            (request.session_id, request.otp),
        )
        session = cur.fetchone()
        cur.close()
        conn.close()

        if not session:
            return ScoreCalculationResponse(
                success=False,
                message="Invalid session or OTP",
                total_score=0,
                required_score=70,
                passed=False,
                breakdown={},
                policy={"can_proceed_to_liveness": False, "can_proceed_to_face": False},
            )
        if not session["is_active"] or session["expires_at"] <= datetime.now():
            return ScoreCalculationResponse(
                success=False,
                message="Session inactive or expired",
                total_score=0,
                required_score=70,
                passed=False,
                breakdown={},
                policy={"can_proceed_to_liveness": False, "can_proceed_to_face": False},
            )

        gps_valid, distance, gps_msg = LocationService.validate_geofence(
            request.latitude,
            request.longitude,
            float(session.get("classroom_lat")),
            float(session.get("classroom_lon")),
            float(session.get("geofence_radius", settings.DEFAULT_GEOFENCE_RADIUS_METERS)),
        )
        gps_score = 60 if gps_valid else 0

        device_valid, device_msg = LocationService.validate_device_fingerprint(
            request.device_fingerprint
        )
        device_score = 40 if device_valid else 0

        total = gps_score + device_score
        passed = total >= 70
        breakdown = {
            "gps": {
                "passed": gps_valid,
                "score": gps_score,
                "max_score": 60,
                "distance_meters": distance,
                "message": gps_msg,
            },
            "device": {
                "passed": device_valid,
                "score": device_score,
                "max_score": 40,
                "message": device_msg,
                "flags": [] if device_valid else ["suspicious_or_invalid_fingerprint"],
            },
        }
        return ScoreCalculationResponse(
            success=True,
            message="Score calculated" if passed else "Score below threshold",
            total_score=total,
            required_score=70,
            passed=passed,
            breakdown=breakdown,
            policy={
                "can_proceed_to_liveness": passed,
                "can_proceed_to_face": passed and (not settings.LIVENESS_ENABLED),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Score calculation failed: {str(e)}")


@router.post(
    "/verify-liveness",
    response_model=LivenessVerificationResponse,
)
async def verify_liveness(request: LivenessVerificationRequest):
    """Run EAR blink-based liveness verification after score gate passes."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT id, otp, classroom_lat, classroom_lon, geofence_radius, expires_at, is_active
            FROM attendance_sessions
            WHERE id = %s AND otp = %s
        """,
            (request.session_id, request.otp),
        )
        session = cur.fetchone()
        cur.close()
        conn.close()

        if not session:
            return LivenessVerificationResponse(
                success=False,
                message="Invalid session or OTP",
                liveness_passed=False,
                confidence_score=0.0,
                details={"failure_reason": "invalid_session_or_otp"},
            )
        if not session["is_active"] or session["expires_at"] <= datetime.now():
            return LivenessVerificationResponse(
                success=False,
                message="Session inactive or expired",
                liveness_passed=False,
                confidence_score=0.0,
                details={"failure_reason": "inactive_or_expired_session"},
            )

        result = LivenessService.verify_liveness(
            [frame.model_dump() for frame in request.frames]
        )
        return LivenessVerificationResponse(
            success=True,
            message="Liveness verified"
            if result["liveness_passed"]
            else "Liveness verification failed",
            liveness_passed=result["liveness_passed"],
            confidence_score=result["confidence_score"],
            details=result["details"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Liveness verification failed: {str(e)}")


@router.get(
    "/today",
    response_model=List[AttendanceLog],
    dependencies=[Depends(require_role("professor"))],
)
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


@router.post(
    "/verify-location",
    response_model=LocationVerificationResponse,
)
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


@router.post(
    "/mark-secure",
    response_model=SecureAttendanceResponse,
)
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

        # 2. Verify required score (GPS 60 + Device 40, threshold 70)
        gps_valid, distance, gps_msg = LocationService.validate_geofence(
            request.latitude,
            request.longitude,
            float(session.get("classroom_lat")),
            float(session.get("classroom_lon")),
            float(session.get("geofence_radius", settings.DEFAULT_GEOFENCE_RADIUS_METERS)),
        )
        gps_score = 60 if gps_valid else 0

        device_valid, device_msg = LocationService.validate_device_fingerprint(
            request.device_fingerprint
        )
        device_score = 40 if device_valid else 0

        total_score = gps_score + device_score
        verification_result = {
            "total_score": total_score,
            "required_score": 70,
            "passed": total_score >= 70,
            "checks": {
                "gps": {
                    "passed": gps_valid,
                    "score": gps_score,
                    "max_score": 60,
                    "distance_meters": distance,
                    "message": gps_msg,
                },
                "device": {
                    "passed": device_valid,
                    "score": device_score,
                    "max_score": 40,
                    "message": device_msg,
                },
            },
        }

        if total_score < 70:
            return SecureAttendanceResponse(
                success=False,
                message=f"Verification score below threshold. Score: {total_score}/70",
                verification_summary=verification_result,
            )

        # 3. Liveness gate (if enabled) must pass before embedding matching
        if settings.LIVENESS_ENABLED:
            liveness_ok = bool(request.liveness_data and request.liveness_data.get("passed"))
            if not liveness_ok:
                return SecureAttendanceResponse(
                    success=False,
                    message="Liveness verification required before face matching",
                    verification_summary={
                        "location_score": total_score,
                        "liveness_passed": False,
                    },
                )

        # 4. Face detection and recognition
        face_success, embedding, face_error = detect_face_from_base64(request.image)

        if not face_success:
            return SecureAttendanceResponse(
                success=False, message=face_error or "Face detection failed"
            )

        # 5. Match face against the specific student's registered face
        cur.execute("SELECT id, name, embedding FROM students WHERE email = %s", (request.email,))
        student_record = cur.fetchone()
        
        if not student_record:
            return SecureAttendanceResponse(
                success=False, message="Email not found in database"
            )
            
        student_id = student_record["id"]
        best_match_name = student_record["name"]
        
        student_embedding_raw = student_record["embedding"]
        if isinstance(student_embedding_raw, str):
            student_embedding = json.loads(student_embedding_raw)
        else:
            student_embedding = student_embedding_raw
            
        live_embedding = np.array(embedding).astype(np.float32)
        known_embedding = np.array(student_embedding).astype(np.float32)
        
        best_similarity = np.dot(live_embedding, known_embedding) / (
            np.linalg.norm(live_embedding) * np.linalg.norm(known_embedding)
        )
        
        if best_similarity < settings.RECOGNITION_THRESHOLD:
            return SecureAttendanceResponse(
                success=False,
                message=f"Face does not match the registered owner of this email. Confidence: {best_similarity:.2%}",
            )

        # 7. Check if already marked in this session
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

        # 8. Mark attendance
        marked_at = datetime.now()

        # Prepare data for storage
        device_info = {
            "fingerprint": request.device_fingerprint,
            "timestamp": marked_at.isoformat(),
        }

        location_data = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "distance_from_classroom": verification_result["checks"]["gps"][
                "distance_meters"
            ],
        }

        verification_scores = {
            "total_score": verification_result["total_score"],
            "required_score": verification_result["required_score"],
            "gps_score": verification_result["checks"]["gps"]["score"],
            "device_score": verification_result["checks"]["device"]["score"],
        }

        # Determine verification method
        passed_checks = [k for k, v in verification_result["checks"].items() if v["passed"]]
        if settings.LIVENESS_ENABLED:
            passed_checks.append("liveness")
        passed_checks.append("face")
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

        # 9. Success response
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


@router.get("/export/csv", dependencies=[Depends(require_role("professor"))])
async def export_csv(session_id: str = None):
    """Export attendance as CSV"""
    try:
        content, filename = generate_csv_export(session_id)
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/export/excel", dependencies=[Depends(require_role("professor"))])
async def export_excel(session_id: str = None):
    """Export attendance as Excel"""
    try:
        excel_file, filename = generate_excel_export(session_id)
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        return {"error": str(e)}


@router.get(
    "/session/{session_id}/summary",
    dependencies=[Depends(require_role("professor"))],
)
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
