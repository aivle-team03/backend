from sqlalchemy import Column, BigInteger, String
from sqlalchemy.orm import relationship
from app.db.db import Base


class CCTV(Base):
    __tablename__ = "cctv"

    camera_id = Column(BigInteger, primary_key=True)                          # PK
    camera_name = Column(String(100), nullable=False)                         # 카메라 이름
    location = Column(String(255), nullable=False)                            # 위치
    stream_url = Column(String(255), nullable=False)                          # 스트림 URL
    status = Column(String(50), nullable=False)                               # 상태

    events = relationship("Event", back_populates="cctv")
    checklists = relationship("Checklist", back_populates="cctv")
