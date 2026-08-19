from sqlalchemy import BigInteger, Column, String, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship

from app.db.db import Base


class Education(Base):
    __tablename__ = "education"

    education_id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_id = Column(
        BigInteger,
        ForeignKey("company.company_id", ondelete="CASCADE"),
        nullable=False,
    )  # 회사 아이디
    title = Column(String(200), nullable=False)
    video_url = Column(String(500), nullable=False)     # 한국어 영상
    video_url_en = Column(String(500), nullable=True)   # 영어 영상. 없으면 video_url 로 폴백
    category = Column(String(100), nullable=False)      # 카테고리(공통, 지게차, 화재)
    type = Column(String(50), nullable=False)           # 구분 (예: 필수, 정기)
    due_date = Column(Date, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)


    statuses = relationship(
        "EducationStatus",
        back_populates="education",
        cascade="all, delete-orphan",
    )
    company = relationship("Company")
