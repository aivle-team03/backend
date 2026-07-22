from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base


class Event(Base):
    __tablename__ = "event"

    event_id = Column(BigInteger, primary_key=True)                           # PK
    category_id = Column(BigInteger, ForeignKey("event_category.category_id"), nullable=False) # FK
    camera_id = Column(BigInteger, ForeignKey("cctv.cctv_id"), nullable=False) # FK
    date = Column(DateTime, nullable=False)                                   # 감지 일시
    image_url = Column(String(255), nullable=True)                            # 이미지 URL

    category = relationship("EventCategory", back_populates="events")
    cctv = relationship("CCTV", back_populates="events")
    checklists = relationship("Checklist", back_populates="event")
    report_maps = relationship("ReportEventMap", back_populates="event")
