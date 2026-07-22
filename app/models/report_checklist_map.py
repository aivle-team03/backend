from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base

class ReportChecklistMap(Base):
    __tablename__ = "report_checklist_map"

    report_id = Column(BigInteger, ForeignKey("report.report_id", ondelete="CASCADE"), primary_key=True)
    checklist_id = Column(BigInteger, ForeignKey("checklist.checklist_id", ondelete="CASCADE"), primary_key=True)

    report = relationship("Report", back_populates="checklist_maps")
    checklist = relationship("Checklist", back_populates="report_maps")