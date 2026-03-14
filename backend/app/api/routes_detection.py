from fastapi import APIRouter, Depends, HTTPException
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
