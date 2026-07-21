from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from typing import List
from app.db.db import Base

class Report(Base):
    __tablename__ = "report"

    report_id = Column(BigInteger, primary_key=True)
    uid = Column(BigInteger, ForeignKey("user.uid"), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="reports")
    event_maps = relationship("ReportEventMap", back_populates="report", cascade="all, delete-orphan")
    checklist_maps = relationship("ReportChecklistMap", back_populates="report", cascade="all, delete-orphan")

    @property
    def event_ids(self) -> List[int]:
        return [m.event_id for m in self.event_maps]

    @property
    def checklist_ids(self) -> List[int]:
        return [m.checklist_id for m in self.checklist_maps]