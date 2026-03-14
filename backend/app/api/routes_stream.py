from fastapi import APIRouter, HTTPException
from app.database.schemas import StreamStartRequest
from app.services.stream_processor import stream_processor

router = APIRouter()

@router.post("/start-stream")
def start_stream(request: StreamStartRequest):
    success = stream_processor.start_stream(request.camera_url, request.camera_id)
    if not success:
        raise HTTPException(status_code=400, detail="Stream already active for this camera.")
    return {"message": f"Started processing stream for camera {request.camera_id}"}
