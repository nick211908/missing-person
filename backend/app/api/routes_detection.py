from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database.db import get_db, DetectionEvent, MissingPerson
from app.database.schemas import DetectionEventResponse
from app.services.face_detector import detect_faces
from app.services.matcher import matcher
from app.services.preprocessor import preprocess_frame
from app.auth.auth import get_current_user
from app.models.user import User
from pydantic import BaseModel
from typing import Optional
import cv2
import numpy as np
import base64
import tempfile
import os

router = APIRouter()

class FrameRequest(BaseModel):
    camera_id: str
    timestamp: Optional[str] = None
    frame: str  # base64 encoded JPEG image

@router.get("/detections", response_model=list[DetectionEventResponse])
def get_detections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 🔒 Auth required
):
    events = db.query(DetectionEvent).order_by(DetectionEvent.timestamp.desc()).limit(100).all()
    return events

@router.post("/process-frame")
async def process_frame(
    body: FrameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a base64-encoded JPEG image, detect faces and match against DB."""
    try:
        img_bytes = base64.b64decode(body.frame)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data.")
    
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")

    # Preprocess frame for better detection in CCTV conditions
    img = preprocess_frame(img)

    faces = detect_faces(img)
    results = []
    alerts = []
    
    for face in faces:
        if face.embedding is not None:
            # First match to find best candidate
            best_match_id, sim_score = matcher.match(face.embedding)

            # Get per-person threshold if available
            threshold = 0.55  # Default threshold
            if best_match_id:
                person = db.query(MissingPerson).filter(MissingPerson.person_id == best_match_id).first()
                if person and person.match_threshold:
                    threshold = person.match_threshold

            result = {
                "bbox": face.bbox.astype(int).tolist(),
                "best_match_id": best_match_id,
                "similarity_score": float(sim_score) if best_match_id else 0.0,
                "threshold_used": threshold
            }
            results.append(result)

            if best_match_id and sim_score >= threshold:
                alerts.append({
                    "person_id": best_match_id,
                    "confidence": float(sim_score),
                    "camera_id": body.camera_id
                })

    return {
        "camera_id": body.camera_id,
        "face_count": len(faces),
        "detections": results,
        "alerts": alerts
    }


@router.post("/process-video")
async def process_video(
    file: UploadFile = File(...),
    camera_id: str = "video_upload",
    frame_skip: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept an uploaded video file, sample frames at the given interval,
    apply the same preprocessing pipeline as the live feed (CLAHE + denoising),
    detect faces and match against the missing persons database.
    Returns per-frame results and a consolidated alert list.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a video.")

    # Write the upload to a temp file so OpenCV can read it
    suffix = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video file.")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0

        frame_results = []
        all_alerts = []
        frame_count = 0
        processed_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            # Sample every `frame_skip` frames (default every 30 frames ≈ 1 s at 30 fps)
            if frame_count % frame_skip != 0:
                continue

            # ── Apply the same preprocessing as live feed ──────────────────────
            processed_frame = preprocess_frame(frame)
            # ──────────────────────────────────────────────────────────────────

            faces = detect_faces(processed_frame)
            processed_count += 1
            timestamp_sec = round(frame_count / fps, 2)

            frame_detections = []
            for face in faces:
                if face.embedding is None:
                    continue

                best_match_id, sim_score = matcher.match(face.embedding)

                threshold = 0.55
                if best_match_id:
                    person = db.query(MissingPerson).filter(
                        MissingPerson.person_id == best_match_id
                    ).first()
                    if person and person.match_threshold:
                        threshold = person.match_threshold

                detection = {
                    "bbox": face.bbox.astype(int).tolist(),
                    "best_match_id": best_match_id,
                    "similarity_score": float(sim_score) if best_match_id else 0.0,
                    "threshold_used": threshold,
                    "is_match": bool(best_match_id and sim_score >= threshold),
                }
                frame_detections.append(detection)

                if best_match_id and sim_score >= threshold:
                    all_alerts.append({
                        "person_id": best_match_id,
                        "confidence": float(sim_score),
                        "camera_id": camera_id,
                        "timestamp_sec": timestamp_sec,
                    })

            if frame_detections:
                frame_results.append({
                    "frame_index": frame_count,
                    "timestamp_sec": timestamp_sec,
                    "detections": frame_detections,
                })

        cap.release()
    finally:
        os.unlink(tmp_path)

    return {
        "camera_id": camera_id,
        "video_duration_sec": duration_sec,
        "total_frames_in_video": total_frames,
        "frames_analyzed": processed_count,
        "frames_with_detections": len(frame_results),
        "frame_results": frame_results,
        "alerts": all_alerts,
    }
