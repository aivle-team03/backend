from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.db import Base


class EventCategory(Base):
    __tablename__ = "event_category"

    category_id = Column(BigInteger, primary_key=True)            # PK
    company_id = Column(
        BigInteger,
        ForeignKey("company.company_id", ondelete="CASCADE"),
        nullable=False,
    )  # 회사 아이디
    category = Column(String(50), nullable=False)                             # 분류 (회재/위험/이상 등)
    category_name = Column(String(100), nullable=False)                        # 상세 이벤트명
    level = Column(Integer, nullable=False, default=1)
    is_deleted = Column(Boolean, nullable=False, default=False)

    events = relationship("Event", back_populates="category")
    company = relationship("Company")
