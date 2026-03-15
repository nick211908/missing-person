"""
Face Image Augmentation Module.

Generates augmented variations of reference images to simulate CCTV conditions
and improve matching robustness.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from app.config import settings


class FaceAugmentor:
    """
    Augments face images to create variations for more robust embeddings.
    Simulates real-world conditions like lighting changes, blur, and noise.
    """

    def __init__(
        self,
        brightness_range: Tuple[float, float] = None,
        noise_std: float = None,
        max_variations: int = None
    ):
        """
        Initialize augmentor with settings.

        Args:
            brightness_range: (min_factor, max_factor) for brightness adjustment
            noise_std: Standard deviation for Gaussian noise
            max_variations: Maximum number of augmented variations to generate
        """
        self.brightness_range = brightness_range or settings.AUGMENTATION_BRIGHTNESS_RANGE
        self.noise_std = noise_std or settings.AUGMENTATION_NOISE_STD
        self.max_variations = max_variations or settings.AUGMENTATION_MAX_VARIATIONS

    def adjust_brightness(self, img: np.ndarray, factor: float) -> np.ndarray:
        """
        Adjust image brightness.

        Args:
            img: BGR image
            factor: Brightness multiplier (>1 brighter, <1 darker)

        Returns:
            Brightness-adjusted image
        """
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * factor, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    def adjust_contrast(self, img: np.ndarray, factor: float) -> np.ndarray:
        """
        Adjust image contrast.

        Args:
            img: BGR image
            factor: Contrast multiplier

        Returns:
            Contrast-adjusted image
        """
        return np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)

    def add_gaussian_noise(self, img: np.ndarray, std: float = None) -> np.ndarray:
        """
        Add Gaussian noise to image.

        Args:
            img: BGR image
            std: Standard deviation of noise

        Returns:
            Noisy image
        """
        noise_std = std if std is not None else self.noise_std
        noise = np.random.normal(0, noise_std, img.shape).astype(np.float32)
        noisy = img.astype(np.float32) + noise
        return np.clip(noisy, 0, 255).astype(np.uint8)

    def apply_motion_blur(self, img: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """
        Apply horizontal motion blur.

        Args:
            img: BGR image
            kernel_size: Size of blur kernel

        Returns:
            Blurred image
        """
        kernel = np.zeros((kernel_size, kernel_size))
        kernel[int((kernel_size - 1) / 2), :] = 1 / kernel_size
        return cv2.filter2D(img, -1, kernel)

    def apply_gaussian_blur(self, img: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """
        Apply Gaussian blur.

        Args:
            img: BGR image
            kernel_size: Size of blur kernel (must be odd)

        Returns:
            Blurred image
        """
        if kernel_size % 2 == 0:
            kernel_size += 1
        return cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)

    def horizontal_flip(self, img: np.ndarray) -> np.ndarray:
        """
        Flip image horizontally (mirror).

        Args:
            img: BGR image

        Returns:
            Flipped image
        """
        return cv2.flip(img, 1)

    def augment_image(self, img: np.ndarray, include_flip: bool = True) -> List[np.ndarray]:
        """
        Generate augmented variations of a face image.

        Applies various transformations to simulate different capture conditions:
        - Brightness variations (darker and brighter)
        - Contrast variations
        - Gaussian noise (CCTV noise simulation)
        - Motion blur
        - Gaussian blur
        - Horizontal flip (for frontal faces)

        Args:
            img: BGR face image
            include_flip: Whether to include horizontal flip variation

        Returns:
            List of augmented image variations (including original)
        """
        if img is None or img.size == 0:
            return []

        variations = [img]  # Always include original

        # Brightness variations
        min_b, max_b = self.brightness_range
        if min_b < 1.0:
            variations.append(self.adjust_brightness(img, min_b))
        if max_b > 1.0:
            variations.append(self.adjust_brightness(img, max_b))

        # Contrast variations
        variations.append(self.adjust_contrast(img, 0.8))
        variations.append(self.adjust_contrast(img, 1.2))

        # Noise variations
        variations.append(self.add_gaussian_noise(img))

        # Blur variations
        variations.append(self.apply_motion_blur(img))
        variations.append(self.apply_gaussian_blur(img))

        # Horizontal flip (only for frontal faces)
        if include_flip:
            variations.append(self.horizontal_flip(img))

        # Limit to max variations
        if len(variations) > self.max_variations:
            # Keep original and sample randomly
            np.random.seed(42)  # Reproducibility
            indices = [0] + list(np.random.choice(
                range(1, len(variations)),
                size=self.max_variations - 1,
                replace=False
            ))
            variations = [variations[i] for i in sorted(indices)]

        return variations

    def augment_for_cctv(self, img: np.ndarray) -> List[np.ndarray]:
        """
        Generate CCTV-optimized variations.
        Focuses on conditions commonly seen in surveillance footage.

        Args:
            img: BGR face image

        Returns:
            List of CCTV-simulated variations
        """
        if img is None or img.size == 0:
            return []

        variations = [img]  # Original

        # Low light simulation (common in indoor CCTV)
        variations.append(self.adjust_brightness(img, 0.7))

        # High contrast (outdoor CCTV)
        variations.append(self.adjust_contrast(img, 1.3))

        # Low resolution effect (distance from camera)
        h, w = img.shape[:2]
        small = cv2.resize(img, (max(w // 2, 32), max(h // 2, 32)))
        variations.append(cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR))

        # Compression artifacts simulation
        variations.append(self.add_gaussian_noise(img, std=15))

        # Motion blur (moving subjects)
        variations.append(self.apply_motion_blur(img, kernel_size=7))

        return variations[:self.max_variations]


# Global augmentor instance
_augmentor = None


def get_augmentor() -> FaceAugmentor:
    """Get or create global augmentor instance."""
    global _augmentor
    if _augmentor is None:
        _augmentor = FaceAugmentor()
    return _augmentor


def augment_image(img: np.ndarray, include_flip: bool = True) -> List[np.ndarray]:
    """
    Convenience function to augment an image using global augmentor.

    Args:
        img: BGR face image
        include_flip: Whether to include horizontal flip

    Returns:
        List of augmented variations
    """
    return get_augmentor().augment_image(img, include_flip=include_flip)