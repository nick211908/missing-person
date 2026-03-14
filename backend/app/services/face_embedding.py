import numpy as np
from app.services.face_detector import detect_faces

def get_face_embeddings(img: np.ndarray):
    """
    Detect faces and return their 512-D embeddings.
    """
    faces = detect_faces(img, get_embedding=True)
    embeddings = []
    bboxes = []
    
    for face in faces:
        if face.embedding is not None:
            embeddings.append(face.embedding)
            bboxes.append(face.bbox.astype(int).tolist())
            
    return embeddings, bboxes

def get_single_face_embedding(img: np.ndarray):
    """
    Returns the embedding of the largest face in the image.
    Used for uploading a missing person's clear photo.
    """
    faces = detect_faces(img, get_embedding=True)
    if not faces:
        return None
        
    # Find largest face by bounding box area (width * height)
    largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return largest_face.embedding
