from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Missing Person AI"
    SIMILARITY_THRESHOLD: float = 0.55
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./missing_persons.db")
    EMBEDDING_DB_PATH: str = os.getenv("EMBEDDING_DB_PATH", "embeddings/db_embeddings.pkl")
    MISSING_PERSONS_DIR: str = os.getenv("MISSING_PERSONS_DIR", "data/missing_persons")

    class Config:
        env_file = ".env"

settings = Settings()
