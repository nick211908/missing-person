"""
Services module for face detection and matching.
"""

from app.services.face_detector import detect_faces
from app.services.face_embedding import get_face_embeddings, get_single_face_embedding
from app.services.matcher import matcher
from app.services.preprocessor import preprocess_frame
from app.services.stream_processor import stream_processor
from app.services.phone_camera_service import phone_camera_service, PhoneCameraSession

__all__ = [
    "detect_faces",
    "get_face_embeddings",
    "get_single_face_embedding",
    "matcher",
    "preprocess_frame",
    "stream_processor",
    "phone_camera_service",
    "PhoneCameraSession",
]
