from fastapi import APIRouter, Depends, HTTPException, UploadFile, File  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from app.database.db import get_db, DetectionEvent, MissingPerson  # type: ignore
from app.database.schemas import DetectionEventResponse  # type: ignore
from app.services.face_detector import detect_faces  # type: ignore
from app.services.matcher import matcher  # type: ignore
from app.services.preprocessor import preprocess_frame, preprocess_face_roi  # type: ignore
from app.services.quality_assessment import assess_face_quality  # type: ignore
from app.config import settings  # type: ignore
from app.auth.auth import get_current_user  # type: ignore
from app.models.user import User  # type: ignore
from pydantic import BaseModel  # type: ignore
from typing import Optional
import cv2  # type: ignore
import numpy as np  # type: ignore
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
    events_with_names = (
        db.query(DetectionEvent, MissingPerson.name.label("person_name"))
        .outerjoin(MissingPerson, DetectionEvent.person_id == MissingPerson.person_id)
        .order_by(DetectionEvent.timestamp.desc())
        .limit(100)
        .all()
    )
    
    result = []
    for evt, p_name in events_with_names:
        evt_dict = evt.__dict__.copy()
        evt_dict["person_name"] = p_name
        result.append(evt_dict)
        
    return result

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
            # Match using KNN (enabled in settings) for robust matching
            best_match_id, sim_score = matcher.match(face.embedding)

            # Get per-person threshold if available, otherwise use default
            threshold = settings.THRESHOLD_LOW_VARIANCE_DEFAULT
            if best_match_id:
                person = db.query(MissingPerson).filter(MissingPerson.person_id == best_match_id).first()
                if person and person.match_threshold:
                    threshold = person.match_threshold

            is_match = best_match_id is not None and float(sim_score) >= float(threshold)

            result = {
                "bbox": face.bbox.astype(int).tolist(),
                "best_match_id": best_match_id,
                "similarity_score": float(sim_score) if best_match_id else 0.0,
                "threshold_used": threshold,
                "is_match": is_match
            }
            results.append(result)

            if is_match:
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

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration_sec = float(total_frames) / fps if fps > 0 else 0.0

        frame_results: list = []
        all_alerts: list = []
        frame_count: int = 0
        processed_count: int = 0

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
            processed_count += 1  # type: ignore
            timestamp_sec = round(float(frame_count) / fps, 2)  # type: ignore

            frame_detections = []
            
            if len(faces) > 0:
                for i, face in enumerate(faces):
                    if face.embedding is None:
                        continue

                    # Use KNN matching for robust results
                    best_match_id, sim_score = matcher.match(face.embedding)

                    # Get per-person threshold
                    threshold = settings.THRESHOLD_LOW_VARIANCE_DEFAULT
                    if best_match_id:
                        person = db.query(MissingPerson).filter(
                            MissingPerson.person_id == best_match_id
                        ).first()
                        if person and person.match_threshold:
                            threshold = person.match_threshold

                    is_match = best_match_id is not None and sim_score >= threshold

                    detection = {
                        "bbox": face.bbox.astype(int).tolist(),
                        "best_match_id": best_match_id,
                        "similarity_score": float(sim_score) if best_match_id else 0.0,
                        "threshold_used": threshold,
                        "is_match": is_match,
                        "track_id": i
                    }
                    frame_detections.append(detection)

                    if is_match:
                        all_alerts.append({
                            "person_id": best_match_id,
                            "confidence": float(sim_score),
                            "camera_id": camera_id,
                            "timestamp_sec": timestamp_sec,
                            "track_id": i
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
