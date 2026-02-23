"""
Location verification service
Handles GPS geofencing, WiFi validation, QR tokens
"""

import hashlib
import time
from math import radians, sin, cos, sqrt, atan2
from typing import Tuple, Dict, Optional
from datetime import datetime
from config import settings


class LocationService:

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates in meters using Haversine formula

        Args:
            lat1: Latitude of point 1
            lon1: Longitude of point 1
            lat2: Latitude of point 2
            lon2: Longitude of point 2

        Returns:
            Distance in meters
        """
        # Earth's radius in meters
        R = 6371000

        # Convert to radians
        phi1, phi2 = radians(lat1), radians(lat2)
        delta_phi = radians(lat2 - lat1)
        delta_lambda = radians(lon2 - lon1)

        # Haversine formula
        a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        return distance

    @staticmethod
    def validate_geofence(
        student_lat: Optional[float],
        student_lon: Optional[float],
        classroom_lat: Optional[float],
        classroom_lon: Optional[float],
        radius: int,
    ) -> Tuple[bool, Optional[float], str]:
        """
        Validate if student is within geofence

        Returns:
            (is_valid, distance_meters, message)
        """
        if student_lat is None or student_lon is None:
            return False, None, "GPS coordinates not provided"

        if classroom_lat is None or classroom_lon is None:
            return False, None, "Classroom coordinates not configured"

        distance = LocationService.haversine_distance(
            student_lat, student_lon, classroom_lat, classroom_lon
        )

        is_valid = distance <= radius

        if is_valid:
            message = f"Within geofence ({int(distance)}m from classroom)"
        else:
            message = (
                f"Outside geofence ({int(distance)}m away, must be within {radius}m)"
            )

        return is_valid, distance, message

    @staticmethod
    def validate_wifi_ssid(
        device_ssid: Optional[str], allowed_ssid: Optional[str]
    ) -> Tuple[bool, str]:
        """
        Validate WiFi SSID

        Returns:
            (is_valid, message)
        """
        if not device_ssid:
            return False, "WiFi SSID not provided"

        if not allowed_ssid:
            return False, "No WiFi restriction configured"

        # Case-insensitive comparison, strip whitespace
        is_valid = device_ssid.strip().lower() == allowed_ssid.strip().lower()

        if is_valid:
            message = f"Connected to correct WiFi: {allowed_ssid}"
        else:
            message = (
                f"Wrong WiFi network. Expected: {allowed_ssid}, Got: {device_ssid}"
            )

        return is_valid, message

    @staticmethod
    def generate_dynamic_qr_token(
        session_id: str, timestamp: Optional[int] = None
    ) -> str:
        """
        Generate dynamic QR token that changes every 30 seconds

        Args:
            session_id: Session UUID
            timestamp: Unix timestamp (defaults to current time)

        Returns:
            16-character hex token
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Round to nearest 30-second interval
        interval = timestamp // settings.QR_TOKEN_VALIDITY_SECONDS

        # Hash session_id + interval + secret
        token_string = f"{session_id}{interval}{settings.SECRET_KEY}"
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()

        # Return first 16 characters
        return token_hash[: settings.QR_TOKEN_LENGTH]

    @staticmethod
    def validate_qr_token(session_id: str, provided_token: str) -> Tuple[bool, str]:
        """
        Validate QR token (checks current and previous interval for grace period)

        Returns:
            (is_valid, message)
        """
        if not provided_token:
            return False, "QR token not provided"

        current_time = int(time.time())

        # Generate valid tokens (current and previous interval)
        current_token = LocationService.generate_dynamic_qr_token(
            session_id, current_time
        )
        previous_token = LocationService.generate_dynamic_qr_token(
            session_id, current_time - settings.QR_TOKEN_VALIDITY_SECONDS
        )

        is_valid = provided_token in [current_token, previous_token]

        if is_valid:
            message = "Valid QR token"
        else:
            message = f"QR code expired or invalid. Please scan again."

        return is_valid, message

    @staticmethod
    def validate_device_fingerprint(fingerprint: Optional[str]) -> Tuple[bool, str]:
        """
        Basic device legitimacy check

        Returns:
            (is_legitimate, message)
        """
        if not fingerprint:
            return False, "Device fingerprint not provided"

        # Suspicious patterns (emulators, VMs)
        suspicious_keywords = [
            "emulator",
            "generic",
            "unknown",
            "goldfish",
            "vbox",
            "vmware",
            "qemu",
        ]

        fingerprint_lower = fingerprint.lower()

        for keyword in suspicious_keywords:
            if keyword in fingerprint_lower:
                return False, f"Suspicious device detected: {keyword}"

        # Check if fingerprint is too short (likely fake)
        if len(fingerprint) < 20:
            return False, "Device fingerprint too short"

        return True, "Device appears legitimate"

    @staticmethod
    def calculate_verification_score(
        session: Dict,
        student_lat: Optional[float],
        student_lon: Optional[float],
        wifi_ssid: Optional[str],
        qr_token: Optional[str],
        device_fingerprint: Optional[str],
    ) -> Dict:
        """
        Calculate total verification score and details

        Returns:
            {
                'total_score': int,
                'required_score': int,
                'passed': bool,
                'checks': {
                    'wifi': {'passed': bool, 'score': int, 'message': str},
                    'gps': {...},
                    'qr': {...},
                    'device': {...}
                }
            }
        """
        checks = {}
        total_score = 0

        # WiFi Check
        wifi_valid, wifi_msg = LocationService.validate_wifi_ssid(
            wifi_ssid, session.get("allowed_wifi_ssid")
        )
        wifi_score = settings.SCORE_WIFI_MATCH if wifi_valid else 0
        total_score += wifi_score
        checks["wifi"] = {
            "passed": wifi_valid,
            "score": wifi_score,
            "max_score": settings.SCORE_WIFI_MATCH,
            "message": wifi_msg,
        }

        # GPS Geofence Check
        gps_valid, distance, gps_msg = LocationService.validate_geofence(
            student_lat,
            student_lon,
            session.get("classroom_lat"),
            session.get("classroom_lon"),
            session.get("geofence_radius", settings.DEFAULT_GEOFENCE_RADIUS_METERS),
        )
        gps_score = settings.SCORE_GPS_MATCH if gps_valid else 0
        total_score += gps_score
        checks["gps"] = {
            "passed": gps_valid,
            "score": gps_score,
            "max_score": settings.SCORE_GPS_MATCH,
            "distance_meters": distance,
            "message": gps_msg,
        }

        # QR Token Check
        qr_valid, qr_msg = LocationService.validate_qr_token(
            session.get("id"), qr_token
        )
        qr_score = settings.SCORE_QR_VALID if qr_valid else 0
        total_score += qr_score
        checks["qr"] = {
            "passed": qr_valid,
            "score": qr_score,
            "max_score": settings.SCORE_QR_VALID,
            "message": qr_msg,
        }

        # Device Check
        device_valid, device_msg = LocationService.validate_device_fingerprint(
            device_fingerprint
        )
        device_score = settings.SCORE_DEVICE_LEGITIMATE if device_valid else 0
        total_score += device_score
        checks["device"] = {
            "passed": device_valid,
            "score": device_score,
            "max_score": settings.SCORE_DEVICE_LEGITIMATE,
            "message": device_msg,
        }

        passed = total_score >= settings.MINIMUM_VERIFICATION_SCORE

        return {
            "total_score": total_score,
            "required_score": settings.MINIMUM_VERIFICATION_SCORE,
            "max_possible_score": (
                settings.SCORE_WIFI_MATCH
                + settings.SCORE_GPS_MATCH
                + settings.SCORE_QR_VALID
                + settings.SCORE_DEVICE_LEGITIMATE
            ),
            "passed": passed,
            "checks": checks,
        }
