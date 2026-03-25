import cv2
import numpy as np
import os
from app.database.db import SessionLocal, MissingPerson, PersonImage
from app.services.face_detector import detect_faces
from app.services.matcher import matcher
from app.config import settings

def diagnostic_rebuild():
    print(f"DIAGNOSTIC REBUILD with Model: {settings.FACE_MODEL}")
    db = SessionLocal()
    persons = db.query(MissingPerson).all()
    matcher.embeddings = {}
    
    for person in persons:
        print(f"Person: {person.name}")
        for img_record in person.images:
            img_path = os.path.join("c:/Users/Acer/Desktop/face-detection/missing-person-ai/backend/data/missing_persons", os.path.basename(img_record.image_path))
            img = cv2.imread(img_path)
            if img is None: continue
            
            # Use direct DeepFace call to bypass any service logic
            from deepface import DeepFace
            reps = DeepFace.represent(img_path=img, model_name=settings.FACE_MODEL, detector_backend=settings.DETECTOR_BACKEND, enforce_detection=False)
            
            if reps:
                emb = np.array(reps[0]['embedding'])
                print(f"  Img: {os.path.basename(img_path)}")
                print(f"  Emb Shape: {emb.shape}")
                print(f"  Emb Sum: {np.sum(emb)}")
                print(f"  Emb Var: {np.var(emb)}")
                print(f"  Emb first 5: {emb[:5]}")
                
                matcher.add_person_embedding(person.person_id, emb)
            else:
                print(f"  Img: {os.path.basename(img_path)} -> NO FACE")
                
    db.commit()
    matcher.save_db()
    db.close()
    print("Diagnostic Rebuild Finished")

if __name__ == "__main__":
    diagnostic_rebuild()
