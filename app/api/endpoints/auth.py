from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.db import get_db
from app.models import User
from app.crud.user import create_users as crud_create_user, checkid as crud_check_id
from app.crud.auth import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    hash_token,
    get_current_user
)
from app.core.crypt import verify_password, hash_password
from app.schemas.user import PasswordReset, UserCreate, UserLogin
from app.schemas.token import Token, RefreshTokenRequest

router = APIRouter()

@router.post("/signup")
def signup(user_create: UserCreate, db: Session = Depends(get_db)):
    # 이미 존재하는 아이디인지 중복 검사
    if crud_check_id(db, user_create.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 아이디입니다."
        )
    db_user = crud_create_user(db, user_create)
    return {
        "message": "success",
        "user_id": db_user.user_id,
        "company_id": db_user.company_id,
        "role": db_user.role,
        "category": db_user.category
    }

@router.get("/checkid")
def checkid(user_id: str, db: Session = Depends(get_db)):
    exists = crud_check_id(db, user_id)
    if exists:
        return {"message": "duplicated"}  # 아이디가 이미 존재하는 경우
    else:
        return {"message": "available"}     # 아이디 사용 가능한 경우

@router.get("/verify-code")
def verify_code(code: str, db: Session = Depends(get_db)):
    """회원가입 입력 코드 유효성 검증 및 역할/카테고리 사전 확인 API"""
    from app.crud.signup_code import get_signup_code_by_code
    code_obj = get_signup_code_by_code(db, code)
    if not code_obj:
        raise HTTPException(status_code=400, detail="유효하지 않은 회원가입 코드입니다.")
    if code_obj.is_used:
        raise HTTPException(status_code=400, detail="이미 사용된 회원가입 코드입니다.")
    return {
        "message": "valid",
        "code": code_obj.code,
        "company_id": code_obj.company_id,
        "role": code_obj.role,
        "category": code_obj.category
    }


@router.post("/login", response_model=Token)
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    # 유저 조회
    user = db.query(User).filter(User.user_id == user_login.user_id).first()
    if not user or not verify_password(user_login.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 잘못되었습니다."
        )
    
    # JWT Access Token & Refresh Token 생성
    token_data = {"sub": str(user.uid), "company_id": user.company_id}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    # DB에 SHA-256 해시화된 Refresh Token 저장 (보안 강화)
    user.refresh_token = hash_token(refresh_token)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    refresh_req: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Access Token 만료 시 최초 로그인 후 7일 이내에만 새 Access Token 발급 (Refresh Token 만료 연장 없음)"""
    user = verify_refresh_token(db, refresh_req.refresh_token)

    # 새 Access Token만 발급 (기존 Refresh Token의 최초 7일 유효기간 유지하여 무제한 연장 방지)
    token_data = {"sub": str(user.uid), "company_id": user.company_id}
    new_access_token = create_access_token(data=token_data)

    return {
        "access_token": new_access_token,
        "refresh_token": refresh_req.refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """로그아웃 API - DB에 저장된 Refresh Token 무효화(요구사항 USR-02-02-3)"""
    current_user.refresh_token = None
    db.commit()
    return {"message": "success"}

@router.post("/find/password")
def reset_password(reset_data: PasswordReset, db: Session = Depends(get_db)):
    """비밀번호 찾기/재설정 API (로그인 없이 접근 가능)"""
    
    # 1. 아이디와 이름이 일치하는 유저 찾기
    user = db.query(User).filter(
        User.user_id == reset_data.user_id,
        User.name == reset_data.name
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="일치하는 사용자 정보를 찾을 수 없습니다."
        )

    # 2. 새 비밀번호 해싱 후 DB 업데이트
    user.password = hash_password(reset_data.new_password)
    db.commit()

    return {"message": "success"}