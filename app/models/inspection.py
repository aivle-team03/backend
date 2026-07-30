from sqlalchemy import Column, BigInteger, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.db import Base

class Inspection(Base):
    __tablename__ = "inspection"

    inspection_id = Column(BigInteger, primary_key=True)                                  # PK
    company_id = Column(BigInteger, ForeignKey("company.company_id"), nullable=False)     # FK (회사 아이디)
    category_id = Column(BigInteger, ForeignKey("event_category.category_id"), nullable=False) # FK (카테고리 아이디)
    uid = Column(BigInteger, ForeignKey("user.uid"), nullable=True)                      # 담당자
    name = Column(String(100), nullable=False)                                           # 점검 이름
    location = Column(String(250), nullable=False)                                        # 점검 구역 (,로 구역 구분)
    cycle = Column(String(50), nullable=False)                                            # 점검 주기 (매일, 매주 등)
    content = Column(Text, nullable=True)   

    company = relationship("Company")
    histories = relationship("InspectionHistory", back_populates="inspection")
    category = relationship("EventCategory", backref="inspections")
    user = relationship("User", back_populates="inspections")