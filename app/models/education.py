from sqlalchemy import BigInteger, Column, String, Date # Date(마감일) 추가
from sqlalchemy.orm import relationship

from app.db.db import Base


class Education(Base):
    __tablename__ = "education"

    education_id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    video_url = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)      # 카테고리(공통, 지게차, 화재)
    type = Column(String(50), nullable=False)           # 구분 (예: 필수, 정기)

    statuses = relationship(
        "EducationStatus",
        back_populates="education",
        cascade="all, delete-orphan",
    )
