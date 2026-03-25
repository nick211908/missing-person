import cv2
import numpy as np


def preprocess_frame(img: np.ndarray) -> np.ndarray:
    """
    Preprocess a frame for better face detection and recognition.
    Applies CLAHE for brightness normalization and denoising for CCTV noise.

    Args:
        img: Input BGR image (numpy array)

    Returns:
        Preprocessed BGR image
    """
    if img is None or img.size == 0:
        return img

    # Create a copy to avoid modifying the original
    processed = img.copy()

    # CLAHE for brightness/contrast normalization
    # Convert to LAB color space for better control
    lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
    # Reduced clipLimit to preserve natural facial features
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    processed = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Lighter denoising to preserve facial features
    # Reduced h parameters to keep important details
    if processed.shape[0] >= 10 and processed.shape[1] >= 10:
        processed = cv2.fastNlMeansDenoisingColored(processed, None, 6, 6, 7, 21)

    return processed


def preprocess_face_roi(face_roi: np.ndarray, min_size: int = 100) -> np.ndarray:
    """
    Preprocess a detected face ROI before embedding extraction.
    Upscales small faces to ensure quality embeddings.

    Args:
        face_roi: The cropped face region (BGR)
        min_size: Minimum dimension for face ROI

    Returns:
        Preprocessed face ROI, potentially upscaled
    """
    if face_roi is None or face_roi.size == 0:
        return face_roi

    h, w = face_roi.shape[:2]

    # 1. Contrast enhancement (CLAHE) specifically on the face
    lab = cv2.cvtColor(face_roi, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    face_roi = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # 2. Aggressive upscaling for small faces - critical for CCTV
    # Upscale even larger faces slightly for better embedding extraction
    target_size = max(min_size, min(h, w))
    scale = target_size / max(min(h, w), 1)

    # More aggressive upscaling for very small faces
    if h < 60 or w < 60:
        scale = max(scale, 2.0)  # At least 2x for very small faces

    if scale != 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        # Use INTER_CUBIC for better quality upscaling
        face_roi = cv2.resize(face_roi, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    return face_roi
