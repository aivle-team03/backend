<<<<<<< HEAD
from sqlalchemy import BigInteger, Column, String, ForeignKey
=======
from sqlalchemy import BigInteger, Column, String
>>>>>>> f099ac31cb02b8deb209a79802f83b7573b2ff93
from sqlalchemy.orm import relationship

from app.db.db import Base


class Education(Base):
    __tablename__ = "education"

    education_id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_id = Column(BigInteger, ForeignKey("company.company_id"), nullable=False)  #회사 아이디
    title = Column(String(200), nullable=False)
    video_url = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)      # 카테고리(공통, 지게차, 화재)
    type = Column(String(50), nullable=False)           # 구분 (예: 필수, 정기)


    statuses = relationship(
        "EducationStatus",
        back_populates="education",
        cascade="all, delete-orphan",
    )
    company = relationship("Company")
