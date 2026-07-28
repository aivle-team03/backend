from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base

class Inspection(Base):
    __tablename__ = "inspection"

    inspection_id = Column(BigInteger, primary_key=True)                                  # PK
    company_id = Column(BigInteger, ForeignKey("company.company_id"), nullable=False)     # FK (회사 아이디)
    name = Column(String(250), nullable=False)                                           # 점검 이름
    category = Column(String(100), nullable=False)                                        # 카테고리
    location = Column(String(100), nullable=False)                                            # 구역
    cycle = Column(String(50), nullable=False)                                            # 점검 주기 (매일, 매주 등)
    content = Column(String(250), nullable=True)

    company = relationship("Company")
    histories = relationship("InspectionHistory", back_populates="inspection")