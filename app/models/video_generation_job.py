from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Integer, String, Text

from app.db.db import Base


class VideoGenerationJob(Base):
    """Durable state for a VideoAgent generation request.

    The VideoAgent owns the rendering task; this table owns the application
    metadata and the eventual Education persistence state.
    """

    __tablename__ = "video_generation_job"

    task_id = Column(String(100), primary_key=True)
    company_id = Column(BigInteger, ForeignKey("company.company_id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_uid = Column(BigInteger, ForeignKey("user.uid", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=True)
    category = Column(String(100), nullable=True)
    education_type = Column(String(50), nullable=True)
    due_date = Column(Date, nullable=True)

    agent_status = Column(String(30), nullable=False, default="PENDING")
    progress_percent = Column(Integer, nullable=False, default=0)
    publication_status = Column(String(30), nullable=False, default="QUEUED")
    video_url = Column(String(500), nullable=True)
    quality_report_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    education_id = Column(BigInteger, ForeignKey("education.education_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
