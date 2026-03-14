from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Missing Person AI"
    SIMILARITY_THRESHOLD: float = 0.55
    DATABASE_URL: str = "sqlite:///./missing_persons.db"
    EMBEDDING_DB_PATH: str = "embeddings/db_embeddings.pkl"
    MISSING_PERSONS_DIR: str = "data/missing_persons"

    class Config:
        env_file = ".env"

settings = Settings()
