from sqlalchemy import Column, BigInteger, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base

class InspectionHistory(Base):
    __tablename__ = "inspection_history"

    inspection_history_id = Column(BigInteger, primary_key=True)                                     # PK
    company_id = Column(BigInteger, ForeignKey("company.company_id"), nullable=False)     # FK (회사 아이디)
    inspection_id = Column(BigInteger, ForeignKey("inspection.inspection_id"), nullable=False) # FK (점검 아이디)
    uid = Column(
      BigInteger,
      ForeignKey('user.uid', ondelete='SET NULL'),
      nullable=True,
    ) 
    user_name = Column(String(100), nullable=True)
    name = Column(String(100), nullable=False) 
    location = Column(String(50), nullable=False)  
    date = Column(DateTime, nullable=False)                                       # 점검 일시
    status = Column(String(50), nullable=False)                                           # 점검 진행 상황 (점검 대기, 점검 완료)
    is_action_required = Column(Boolean, nullable=False, default=False)                  # 조치로 넘어갔는지 여부
    content = Column(Text, nullable=True)                                                 # 내용

    inspection = relationship("Inspection", back_populates="histories")
    company = relationship("Company")
    user = relationship("User", back_populates="inspection_histories")
    report_maps = relationship("ReportInspectionMap", back_populates="inspection_history", cascade="all, delete-orphan")