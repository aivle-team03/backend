from sqlalchemy import BigInteger, Column, String, Date # Date(마감일) 추가
from sqlalchemy.orm import relationship

from app.db.db import Base


class Education(Base):
    __tablename__ = "education"

    education_id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    role = Column(String(50), nullable=False)           # 대상 (예: 신규 근로자, 일반 작업자, 특수 작업자, 안전 관리자)
    video_url = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)           # 구분 (예: 필수, 정기)
    due_date = Column(Date, nullable=True)              # 마감일(Date)

    statuses = relationship(
        "EducationStatus",
        back_populates="education",
        cascade="all, delete-orphan",
    )
