from sqlalchemy import Column, BigInteger, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.db import Base


class CCTV(Base):
    __tablename__ = "cctv"

    cctv_id = Column(BigInteger, primary_key=True, autoincrement=True)              # PK

    cctv_name = Column(String(100), nullable=False)                    # CCTV 이름
    location = Column(String(255), nullable=False)                      # 위치
    stream_url = Column(String(255), nullable=False)                    # 스트림 URL
    status = Column(String(50), nullable=False)                         # 상태
    company_id = Column(BigInteger, ForeignKey("company.company_id", ondelete="CASCADE"), nullable=False)       # 회사 아이디
    is_deleted = Column(Boolean, nullable=False, default=False)


    events = relationship("Event", back_populates="cctv")
    checklists = relationship("Checklist", back_populates="cctv")
    company = relationship("Company")
