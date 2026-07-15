from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.db import get_db
from app.models.models import User
from app.crud.user import get_users
from pydantic import BaseModel
from app.utils.auth_utils import hash_password, verify_password

router = APIRouter()

class UserSignup(BaseModel):
    user_id: str
    password: str
    name: str
    role: str = "field_worker"
    company_code: str

class UserLogin(BaseModel):
    user_id: str
    password: str

    
@router.post("/signup")
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    # 1. 이미 존재하는 아이디인지 확인
    existing_user = db.query(User).filter(User.user_id == user_data.user_id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")

    # 2. 비밀번호 암호화 후 저장
    new_user = User(
        user_id=user_data.user_id,
        password=hash_password(user_data.password), # 암호화 적용!
        name=user_data.name,
        role=user_data.role,
        company_code=user_data.company_code
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"{new_user.name}님, 회원가입이 완료되었습니다."}

@router.post("/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    # 1. 아이디로 사용자 찾기
    user = db.query(User).filter(User.user_id == user_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # 2. 비밀번호 일치 확인
    if not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=400, detail="비밀번호가 틀렸습니다.")

    # 3. 로그인 성공 (원래는 여기서 토큰을 주지만, 일단 성공 메시지만 리턴)
    return {
        "message": "로그인 성공!",
        "user_info": {
            "name": user.name,
            "role": user.role,
            "uid": user.uid,
            "company_code": user.company_code
        }
    }

@router.post("/logout")
def logout():
    return {"message": "로그아웃 성공!"}