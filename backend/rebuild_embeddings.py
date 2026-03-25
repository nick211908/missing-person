import cv2
import numpy as np
import os
from app.database.db import SessionLocal, MissingPerson, PersonImage
from app.services.face_detector import detect_faces
from app.services.matcher import matcher
from app.services.quality_assessment import assess_face_quality
from app.services.preprocessor import preprocess_face_roi
from app.config import settings

def rebuild():
    print(f"Starting DB Rebuild with Model: {settings.FACE_MODEL}...")
    db = SessionLocal()
    persons = db.query(MissingPerson).all()
    
    # Clear existing memory embeddings before rebuilding
    matcher.embeddings = {}
    
    total_processed = 0
    total_failed = 0
    
    for person in persons:
        print(f"Processing Person {person.person_id}: {person.name}")
        for img_record in person.images:
            img_path = img_record.image_path
            # Check if path is relative or absolute
            if not os.path.isabs(img_path):
                img_full_path = os.path.join("data/missing_persons", os.path.basename(img_path))
            else:
                img_full_path = img_path
                
            if not os.path.exists(img_full_path):
                print(f"  FAILED: Image not found at {img_full_path}")
                total_failed += 1
                continue
                
            img = cv2.imread(img_full_path)
            if img is None:
                print(f"  FAILED: Could not decode image at {img_full_path}")
                total_failed += 1
                continue
                
            # Detect
            faces = detect_faces(img)
            if not faces:
                print(f"  WARNING: No face detected in {img_full_path}")
                total_failed += 1
                continue
                
            # Take the best face (highest confidence)
            face = sorted(faces, key=lambda x: x.confidence, reverse=True)[0]
            
            # Sub-cropping for quality assessment
            bbox = face.bbox.astype(int)
            x, y, x2, y2 = max(0, bbox[0]), max(0, bbox[1]), min(img.shape[1], bbox[2]), min(img.shape[0], bbox[3])
            face_roi = img[y:y2, x:x2]
            
            # Quality assessment
            quality = assess_face_quality(face_roi)
            
            # Update DB with quality metadata
            img_record.blur_score = quality.blur_score
            img_record.yaw_angle = quality.yaw
            img_record.pitch_angle = quality.pitch
            img_record.quality_score = quality.quality_score
            
            # Enhance face ROI before adding to matcher (optional, deepface handles its own resize)
            # but we use it for consistency
            
            # Add to matcher
            matcher.add_person_embedding(person.person_id, face.embedding)
            total_processed += 1
            print(f"  SUCCESS: Added embedding (Similarity Confidence: {face.confidence:.2f}, Blur: {quality.blur_score:.1f})")
            
    db.commit()
    matcher.save_db()
    db.close()
    print(f"\nRebuild Finished!")
    print(f"Successfully processed: {total_processed}")
    print(f"Failed/Skipped: {total_failed}")

if __name__ == "__main__":
    rebuild()
