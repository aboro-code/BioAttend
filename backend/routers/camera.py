from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from datetime import datetime
from services.camera_service import force_release_camera, generate_video_frames
from models.schemas import CameraStatusResponse
from dependencies import stream_active, camera

router = APIRouter(prefix="/camera", tags=["camera"])


@router.get("/video_feed")
async def video_feed():
    """Stream live video with face recognition"""
    return StreamingResponse(
        generate_video_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.post("/release")
async def release_camera():
    """Force release camera"""
    force_release_camera()
    return {"status": "Camera released", "timestamp": datetime.now().isoformat()}


@router.get("/status", response_model=CameraStatusResponse)
async def camera_status():
    """Get camera status"""
    return {"active": stream_active, "camera_object_exists": camera is not None}
