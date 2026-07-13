from sqlalchemy import Column, BigInteger, String, DateTime
from db import Base

class User(Base):
    __tablename__ = "user"

    uid = Column(BigInteger, primary_key=True, index=True)   # PK
    user_id = Column(String(50), unique=True, nullable=False)  # 로그인 아이디
    name = Column(String(100), nullable=False)                # 이름
    password = Column(String(255), nullable=False)            # 비밀번호
    refresh_token = Column(String(255), nullable=True)        # 리프레시 토큰
    role = Column(String(50), nullable=False)                 # 권한
    company_code = Column(String(50), nullable=True)          # 회사 코드
    created_at = Column(DateTime, nullable=False)             # 생성일
