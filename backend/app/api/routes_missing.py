from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.db import get_db, MissingPerson, PersonImage
from app.database.schemas import MissingPersonResponse
from app.services.face_detector import detect_faces
from app.services.matcher import matcher
from app.auth.auth import get_current_user, require_admin
from app.models.user import User
from app.config import settings
import shutil
import uuid
import os
import cv2
import numpy as np

router = APIRouter()

@router.post("/upload-missing-person", response_model=MissingPersonResponse)
async def upload_missing_person(
    name: str = Form(...),
    description: str = Form(None),
    last_seen_location: str = Form(None),
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a missing person with multiple images (3-5 recommended).
    Supports both single 'file' (backward compatible) and multiple 'files'.
    """
    # Normalize to list of files
    file_list = []
    if files:
        file_list.extend(files)
    if file:
        file_list.append(file)

    if not file_list:
        raise HTTPException(status_code=400, detail="At least one image file is required.")

    if len(file_list) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 images allowed per person.")

    # Create the missing person record first
    new_person = MissingPerson(
        name=name,
        description=description,
        last_seen_location=last_seen_location
    )
    db.add(new_person)
    db.commit()
    db.refresh(new_person)

    embeddings = []
    saved_images = []

    os.makedirs(settings.MISSING_PERSONS_DIR, exist_ok=True)

    for idx, file in enumerate(file_list):
        # Save uploaded file
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ['jpg', 'jpeg', 'png']:
            continue  # Skip invalid files

        filename = f"{new_person.person_id}_{uuid.uuid4().hex}.{file_ext}"
        filepath = os.path.join(settings.MISSING_PERSONS_DIR, filename)

        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Read image and extract embedding
        img = cv2.imread(filepath)
        if img is None:
            continue  # Skip invalid images

        faces = detect_faces(img)
        if not faces:
            continue  # Skip images with no faces

        def face_area(f):
            b = f.bbox
            return (b[2] - b[0]) * (b[3] - b[1])

        largest_face = max(faces, key=face_area)

        if largest_face.embedding is not None:
            # Add embedding to matcher
            matcher.add_person_embedding(new_person.person_id, largest_face.embedding)
            embeddings.append(largest_face.embedding)

            # Create PersonImage record - store just the filename, not full path
            person_image = PersonImage(
                person_id=new_person.person_id,
                image_path=filename,  # Just the filename, not the full path
                embedding_index=len(embeddings) - 1
            )
            db.add(person_image)
            saved_images.append(person_image)

    if not embeddings:
        # Rollback - no valid faces found
        db.delete(new_person)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="No valid faces detected in any of the uploaded images. Please upload clear frontal or profile face photos."
        )

    # Compute per-person threshold based on self-similarity
    if len(embeddings) >= 2:
        mean_self_sim = matcher.compute_self_similarity(new_person.person_id)
        # Set threshold slightly below mean self-similarity
        calibrated_threshold = max(0.4, mean_self_sim - 0.05)
        new_person.match_threshold = calibrated_threshold

    db.commit()
    db.refresh(new_person)

    return new_person


@router.get("/missing-persons", response_model=list[MissingPersonResponse])
def get_missing_persons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    persons = db.query(MissingPerson).all()
    return persons


@router.delete("/missing-persons/{person_id}")
def delete_missing_person(
    person_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    person = db.query(MissingPerson).filter(MissingPerson.person_id == person_id).first()
    if not person:
        raise HTTPException(404, detail="Person not found.")

    # Delete associated image files
    for img in person.images:
        full_path = os.path.join(settings.MISSING_PERSONS_DIR, img.image_path)
        if os.path.exists(full_path):
            os.remove(full_path)

    db.delete(person)
    db.commit()
    matcher.remove_person(person_id)
    return {"detail": f"Person {person_id} deleted successfully."}
