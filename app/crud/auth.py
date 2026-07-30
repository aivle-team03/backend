from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

from app.db.db import get_db
from app.models import User
from app.core.crypt import verify_password

load_dotenv()

import hashlib

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("ENV") == "production":
        raise ValueError("CRITICAL: Production environment requires SECRET_KEY to be explicitly defined in .env!")
    else:
        SECRET_KEY = "super-secret-key-12345"

ALGORITHM = os.getenv("ALGORITHM") or "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def hash_token(token: str) -> str:
    """DB 유출 시 원본 리프레시 토큰 탈취를 방지하기 위한 SHA-256 해시 함수"""
    if not token:
        return ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(data: dict) -> str:
    """JWT Access Token 생성 (기본 30분 유효)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """JWT Refresh Token 생성 (기본 7일 유효)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_refresh_token(db: Session, refresh_token: str) -> User:
    """Refresh Token 검증 및 DB 해시 토큰과의 일치 여부 확인"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="리프레시 토큰이 유효하지 않거나 만료되었습니다. 다시 로그인해주세요.",
    )
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise credentials_exception
        uid_int = int(user_id)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    hashed_token = hash_token(refresh_token)
    user = db.query(User).filter(User.uid == uid_int).first()
    if user is None or user.refresh_token != hashed_token:
        raise credentials_exception

    return user


# 토큰 추출 도구 (요청 헤더에서 토큰 꺼냄)
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않거나 이미 로그아웃된 세션입니다.",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        company_id: int = payload.get("company_id")
        token_type: str = payload.get("type")

        print(f"👉 [DEBUG Token Payload] user_id: {user_id} ({type(user_id)}), company_id: {company_id}, token_type: {token_type}")

        # [보안 검증 1] refresh 토큰을 Authorization 헤더에 보내 access 토큰처럼 사용하는 공격 차단
        if token_type != "access" or user_id is None or company_id is None:
            print("❌ [DEBUG Error] 토큰 타입 불일치 또는 필수값 누락")
            raise credentials_exception
        uid_int = int(user_id)
    except (JWTError, ValueError, TypeError) as e:
        print(f"❌ [DEBUG Token Decode Exception]: {e}")
        raise credentials_exception

    user = db.query(User).filter(User.uid == uid_int).first()
    if user is None:
        print(f"❌ [DEBUG Error] DB에 UID={uid_int}인 유저가 없습니다.")
    else:
        print(f"👉 [DEBUG DB User] uid: {user.uid}, company_id: {user.company_id}, has_refresh_token: {bool(user.refresh_token)}")

    # [보안 검증 2] 로그아웃하여 user.refresh_token이 None인 경우, 남은 Access Token 요청도 즉시 차단
    if user is None or user.company_id != company_id or user.refresh_token is None:
        print("❌ [DEBUG Error] 유저 검증(company_id 불일치 또는 refresh_token이 None) 실패!")
        raise credentials_exception

    return user


def get_current_admin(current_user: User = Depends(get_current_user)):
    """안전관리자(총책임자) 권한 확인 - role이 '안전관리자'인 경우에만 접근 허용"""
    if current_user.role != "안전관리자":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="안전관리자(총책임자) 권한이 필요합니다",
        )
    return current_user


