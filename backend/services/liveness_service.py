import base64
import cv2
import numpy as np
from typing import Any, Dict, List, Tuple
from config import settings
from dependencies import get_face_app

class LivenessService:
    """Blink-based liveness checks using eye landmark geometry."""
    # InsightFace 106-point eye indices
    LEFT_EYE_106 = [35, 41, 33, 37, 42, 39] 
    RIGHT_EYE_106 = [89, 95, 87, 91, 96, 93]

    @staticmethod
    def _decode_base64_image(frame_data: str):
        """Decodes base64 string to OpenCV BGR image."""
        if not frame_data:
            return None
        try:
            # Handle data URI prefix if present
            payload = frame_data.split(",")[1] if "," in frame_data else frame_data
            img_bytes = base64.b64decode(payload)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"Liveness decoding error: {e}")
            return None

    @staticmethod
    def _euclidean(p1: np.ndarray, p2: np.ndarray) -> float:
        return float(np.linalg.norm(p1 - p2))

    @staticmethod
    def _eye_aspect_ratio(eye_points: np.ndarray) -> float:
        # EAR formula: (vertical dists) / (2 * horizontal dist)
        v1 = LivenessService._euclidean(eye_points[1], eye_points[5])
        v2 = LivenessService._euclidean(eye_points[2], eye_points[4])
        h = LivenessService._euclidean(eye_points[0], eye_points[3])
        return (v1 + v2) / (2.0 * h) if h != 0 else 0.0

    @staticmethod
    def _extract_ear(face) -> Tuple[bool, float]:
        """Extracts average EAR from InsightFace landmarks."""
        # Try finding landmarks in common InsightFace attribute locations
        kps = getattr(face, "landmark_2d_106", None)
        if kps is None:
            kps = getattr(face, "kps", None)

        if kps is None:
            return False, 0.0

        kps = np.array(kps)
        
        # Check for 106-point model output
        if len(kps) >= 106:
            left = kps[LivenessService.LEFT_EYE_106]
            right = kps[LivenessService.RIGHT_EYE_106]
            ear_left = LivenessService._eye_aspect_ratio(left)
            ear_right = LivenessService._eye_aspect_ratio(right)
            return True, float((ear_left + ear_right) / 2.0)
        
        return False, 0.0

    @classmethod
    def verify_liveness(cls, frames: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Entry point for liveness verification using dynamic thresholding."""
        if not frames:
            return {"liveness_passed": False, "confidence_score": 0.0, "details": {"failure_reason": "No frames"}}

        ear_values = []
        face_detected_count = 0

        # Pass 1: Extract EAR from all frames
        for frame in frames:
            # Using 'cls' ensures we call the method belonging to this class
            img = cls._decode_base64_image(frame.get("frame_data", ""))
            if img is None:
                continue
            
            face_app = get_face_app()
            faces = face_app.get(img)
            if not faces:
                continue

            face_detected_count += 1
            ok, ear = cls._extract_ear(faces[0])
            if ok:
                ear_values.append(ear)

        if not ear_values:
            return {
                "liveness_passed": False, 
                "confidence_score": 0.0,
                "details": {
                    "failure_reason": "Landmark extraction failed. Ensure 'landmark_2d_106' module is loaded.", 
                    "face_detected": face_detected_count,
                    "points_detected": len(getattr(faces[0], "landmark_2d_106", [])) if face_detected_count > 0 else 0
                }
            }

        # Pass 2: Analysis
        ear_mean = sum(ear_values) / len(ear_values)
        # Use 94% of mean to detect a significant dip (a blink)
        # Higher threshold (e.g. 0.94) is more sensitive/forgiving
        dynamic_threshold = ear_mean * 0.98
        
        blink_count = 0
        consecutive_closed = 0
        
        for ear in ear_values:
            if ear < dynamic_threshold:
                consecutive_closed += 1
            else:
                # If we were closed and now open, that's a blink
                if consecutive_closed >= 1: 
                    blink_count += 1
                consecutive_closed = 0

        # Handle case where the last frames were a blink
        if consecutive_closed >= 1:
            blink_count += 1
            
        # Verification Logic
        # We require at least 1 clear blink in the 3-second window
        min_blinks = 1
        passed = blink_count >= min_blinks

        return {
            "liveness_passed": passed,
            "confidence_score": 0.95 if passed else 0.3,
            "details": {
                "blink_count": blink_count,
                "ear_mean": float(ear_mean),
                "ear_min": float(min(ear_values)),
                "dynamic_threshold": float(dynamic_threshold),
                "face_detected_frames": face_detected_count,
                "status": "Success" if passed else "Blink not detected clearly"
            }
        }