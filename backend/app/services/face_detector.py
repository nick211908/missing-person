import cv2  # type: ignore
import numpy as np  # type: ignore
from deepface import DeepFace  # type: ignore
from app.config import settings  # type: ignore

class FaceResult:
    def __init__(self, bbox, embedding, confidence=None):
        self.bbox = bbox  # [x, y, x+w, y+h]
        self.embedding = embedding
        self.confidence = confidence  # Face detection confidence

def detect_faces(img: np.ndarray, get_embedding=True, model_name=None, detector_backend=None):
    """
    Detect faces in an image using DeepFace.
    Returns a list of FaceResult objects (contains bbox and embedding).

    Args:
        img: BGR image (numpy array)
        get_embedding: Whether to extract embeddings
        model_name: Override model from settings (optional)
        detector_backend: Override detector from settings (optional)

    Returns:
        List of FaceResult objects
    """
    try:
        # Use configured model and detector unless overridden
        model = model_name if model_name else settings.FACE_MODEL
        detector = detector_backend if detector_backend else settings.DETECTOR_BACKEND

        results = []
        if get_embedding:
            # Use configured model for embedding extraction
            reps = DeepFace.represent(
                img_path=img,
                model_name=model,
                detector_backend=detector,
                enforce_detection=False
            )

            for rep in reps:
                confidence = rep.get("face_confidence", 0)
                if confidence > 0:
                    area = rep["facial_area"]
                    bbox = np.array([area["x"], area["y"], area["x"] + area["w"], area["y"] + area["h"]])
                    embedding = np.array(rep["embedding"])
                    results.append(FaceResult(bbox=bbox, embedding=embedding, confidence=confidence))
        else:
            # Just face extraction
            faces = DeepFace.extract_faces(
                img_path=img,
                detector_backend=detector,
                enforce_detection=False
            )
            for face in faces:
                confidence = face.get("confidence", 0)
                if confidence > 0:
                    area = face["facial_area"]
                    bbox = np.array([area["x"], area["y"], area["x"] + area["w"], area["y"] + area["h"]])
                    results.append(FaceResult(bbox=bbox, embedding=None, confidence=confidence))

        return results
    except Exception as e:
        print(f"DeepFace processing error: {e}")
        return []

def draw_faces(img: np.ndarray, faces):
    """
    Utility to draw bounding boxes on the image.
    """
    res_img = img.copy()
    for face in faces:
        bbox = face.bbox.astype(int)
        cv2.rectangle(res_img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 0, 255), 2)
    return res_img
