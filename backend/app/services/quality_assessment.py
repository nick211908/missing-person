"""
Face Quality Assessment (FIQA) module.

Provides blur detection and pose estimation to filter low-quality faces
before embedding extraction.
"""

import cv2
import numpy as np
from typing import Tuple, Optional, NamedTuple
from dataclasses import dataclass
from deepface import DeepFace


@dataclass
class QualityResult:
    """Result of face quality assessment."""
    accepted: bool
    quality_score: float
    blur_score: float
    yaw: Optional[float] = None
    pitch: Optional[float] = None
    rejection_reason: Optional[str] = None


def compute_blur_score(img: np.ndarray) -> float:
    """
    Compute blur score using Variance of Laplacian.
    Higher scores indicate sharper images.

    Args:
        img: BGR or grayscale image

    Returns:
        Float score - typically > 100 for sharp images
    """
    if img is None or img.size == 0:
        return 0.0

    # Convert to grayscale if needed
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # Variance of Laplacian
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def estimate_pose_angles(img: np.ndarray, detector_backend: str = "retinaface") -> Tuple[float, float, float]:
    """
    Estimate face pose angles (yaw, pitch, roll) using facial landmarks.

    Uses DeepFace's detector to extract landmarks, then computes pose.
    Falls back to (0, 0, 0) if estimation fails.

    Args:
        img: BGR image containing a face
        detector_backend: DeepFace detector backend to use

    Returns:
        Tuple of (yaw, pitch, roll) in degrees
    """
    default_pose = (0.0, 0.0, 0.0)

    if img is None or img.size == 0:
        return default_pose

    try:
        # Extract faces with landmarks
        faces = DeepFace.extract_faces(
            img_path=img,
            detector_backend=detector_backend,
            enforce_detection=False,
            align=False
        )

        if not faces or len(faces) == 0:
            return default_pose

        face = faces[0]

        # Get landmarks if available
        landmarks = face.get("facial_area", {})
        if not isinstance(landmarks, dict):
            return default_pose

        # RetinaFace provides landmarks as 'landmarks' key
        landmarks_data = landmarks.get("landmarks")
        if landmarks_data is None:
            return default_pose

        # Calculate pose from landmarks
        # Typical landmarks: left eye, right eye, nose, left mouth, right mouth
        if isinstance(landmarks_data, dict):
            left_eye = landmarks_data.get("left_eye")
            right_eye = landmarks_data.get("right_eye")
            nose = landmarks_data.get("nose")

            if left_eye and right_eye and nose:
                # Estimate yaw from eye-nose distances
                left_eye = np.array(left_eye)
                right_eye = np.array(right_eye)
                nose = np.array(nose)

                # Eye centers and midpoint
                eye_center = (left_eye + right_eye) / 2
                eye_distance = np.linalg.norm(right_eye - left_eye)

                if eye_distance > 0:
                    # Yaw: horizontal deviation of nose from eye center
                    nose_deviation = (nose[0] - eye_center[0]) / eye_distance
                    yaw = float(np.clip(nose_deviation * 90, -90, 90))

                    # Pitch: vertical deviation (simplified)
                    nose_vertical = (nose[1] - eye_center[1]) / eye_distance
                    pitch = float(np.clip(nose_vertical * 60, -60, 60))

                    # Roll: eye line angle
                    delta_y = right_eye[1] - left_eye[1]
                    delta_x = right_eye[0] - left_eye[0]
                    roll = float(np.degrees(np.arctan2(delta_y, delta_x)))

                    return (yaw, pitch, roll)

        return default_pose

    except Exception as e:
        print(f"Pose estimation error: {e}")
        return default_pose


def assess_face_quality(
    img: np.ndarray,
    blur_threshold: float = 50.0,
    max_yaw: float = 60.0,
    max_pitch: float = 45.0,
    detector_backend: str = "retinaface"
) -> QualityResult:
    """
    Assess face quality for embedding extraction.
    Relaxed thresholds for CCTV conditions.

    Args:
        img: BGR image of face region
        blur_threshold: Minimum variance of Laplacian for sharp images
        max_yaw: Maximum allowed yaw angle in degrees
        max_pitch: Maximum allowed pitch angle in degrees
        detector_backend: DeepFace detector for pose estimation

    Returns:
        QualityResult with acceptance status and scores
    """
    if img is None or img.size == 0:
        return QualityResult(
            accepted=False,
            quality_score=0.0,
            blur_score=0.0,
            rejection_reason="Empty or invalid image"
        )

    # Compute blur score
    blur_score = compute_blur_score(img)

    # More permissive blur check - allow slightly blurry faces for CCTV
    if blur_score < blur_threshold * 0.5:  # Accept faces at 50% of threshold
        return QualityResult(
            accepted=False,
            quality_score=blur_score / blur_threshold,
            blur_score=blur_score,
            rejection_reason=f"Image too blurry (score: {blur_score:.1f}, minimum: {blur_threshold * 0.5:.1f})"
        )

    # Estimate pose
    yaw, pitch, roll = estimate_pose_angles(img, detector_backend)

    # Check pose constraints with wider tolerance
    abs_yaw = abs(yaw)
    abs_pitch = abs(pitch)

    if abs_yaw > max_yaw:
        return QualityResult(
            accepted=False,
            quality_score=blur_score / blur_threshold * 0.5,
            blur_score=blur_score,
            yaw=yaw,
            pitch=pitch,
            rejection_reason=f"Yaw angle too extreme ({yaw:.1f}°, max: {max_yaw}°)"
        )

    if abs_pitch > max_pitch:
        return QualityResult(
            accepted=False,
            quality_score=blur_score / blur_threshold * 0.5,
            blur_score=blur_score,
            yaw=yaw,
            pitch=pitch,
            rejection_reason=f"Pitch angle too extreme ({pitch:.1f}°, max: {max_pitch}°)"
        )

    # Compute overall quality score with weighted formula
    # Blur is more important than pose for recognition
    blur_factor = min(blur_score / blur_threshold, 1.5)
    pose_factor = 1.0 - (abs_yaw / 120 + abs_pitch / 90) / 2  # More permissive scaling
    quality_score = (blur_factor * 0.7 + pose_factor * 0.3)  # Weight blur more heavily

    return QualityResult(
        accepted=True,
        quality_score=quality_score,
        blur_score=blur_score,
        yaw=yaw,
        pitch=pitch
    )