<<<<<<< HEAD
from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey
=======
from sqlalchemy import Column, BigInteger, String, Integer
>>>>>>> 7ed113320afa3b57587df0d79e1737a2c6d68b8d
from sqlalchemy.orm import relationship
from app.db.db import Base


class EventCategory(Base):
    __tablename__ = "event_category"

<<<<<<< HEAD
    category_id = Column(BigInteger, primary_key=True)            # PK
    company_id = Column(BigInteger, ForeignKey("company.company_id"), nullable=False)  #회사 아이디
=======
    category_id = Column(BigInteger, primary_key=True, autoincrement=True)          # PK

>>>>>>> 7ed113320afa3b57587df0d79e1737a2c6d68b8d
    category = Column(String(50), nullable=False)                             # 분류 (회재/위험/이상 등)
    category_name = Column(String(100), nullable=False)                        # 상세 이벤트명
    level = Column(Integer, nullable=False, default=1)

    events = relationship("Event", back_populates="category")
    company = relationship("Company")
