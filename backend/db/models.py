from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from backend.db.database import Base

class VideoAnalysis(Base):
    __tablename__ = "video_analyses"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Video properties
    duration = Column(Float, nullable=True)
    frame_rate = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Analysis parameters
    nominal_freq = Column(Float, default=50.0)
    enf_source = Column(String, default="audio")  # audio, video, joint
    
    # Results serialized as JSON
    results = Column(JSON, nullable=True)
    # Includes:
    # - audio_enf: List of floats
    # - video_enf: List of floats
    # - time_axis: List of floats
    # - tampering_report: JSON object
    # - auth_report: JSON object
    
    report_path = Column(String, nullable=True)


class ReferenceENF(Base):
    __tablename__ = "reference_enfs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    grid_region = Column(String, nullable=False)  # e.g., "US_EAST", "UK", "EUROPE"
    nominal_freq = Column(Float, default=50.0)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # ENF values and timestamps
    # stored as JSON array of floats or timestamps
    timestamps = Column(JSON, nullable=False)
    frequencies = Column(JSON, nullable=False)
