from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.db import Base


class Report(Base):
    __tablename__ = "report"

    report_id = Column(BigInteger, primary_key=True)                          # PK
    uid = Column(BigInteger, ForeignKey("user.uid"), nullable=False)          # FK (작성자)
    content = Column(String(255), nullable=False)                             # 보고서 내용
    summary = Column(String(100), nullable=False)                             # 요약
    created_at = Column(DateTime, nullable=False, server_default=func.now())  # 생성일

    user = relationship("User", back_populates="reports")
    event_maps = relationship("ReportEventMap", back_populates="report")
    checklist_maps = relationship("ReportChecklistMap", back_populates="report")
