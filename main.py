import models
import asyncio
from database import engine, get_db
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from auth_utils import hash_password, verify_password
from pydantic import BaseModel
from sqlalchemy.orm import Session

app = FastAPI(
    title="FastAPI Backend",
    description="시설 안전관리 AI 자동화 시스템",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 실제 배포 시에는 ["http://localhost:3000"] 처럼 프론트 주소만 적는 게 안전합니다.
    allow_credentials=True,
    allow_methods=["*"], # GET, POST, PUT, DELETE 모두 허용
    allow_headers=["*"], # 모든 헤더 허용
)

models.Base.metadata.create_all(bind=engine)

class UserSignup(BaseModel):
    user_id: str
    password: str
    name: str
    role: str = "field_worker"

class UserLogin(BaseModel):
    user_id: str
    password: str


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/api/auth/signup")
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    # 1. 이미 존재하는 아이디인지 확인
    existing_user = db.query(models.User).filter(models.User.user_id == user_data.user_id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")

    # 2. 비밀번호 암호화 후 저장
    new_user = models.User(
        user_id=user_data.user_id,
        password=hash_password(user_data.password), # 암호화 적용!
        name=user_data.name,
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    return {"message": f"{new_user.name}님, 회원가입이 완료되었습니다."}

@app.post("/api/auth/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    # 1. 아이디로 사용자 찾기
    user = db.query(models.User).filter(models.User.user_id == user_data.user_id).first()
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
            "uid": user.uid
        }
    }

@app.post("/api/auth/logout")
def logout():
    return {"message": "로그아웃 성공!"}