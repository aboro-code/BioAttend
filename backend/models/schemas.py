"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EnrollRequest(BaseModel):
    name: str
    image: str  # Base64 encoded image


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
