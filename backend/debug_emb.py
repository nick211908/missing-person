import pickle
import numpy as np
import cv2
import os
from deepface import DeepFace
from app.config import settings

def debug():
    db_path = "c:/Users/Acer/Desktop/face-detection/missing-person-ai/backend/embeddings/db_embeddings.pkl"
    img_path = "c:/Users/Acer/Desktop/face-detection/missing-person-ai/backend/data/missing_persons/1_972e2aceb5ed46928a2a2981cd5b1070.jpg"
    
    # 1. Load from DB
    with open(db_path, "rb") as f:
        data = pickle.load(f)
        db_emb = np.array(data[1]['embeddings'][0])
        print(f"DB Embedding shape: {db_emb.shape}")
        print(f"DB Embedding first 5: {db_emb.flatten()[:5]}")

    # 2. Extract freshly
    img = cv2.imread(img_path)
    reps = DeepFace.represent(img_path=img, model_name=settings.FACE_MODEL, detector_backend=settings.DETECTOR_BACKEND, enforce_detection=False)
    fresh_emb = np.array(reps[0]['embedding'])
    print(f"Fresh Embedding shape: {fresh_emb.shape}")
    print(f"Fresh Embedding first 5: {fresh_emb.flatten()[:5]}")

    # 3. Compare
    from sklearn.metrics.pairwise import cosine_similarity
    sim = cosine_similarity(db_emb.reshape(1, -1), fresh_emb.reshape(1, -1))[0][0]
    print(f"Direct Cosine Similarity: {sim}")

if __name__ == "__main__":
    debug()
