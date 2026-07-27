from sqlalchemy import BigInteger, Column, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.db import Base


class Education(Base):
    __tablename__ = "education"

    education_id = Column(BigInteger, primary_key=True, autoincrement=True)
<<<<<<< HEAD
    company_id = Column(BigInteger, ForeignKey("company.company_id"), nullable=False)  #회사 아이디
=======

>>>>>>> 7ed113320afa3b57587df0d79e1737a2c6d68b8d
    title = Column(String(200), nullable=False)
    role = Column(String(50), nullable=True)             # 권한 (전체, 일반 작업자 등)
    video_url = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)      # 카테고리(공통, 지게차, 화재)
    type = Column(String(50), nullable=False)           # 구분 (예: 필수, 정기)
    due_date = Column(Date, nullable=True)              # 마감일


    statuses = relationship(
        "EducationStatus",
        back_populates="education",
        cascade="all, delete-orphan",
    )
    company = relationship("Company")
