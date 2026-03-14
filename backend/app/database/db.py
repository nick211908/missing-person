from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, LargeBinary, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from app.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class MissingPerson(Base):
    __tablename__ = "missing_persons"

    person_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    last_seen_location = Column(String, nullable=True)   # Reverse-geocoded address
    date_added = Column(DateTime, default=datetime.utcnow)
    match_threshold = Column(Float, nullable=True)  # Per-person calibrated threshold

    # Relationship to multiple images
    images = relationship("PersonImage", back_populates="person", cascade="all, delete-orphan")

class PersonImage(Base):
    __tablename__ = "person_images"

    image_id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("missing_persons.person_id"), nullable=False)
    image_path = Column(String, nullable=False)
    embedding_index = Column(Integer, default=0)  # Index in the matcher embeddings list
    date_added = Column(DateTime, default=datetime.utcnow)

    person = relationship("MissingPerson", back_populates="images")

class DetectionEvent(Base):
    __tablename__ = "detection_events"

    event_id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, index=True)
    camera_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    similarity_score = Column(Float)
    snapshot_path = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
