from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base


class Checklist(Base):
    __tablename__ = "checklist"

    checklist_id = Column(BigInteger, primary_key=True, autoincrement=True)         # PK

    event_id = Column(
        BigInteger,
        ForeignKey("event.event_id", ondelete="SET NULL"),
        nullable=True,
    )  # FK (Nullable)
    date = Column(DateTime, nullable=False)                                   # 점검 일시
    status = Column(String(50), nullable=False)                               # 조치 상태
    uid = Column(
        BigInteger,
        ForeignKey("user.uid", ondelete="SET NULL"),
        nullable=True,
    )  # FK (점검자)
    camera_id = Column(
        BigInteger,
        ForeignKey("cctv.cctv_id", ondelete="SET NULL"),
        nullable=True,
    )  # FK (점검 대상 CCTV)
    content = Column(String(255), nullable=False)                             # 내용
    image_url = Column(String(255), nullable=True)                            # 현장 이미지 URL
    type = Column(String(50), nullable=False, default="점검")              # 조치 or 점검
    company_id = Column(
        BigInteger,
        ForeignKey("company.company_id", ondelete="CASCADE"),
        nullable=False,
    )  # 회사 아이디

    event = relationship("Event", back_populates="checklists")
    user = relationship("User", back_populates="checklists")
    cctv = relationship("CCTV", back_populates="checklists")
    report_maps = relationship("ReportChecklistMap", back_populates="checklist")
    company = relationship("Company")

    @property
    def assignee_name(self):
        """담당자 배정 화면용 실제 사용자 이름."""
        return self.user.name if self.user else None

    @property
    def event_category_name(self):
        """이벤트 원본 카테고리(예: 소방안전)를 우선한다."""
        if not self.event or not self.event.category:
            return None
        return self.event.category.category or self.event.category.category_name

    @property
    def event_location(self):
        """체크리스트의 임시 camera_id가 아니라 원본 이벤트 CCTV 위치를 사용한다."""
        if not self.event or not self.event.cctv:
            return None
        return self.event.cctv.location
