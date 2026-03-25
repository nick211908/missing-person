from pydantic import BaseModel, computed_field
from typing import List, Optional
from datetime import datetime

class PersonImageResponse(BaseModel):
    image_id: int
    image_path: str
    embedding_index: Optional[int] = 0
    date_added: Optional[datetime] = None

    class Config:
        from_attributes = True

class MissingPersonBase(BaseModel):
    name: str

class MissingPersonCreate(MissingPersonBase):
    pass

class MissingPersonResponse(MissingPersonBase):
    person_id: int
    name: str
    description: Optional[str] = None
    last_seen_location: Optional[str] = None
    date_added: datetime
    match_threshold: Optional[float] = None
    images: List[PersonImageResponse] = []

    @computed_field
    @property
    def image_path(self) -> Optional[str]:
        """Return the first image path for backward compatibility."""
        if self.images and len(self.images) > 0:
            return self.images[0].image_path
        return None

    class Config:
        from_attributes = True

class DetectionEventResponse(BaseModel):
    event_id: int
    person_id: int
    camera_id: str
    timestamp: datetime
    similarity_score: float
    snapshot_path: Optional[str] = None
    person_name: Optional[str] = None

    class Config:
        from_attributes = True

class StreamStartRequest(BaseModel):
    camera_url: str
    camera_id: str


class PhoneCameraSession(BaseModel):
    """Schema for active phone camera sessions."""
    session_id: str
    camera_id: str
    device_info: Optional[str] = None
    connected_at: datetime
    last_frame_at: Optional[datetime] = None
    status: str  # "connected", "streaming", "disconnected", "error"
    frames_processed: int = 0
    faces_detected: int = 0
    matches_found: int = 0
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True


class PhoneCameraScanRequest(BaseModel):
    """Request to initiate a phone camera scan."""
    camera_id: str
    device_name: Optional[str] = None
    location: Optional[str] = None
    scan_mode: str = "realtime"  # "realtime" or "snapshot"


class PhoneCameraScanResponse(BaseModel):
    """Response for scan initiation."""
    session_id: str
    camera_id: str
    websocket_url: str
    status: str
    message: str


class PhoneCameraFrameRequest(BaseModel):
    """Request for processing a single frame from phone camera."""
    frame: str  # base64 encoded image
    camera_id: str
    timestamp: Optional[datetime] = None
    location: Optional[str] = None
    metadata: Optional[dict] = None


class PhoneCameraDetectionResult(BaseModel):
    """Result of face detection from phone camera."""
    bbox: List[int]
    best_match_id: Optional[int] = None
    similarity_score: float
    threshold_used: float
    is_match: bool
    person_name: Optional[str] = None


class PhoneCameraFrameResponse(BaseModel):
    """Response after processing a phone camera frame."""
    status: str
    face_count: int
    detections: List[PhoneCameraDetectionResult]
    alerts: List[dict]
    timestamp: float
    processing_time_ms: Optional[float] = None
