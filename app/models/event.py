from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.db import Base


class Event(Base):
    __tablename__ = "event"

    event_id = Column(BigInteger, primary_key=True)                           # PK
    company_id = Column(
        BigInteger,
        ForeignKey("company.company_id", ondelete="CASCADE"),
        nullable=False,
    )  # 회사 아이디
    category_id = Column(
        BigInteger,
        ForeignKey("event_category.category_id", ondelete="SET NULL"),
        nullable=True,
    )  # FK
    cctv_id = Column(
        BigInteger,
        ForeignKey("cctv.cctv_id", ondelete="SET NULL"),
        nullable=True,
    )  # FK
    date = Column(DateTime, nullable=False)                                   # 감지 일시
    image_url = Column(String(255), nullable=True)                            # 이미지 URL
    is_deleted = Column(Boolean, nullable=False, default=False)

    category = relationship("EventCategory", back_populates="events")
    cctv = relationship("CCTV", back_populates="events")
    checklists = relationship("Checklist", back_populates="event")
    report_maps = relationship("ReportEventMap", back_populates="event")
    company = relationship("Company")
