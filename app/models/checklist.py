from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base


class Checklist(Base):
    __tablename__ = "checklist"

    checklist_id = Column(BigInteger, primary_key=True)                       # PK
    event_id = Column(BigInteger, ForeignKey("event.event_id"), nullable=True) # FK (Nullable)
    date = Column(DateTime, nullable=False)                                   # 점검 일시
    status = Column(String(50), nullable=False)                               # 조치 상태
    uid = Column(BigInteger, ForeignKey("user.uid"), nullable=False)          # FK (점검자)
    camera_id = Column(BigInteger, ForeignKey("cctv.camera_id"), nullable=False) # FK (점검 대상 CCTV)
    content = Column(String(255), nullable=False)                             # 내용
    image_url = Column(String(255), nullable=True)                            # 현장 이미지 URL

    event = relationship("Event", back_populates="checklists")
    user = relationship("User", back_populates="checklists")
    cctv = relationship("CCTV", back_populates="checklists")
    report_maps = relationship("ReportChecklistMap", back_populates="checklist")
