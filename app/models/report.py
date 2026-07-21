from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from typing import List
from app.db.db import Base


class Report(Base):
    __tablename__ = "report"

    report_id = Column(BigInteger, primary_key=True)                          # PK
    uid = Column(BigInteger, ForeignKey("user.uid"), nullable=False)          # FK (작성자)
    
    # [Point A] 보고서 본문이라면 보통 255자를 넘어가므로 String(255) 대신 Text 사용 권장
    content = Column(Text, nullable=False)                                    # 보고서 내용
    summary = Column(String(100), nullable=False)                             # 요약
    created_at = Column(DateTime, nullable=False, server_default=func.now())  # 생성일

    user = relationship("User", back_populates="reports")
    
    # [Point B] cascade="all, delete-orphan" 추가
    # Report가 삭제될 때 연결된 Map 데이터도 DB에서 자동으로 함께 삭제해 줍니다.
    event_maps = relationship("ReportEventMap", back_populates="report", cascade="all, delete-orphan")
    checklist_maps = relationship("ReportChecklistMap", back_populates="report", cascade="all, delete-orphan")

    # ==========================================
    # Pydantic Schema 매핑을 위한 Property 영역
    # ==========================================
    @property
    def event_ids(self) -> List[int]:
        """Schema의 event_ids와 자동 매핑"""
        return [m.event_id for m in self.event_maps]

    @property
    def checklist_ids(self) -> List[int]:
        """Schema의 checklist_ids와 자동 매핑"""
        return [m.checklist_id for m in self.checklist_maps]