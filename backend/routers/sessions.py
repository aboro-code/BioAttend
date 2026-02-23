"""
Session management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import random
import string
from psycopg2.extras import RealDictCursor
from dependencies import get_db_connection
from models.schemas import (
    SessionCreateRequest,
    SessionCreateResponse,
    QRTokenResponse,
    SessionStatusResponse,
    SessionDetailResponse,
    SessionAttendanceRecord,
)
from services.location_service import LocationService
from config import settings

router = APIRouter(prefix="/sessions", tags=["sessions"])


def generate_otp(length: int = 6) -> str:
    """Generate random numeric OTP"""
    return "".join(random.choices(string.digits, k=length))


@router.post("/create", response_model=SessionCreateResponse)
async def create_attendance_session(request: SessionCreateRequest):
    """
    Create a new attendance session
    Professor endpoint to start attendance collection
    """
    try:
        # Generate OTP
        otp = generate_otp(settings.OTP_LENGTH)

        # Calculate expiry
        expires_at = datetime.now() + timedelta(hours=request.duration_hours)

        # Generate initial QR token
        session_id_temp = f"temp_{datetime.now().timestamp()}"
        qr_token = LocationService.generate_dynamic_qr_token(session_id_temp)

        # Insert into database
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            INSERT INTO attendance_sessions 
            (otp, qr_token, course_name, professor_name, classroom_location,
             classroom_lat, classroom_lon, geofence_radius, allowed_wifi_ssid, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                otp,
                qr_token,
                request.course_name,
                request.professor_name,
                request.classroom_location,
                request.classroom_lat,
                request.classroom_lon,
                request.geofence_radius,
                request.allowed_wifi_ssid,
                expires_at,
            ),
        )

        session_id = cur.fetchone()["id"]

        # Update with actual QR token using real session_id
        actual_qr_token = LocationService.generate_dynamic_qr_token(str(session_id))
        cur.execute(
            "UPDATE attendance_sessions SET qr_token = %s WHERE id = %s",
            (actual_qr_token, session_id),
        )

        conn.commit()
        cur.close()
        conn.close()

        # Generate QR code URL
        qr_code_url = f"{settings.FRONTEND_URL or 'http://localhost:3000'}/mark-attendance?session={session_id}&token={actual_qr_token}"

        return SessionCreateResponse(
            success=True,
            message=f"Session created successfully for {request.course_name}",
            session_id=str(session_id),
            otp=otp,
            qr_code_url=qr_code_url,
            expires_at=expires_at,
        )

    except Exception as e:
        print(f"❌ Session creation error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        )


@router.get("/{session_id}/qr-token", response_model=QRTokenResponse)
async def get_dynamic_qr_token(session_id: str):
    """
    Get current dynamic QR token for session
    Refreshes every 30 seconds
    """
    try:
        # Verify session exists and is active
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT id, is_active, expires_at
            FROM attendance_sessions
            WHERE id = %s
        """,
            (session_id,),
        )

        session = cur.fetchone()
        cur.close()
        conn.close()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if not session["is_active"]:
            raise HTTPException(status_code=400, detail="Session is inactive")

        if session["expires_at"] < datetime.now():
            raise HTTPException(status_code=400, detail="Session has expired")

        # Generate current token
        token = LocationService.generate_dynamic_qr_token(session_id)
        qr_url = f"{settings.FRONTEND_URL or 'http://localhost:3000'}/mark-attendance?session={session_id}&token={token}"

        return QRTokenResponse(
            token=token,
            expires_in=settings.QR_TOKEN_VALIDITY_SECONDS,
            qr_url=qr_url,
            generated_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ QR token generation error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate QR token: {str(e)}"
        )


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    Get current status of a session
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT 
                s.id,
                s.course_name,
                s.professor_name,
                s.is_active,
                s.expires_at,
                s.classroom_location,
                EXTRACT(EPOCH FROM (s.expires_at - NOW())) AS seconds_remaining,
                COUNT(sa.id) AS total_students_marked
            FROM attendance_sessions s
            LEFT JOIN session_attendance sa ON s.id = sa.session_id
            WHERE s.id = %s
            GROUP BY s.id
        """,
            (session_id,),
        )

        session = cur.fetchone()
        cur.close()
        conn.close()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionStatusResponse(
            session_id=str(session["id"]),
            course_name=session["course_name"],
            professor_name=session["professor_name"],
            is_active=session["is_active"],
            expires_at=session["expires_at"],
            seconds_remaining=max(0, int(session["seconds_remaining"] or 0)),
            total_students_marked=session["total_students_marked"],
            classroom_location=session["classroom_location"],
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Session status error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get session status: {str(e)}"
        )


@router.get("/{session_id}/details", response_model=SessionDetailResponse)
async def get_session_details(session_id: str):
    """
    Get detailed session information including all attendance records
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get session info
        cur.execute(
            """
            SELECT 
                s.id,
                s.course_name,
                s.professor_name,
                s.is_active,
                s.expires_at,
                s.classroom_location,
                EXTRACT(EPOCH FROM (s.expires_at - NOW())) AS seconds_remaining,
                COUNT(sa.id) AS total_students_marked
            FROM attendance_sessions s
            LEFT JOIN session_attendance sa ON s.id = sa.session_id
            WHERE s.id = %s
            GROUP BY s.id
        """,
            (session_id,),
        )

        session = cur.fetchone()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get attendance records
        cur.execute(
            """
            SELECT 
                sa.student_id,
                st.name AS student_name,
                sa.marked_at,
                sa.verification_method,
                sa.verification_scores->>'total_score' AS location_score
            FROM session_attendance sa
            JOIN students st ON sa.student_id = st.id
            WHERE sa.session_id = %s
            ORDER BY sa.marked_at DESC
        """,
            (session_id,),
        )

        attendance_records = cur.fetchall()
        cur.close()
        conn.close()

        # Format response
        session_status = SessionStatusResponse(
            session_id=str(session["id"]),
            course_name=session["course_name"],
            professor_name=session["professor_name"],
            is_active=session["is_active"],
            expires_at=session["expires_at"],
            seconds_remaining=max(0, int(session["seconds_remaining"] or 0)),
            total_students_marked=session["total_students_marked"],
            classroom_location=session["classroom_location"],
        )

        attendance_list = [
            SessionAttendanceRecord(
                student_id=str(record["student_id"]),
                student_name=record["student_name"],
                marked_at=record["marked_at"],
                verification_method=record["verification_method"],
                location_score=(
                    int(record["location_score"]) if record["location_score"] else None
                ),
            )
            for record in attendance_records
        ]

        return SessionDetailResponse(
            session=session_status, attendance_records=attendance_list
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Session details error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get session details: {str(e)}"
        )


@router.post("/{session_id}/close")
async def close_session(session_id: str):
    """
    Manually close a session before expiry
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE attendance_sessions
            SET is_active = FALSE
            WHERE id = %s AND is_active = TRUE
            RETURNING id
        """,
            (session_id,),
        )

        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not result:
            raise HTTPException(
                status_code=404, detail="Session not found or already closed"
            )

        return {"success": True, "message": "Session closed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Session close error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to close session: {str(e)}"
        )


@router.get("/active", response_model=list[SessionStatusResponse])
async def get_active_sessions():
    """
    Get all currently active sessions
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT 
                s.id,
                s.course_name,
                s.professor_name,
                s.is_active,
                s.expires_at,
                s.classroom_location,
                EXTRACT(EPOCH FROM (s.expires_at - NOW())) AS seconds_remaining,
                COUNT(sa.id) AS total_students_marked
            FROM attendance_sessions s
            LEFT JOIN session_attendance sa ON s.id = sa.session_id
            WHERE s.is_active = TRUE AND s.expires_at > NOW()
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """
        )

        sessions = cur.fetchall()
        cur.close()
        conn.close()

        return [
            SessionStatusResponse(
                session_id=str(session["id"]),
                course_name=session["course_name"],
                professor_name=session["professor_name"],
                is_active=session["is_active"],
                expires_at=session["expires_at"],
                seconds_remaining=max(0, int(session["seconds_remaining"] or 0)),
                total_students_marked=session["total_students_marked"],
                classroom_location=session["classroom_location"],
            )
            for session in sessions
        ]

    except Exception as e:
        print(f"❌ Get active sessions error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get active sessions: {str(e)}"
        )
