from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, func, Text, Boolean
from sqlalchemy.orm import relationship
from typing import List
from app.db.db import Base

class Report(Base):
    __tablename__ = "report"

    report_id = Column(BigInteger, primary_key=True, autoincrement=True)

    uid = Column(BigInteger, ForeignKey("user.uid", ondelete='SET NULL'), nullable=True)
    writer = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)
    summary = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    company_id = Column(BigInteger, ForeignKey("company.company_id", ondelete="CASCADE"), nullable=False)  #회사 아이디

    user = relationship("User", back_populates="reports")
    event_maps = relationship("ReportEventMap", back_populates="report", cascade="all, delete-orphan")
    company = relationship("Company")
    inspection_maps = relationship("ReportInspectionMap", back_populates="report", cascade="all, delete-orphan")
    action_maps = relationship(
        "ReportActionMap",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    is_deleted = Column(Boolean, nullable=False, default=False)

    @property
    def event_ids(self) -> List[int]:
        return [m.event_id for m in self.event_maps]

    @property
    def inspection_history_ids(self) -> List[int]:
        return [m.inspection_history_id for m in self.inspection_maps]

    @property
    def action_history_ids(self) -> List[int]:
        return [m.action_history_id for m in self.action_maps]
