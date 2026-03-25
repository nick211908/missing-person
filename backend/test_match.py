import cv2
import numpy as np
import os
from app.services.face_detector import detect_faces
from app.services.matcher import matcher
from app.config import settings

def test():
    print(f"Testing with Model: {settings.FACE_MODEL}, Detector: {settings.DETECTOR_BACKEND}")
    # Choose a filename from the list_dir output
    img_name = "1_972e2aceb5ed46928a2a2981cd5b1070.jpg"
    img_path = os.path.join("c:/Users/Acer/Desktop/face-detection/missing-person-ai/backend/data/missing_persons", img_name)
    
    img = cv2.imread(img_path)
    if img is None:
        print(f"Image not found at {img_path}")
        return

    print("Image loaded. Starting detection...")
    faces = detect_faces(img)
    print(f"Detected {len(faces)} faces")
    for face in faces:
        print(f"Face confidence: {face.confidence}")
        if face.embedding is not None:
            best_id, sim = matcher.match(face.embedding)
            print(f"Match results: Best ID: {best_id}, Similarity: {sim}")
        else:
            print("Face embedding is None")

if __name__ == "__main__":
    test()
