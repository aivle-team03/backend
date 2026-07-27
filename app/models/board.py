from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.db import Base

class Board(Base):
    __tablename__ = "board"

# ERD기반으로 추가하였습니다. 추후 수정 가능 
<<<<<<< HEAD
    board_id = Column(BigInteger, primary_key=True, autoincrement=True)  # PK
    company_id = Column(BigInteger, ForeignKey("company.company_id"), nullable=False)       # 회사 아이디
=======
    board_id = Column(BigInteger, primary_key=True, autoincrement=True)              # PK

>>>>>>> 7ed113320afa3b57587df0d79e1737a2c6d68b8d
    uid = Column(BigInteger, ForeignKey("user.uid"), nullable=False)     # 작성자 FK
    event_category_id = Column(BigInteger, ForeignKey("event_category.category_id"), nullable=True) # 카테고리 FK
    title = Column(String(200), nullable=False)                          # 제목
    board_contents = Column(Text, nullable=False)                        # 내용
    status = Column(String(50), nullable=False, default="접수")           # 조치 상태 (예: 접수, 조치중, 완료)
    location = Column(String(100), nullable=True)                        # 위치 정보
    image_url = Column(String(255), nullable=True)                       # 첨부 이미지 URL
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    user = relationship("User", backref="boards")
    event_category = relationship("EventCategory", backref="boards")
    company = relationship("Company")
