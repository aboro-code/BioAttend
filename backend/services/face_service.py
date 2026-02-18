import cv2
import numpy as np
import base64
from dependencies import face_app


def detect_face_from_base64(image_data: str):
    """
    Detect face from base64 encoded image
    Returns: (success, embedding, error_message)
    """
    try:
        # Decode base64 image
        image_data = image_data.split(",")[1]
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Detect faces
        faces = face_app.get(img)

        if not faces:
            return False, None, "No face detected"

        # Get embedding from first face
        embedding = faces[0].embedding.tolist()

        return True, embedding, None

    except Exception as e:
        return False, None, str(e)
