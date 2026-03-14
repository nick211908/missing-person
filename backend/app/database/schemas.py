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
