from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base

class ReportEventMap(Base):
    __tablename__ = "report_event_map"

    report_id = Column(BigInteger, ForeignKey("report.report_id", ondelete="CASCADE"), primary_key=True)
    event_id = Column(BigInteger, ForeignKey("event.event_id", ondelete="CASCADE"), primary_key=True)

    report = relationship("Report", back_populates="event_maps")
    event = relationship("Event", back_populates="report_maps")