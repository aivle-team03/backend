from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base


class ReportEventMap(Base):
    __tablename__ = "report_event_map"

    map_id = Column(BigInteger, primary_key=True)                             # PK
    report_id = Column(BigInteger, ForeignKey("report.report_id"), nullable=False) # FK
    event_id = Column(BigInteger, ForeignKey("event.event_id"), nullable=False)  # FK

    report = relationship("Report", back_populates="event_maps")
    event = relationship("Event", back_populates="report_maps")
