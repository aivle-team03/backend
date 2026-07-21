from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base


class ReportChecklistMap(Base):
    __tablename__ = "report_checklist_map"

    map_id = Column(BigInteger, primary_key=True)                             # PK
    report_id = Column(BigInteger, ForeignKey("report.report_id"), nullable=False) # FK
    checklist_id = Column(BigInteger, ForeignKey("checklist.checklist_id"), nullable=False) # FK

    report = relationship("Report", back_populates="checklist_maps")
    checklist = relationship("Checklist", back_populates="report_maps")
