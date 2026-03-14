import cv2
import numpy as np
from deepface import DeepFace

class FaceResult:
    def __init__(self, bbox, embedding):
        self.bbox = bbox # [x, y, x+w, y+h]
        self.embedding = embedding

def detect_faces(img: np.ndarray, get_embedding=True):
    """
    Detect faces in an image using DeepFace.
    Returns a list of FaceResult objects (contains bbox and embedding).
    """
    try:
        # DeepFace extract_faces returns a list of dictionaries.
        # Enforce exactly one detection run if we only need bbox, but to be safe and fast
        # we can just use the 'represent' function directly which does detection + embedding.
        
        results = []
        if get_embedding:
            # Use ArcFace (512-dim) natively supported by DeepFace, 
            # with opencv backend for face detection
            reps = DeepFace.represent(
                img_path=img,
                model_name="ArcFace",
                detector_backend="retinaface",
                enforce_detection=False
            )
            
            for rep in reps:
                if rep.get("face_confidence", 0) > 0:
                    area = rep["facial_area"]
                    bbox = np.array([area["x"], area["y"], area["x"] + area["w"], area["y"] + area["h"]])
                    embedding = np.array(rep["embedding"])
                    results.append(FaceResult(bbox=bbox, embedding=embedding))
        else:
            # Just face extraction
            faces = DeepFace.extract_faces(
                img_path=img,
                detector_backend="retinaface",
                enforce_detection=False
            )
            for face in faces:
                if face.get("confidence", 0) > 0:
                    area = face["facial_area"]
                    bbox = np.array([area["x"], area["y"], area["x"] + area["w"], area["y"] + area["h"]])
                    results.append(FaceResult(bbox=bbox, embedding=None))
                    
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
