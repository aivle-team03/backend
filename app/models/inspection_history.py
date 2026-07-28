from sqlalchemy import Column, BigInteger, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base

class InspectionHistory(Base):
    __tablename__ = "inspection_history"

    history_id = Column(BigInteger, primary_key=True)                                     # PK
    inspection_id = Column(BigInteger, ForeignKey("inspection.inspection_id"), nullable=False) # FK (점검 아이디)
    company_id = Column(BigInteger, ForeignKey("company.company_id"), nullable=False)     # FK (회사 아이디)
    date = Column(DateTime, nullable=False)                                       # 점검 일시
    uid = Column(String(100), nullable=False)                                             # 담당자
    status = Column(String(50), nullable=False)                                           # 점검 진행 상황 (진행중, 완료 등)
    is_action_required = Column(Boolean, nullable=False, default=False)                  # 조치로 넘어갔는지 여부
    content = Column(Text, nullable=True)                                                 # 내용

    inspection = relationship("Inspection", back_populates="histories")
    company = relationship("Company")