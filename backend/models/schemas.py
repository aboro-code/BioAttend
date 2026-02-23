"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from uuid import UUID

# ==================== EXISTING MODELS ====================


class EnrollRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    image: str = Field(..., description="Base64 encoded image")


class EnrollResponse(BaseModel):
    success: bool
    message: str
    student_id: Optional[str] = None


class StudentResponse(BaseModel):
    id: str
    name: str
    photo_url: str


class AttendanceLog(BaseModel):
    name: str
    status: str
    time: str


class CameraStatusResponse(BaseModel):
    active: bool
    camera_object_exists: bool


class DeleteResponse(BaseModel):
    success: bool
    message: str


# ==================== NEW SESSION MODELS ====================


class SessionCreateRequest(BaseModel):
    course_name: str = Field(
        ..., min_length=1, max_length=200, description="Name of the course"
    )
    professor_name: str = Field(
        ..., min_length=1, max_length=100, description="Professor's name"
    )
    duration_hours: int = Field(
        default=2, ge=1, le=8, description="Session duration in hours"
    )
    classroom_location: Optional[str] = Field(
        None, max_length=200, description="Human-readable location"
    )
    classroom_lat: Optional[float] = Field(
        None, ge=-90, le=90, description="Classroom latitude"
    )
    classroom_lon: Optional[float] = Field(
        None, ge=-180, le=180, description="Classroom longitude"
    )
    geofence_radius: int = Field(
        default=50, ge=10, le=500, description="Geofence radius in meters"
    )
    allowed_wifi_ssid: Optional[str] = Field(
        None, max_length=100, description="Allowed WiFi network name"
    )

    @model_validator(mode="after")
    def validate_gps_coordinates(self):
        """Ensure both lat and lon are provided together"""
        if self.classroom_lat is not None and self.classroom_lon is None:
            raise ValueError("If latitude is provided, longitude must also be provided")
        if self.classroom_lon is not None and self.classroom_lat is None:
            raise ValueError("If longitude is provided, latitude must also be provided")
        return self


class SessionCreateResponse(BaseModel):
    success: bool
    message: str
    session_id: Optional[str] = None
    otp: Optional[str] = None
    qr_code_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class QRTokenResponse(BaseModel):
    token: str
    expires_in: int  # seconds
    qr_url: str
    generated_at: datetime


class LocationVerificationRequest(BaseModel):
    otp: str = Field(..., min_length=6, max_length=6)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    wifi_ssid: Optional[str] = Field(None, max_length=100)
    qr_token: Optional[str] = Field(None)
    device_fingerprint: Optional[str] = Field(None, max_length=500)


class LocationVerificationResponse(BaseModel):
    success: bool
    message: str
    total_score: int
    required_score: int
    passed: bool
    checks: Dict[str, Dict[str, Any]]  # Details of each check
    session_id: Optional[str] = None


class LivenessFrame(BaseModel):
    frame_data: str = Field(..., description="Base64 encoded frame")
    frame_number: int = Field(..., ge=0)
    timestamp: float


class LivenessVerificationRequest(BaseModel):
    frames: List[LivenessFrame] = Field(
        ...,
        min_length=30,
        max_length=120,
        description="Video frames for liveness check",
    )
    challenges_completed: Optional[List[str]] = Field(
        default_factory=list, description="Challenges student completed"
    )


class LivenessVerificationResponse(BaseModel):
    success: bool
    message: str
    liveness_passed: bool
    confidence_score: float = Field(..., ge=0, le=1)
    details: Dict[str, Any]


class SecureAttendanceRequest(BaseModel):
    session_id: str
    otp: str = Field(..., min_length=6, max_length=6)
    image: str = Field(..., description="Base64 encoded face image")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    wifi_ssid: Optional[str] = None
    qr_token: Optional[str] = None
    device_fingerprint: Optional[str] = None
    liveness_data: Optional[Dict[str, Any]] = None


class SecureAttendanceResponse(BaseModel):
    success: bool
    message: str
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    marked_at: Optional[datetime] = None
    verification_summary: Optional[Dict[str, Any]] = None


class SessionStatusResponse(BaseModel):
    session_id: str
    course_name: str
    professor_name: str
    is_active: bool
    expires_at: datetime
    seconds_remaining: int
    total_students_marked: int
    classroom_location: Optional[str] = None


class SessionAttendanceRecord(BaseModel):
    student_id: str
    student_name: str
    marked_at: datetime
    verification_method: Optional[str] = None
    location_score: Optional[int] = None


class SessionDetailResponse(BaseModel):
    session: SessionStatusResponse
    attendance_records: List[SessionAttendanceRecord]
