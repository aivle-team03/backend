from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, func
from app.db.db import Base


class SignupCode(Base):
    __tablename__ = "signup_code"

    id = Column(BigInteger, primary_key=True, autoincrement=True)                   # PK

    code = Column(String(50), unique=True, nullable=False)                      # 고유 회원가입 코드 (예: INV-8X9A2K4M)
    role = Column(String(50), nullable=False)                                   # 부여될 역할 (안전관리사, 관제사, 현장관리자, 일반유저)
    category = Column(String(100), nullable=True)                               # 카테고리 (일반유저 선택 시: 지게차, 화물트럭 등)
    is_used = Column(Boolean, nullable=False, default=False)                    # 코드 사용 여부
    used_by_uid = Column(BigInteger, nullable=True)                             # 코드를 사용한 유저 UID
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())  # 생성일시
