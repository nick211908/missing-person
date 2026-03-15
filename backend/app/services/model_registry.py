"""
Model Registry for DeepFace face recognition models.

Provides configuration and validation for supported face embedding models.
"""

from typing import Dict, List

# Supported DeepFace models for face recognition
SUPPORTED_MODELS = {
    'ArcFace': {
        'embedding_dim': 512,
        'description': 'ArcFace model - high accuracy, good for production'
    },
    'GhostFaceNet': {
        'embedding_dim': 512,
        'description': 'GhostFaceNet - lightweight, faster inference'
    },
    'Facenet512': {
        'embedding_dim': 512,
        'description': 'Facenet512 - FaceNet variant with 512-dim embeddings'
    },
    'Facenet': {
        'embedding_dim': 128,
        'description': 'Facenet - original FaceNet with 128-dim embeddings'
    },
    'VGG-Face': {
        'embedding_dim': 4096,
        'description': 'VGG-Face - older model, larger embeddings'
    },
    'SFace': {
        'embedding_dim': 128,
        'description': 'SFace - compact embeddings'
    },
}

# Supported detector backends
SUPPORTED_DETECTORS = {
    'retinaface': {'description': 'RetinaFace - high accuracy face detection'},
    'mtcnn': {'description': 'MTCNN - multi-task cascaded networks'},
    'opencv': {'description': 'OpenCV - fast, lower accuracy'},
    'ssd': {'description': 'SSD - single shot detector'},
    'dlib': {'description': 'Dlib - HOG/CNN based detection'},
    'skip': {'description': 'Skip detection - assume image is pre-cropped face'},
}


def get_model_info(model_name: str) -> Dict:
    """
    Get information about a face recognition model.

    Args:
        model_name: Name of the model (e.g., 'ArcFace')

    Returns:
        Dictionary with model information

    Raises:
        ValueError: If model is not supported
    """
    if model_name not in SUPPORTED_MODELS:
        raise ValueError(
            f"Model '{model_name}' not supported. "
            f"Available models: {list(SUPPORTED_MODELS.keys())}"
        )
    return SUPPORTED_MODELS[model_name]


def validate_model(model_name: str) -> bool:
    """
    Check if a model name is valid.

    Args:
        model_name: Name of the model to validate

    Returns:
        True if valid, False otherwise
    """
    return model_name in SUPPORTED_MODELS


def validate_detector(detector_name: str) -> bool:
    """
    Check if a detector backend name is valid.

    Args:
        detector_name: Name of the detector to validate

    Returns:
        True if valid, False otherwise
    """
    return detector_name in SUPPORTED_DETECTORS


def get_embedding_dimension(model_name: str) -> int:
    """
    Get the embedding dimension for a model.

    Args:
        model_name: Name of the model

    Returns:
        Embedding dimension (e.g., 512 for ArcFace)
    """
    info = get_model_info(model_name)
    return info['embedding_dim']


def list_models() -> List[str]:
    """
    Get list of supported model names.

    Returns:
        List of model names
    """
    return list(SUPPORTED_MODELS.keys())


def list_detectors() -> List[str]:
    """
    Get list of supported detector backend names.

    Returns:
        List of detector names
    """
    return list(SUPPORTED_DETECTORS.keys())