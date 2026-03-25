from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # Existing
    PROJECT_NAME: str = "Missing Person AI"
    SIMILARITY_THRESHOLD: float = 0.55 # Updated default for ArcFace
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./missing_persons.db")
    EMBEDDING_DB_PATH: str = os.getenv("EMBEDDING_DB_PATH", "embeddings/db_embeddings.pkl")
    MISSING_PERSONS_DIR: str = os.getenv("MISSING_PERSONS_DIR", "data/missing_persons")

    # 1. Tracking
    TRACKING_ENABLED: bool = True
    CONSECUTIVE_MATCH_THRESHOLD: int = 3
    TRACK_MAX_AGE: int = 30
    TRACK_MIN_HITS: int = 2

    # 2. Quality Assessment
    QUALITY_FILTER_ENABLED: bool = True
    BLUR_THRESHOLD: float = 50.0  # Lowered for CCTV conditions
    MAX_YAW_ANGLE: float = 60.0  # More permissive for profile faces
    MAX_PITCH_ANGLE: float = 45.0  # More permissive for tilted faces

    # 3. Augmentation
    AUGMENTATION_ENABLED: bool = True
    AUGMENTATION_MAX_VARIATIONS: int = 6
    AUGMENTATION_BRIGHTNESS_RANGE: tuple = (0.6, 1.4)  # Wider range for CCTV
    AUGMENTATION_NOISE_STD: float = 15.0  # Higher noise for CCTV simulation

    # 4. Model
    FACE_MODEL: str = "ArcFace"
    DETECTOR_BACKEND: str = "retinaface"

    # 5. Threshold
    THRESHOLD_MIN: float = 0.50
    THRESHOLD_MAX: float = 0.80
    THRESHOLD_LOW_VARIANCE_DEFAULT: float = 0.65
    USE_KNN_MATCHING: bool = True  # Enabled for robust matching
    KNN_NEIGHBORS: int = 5  # Increased for better voting

    class Config:
        env_file = ".env"

settings = Settings()
