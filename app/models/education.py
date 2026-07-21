from sqlalchemy import BigInteger, Column, String
from sqlalchemy.orm import relationship

from app.db.db import Base


class Education(Base):
    __tablename__ = "education"

    education_id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    role = Column(String(50), nullable=False)
    video_url = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)

    statuses = relationship(
        "EducationStatus",
        back_populates="education",
        cascade="all, delete-orphan",
    )
