from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional
from app.models import User, SignupCode
from app.schemas.user import UserCreate
from app.core.crypt import hash_password, verify_password


def get_users(db: Session, company_id: int):
    return (
        db.query(User)
        .filter(User.company_id == company_id)
        .all()
    )


def get_user_by_uid(db: Session, uid: int, company_id: Optional[int] = None) -> Optional[User]:
    query = db.query(User).filter(User.uid == uid)
    
    if company_id is not None:
        query = query.filter(User.company_id == company_id)
        
    return query.first()


def create_users(db: Session, user_create: UserCreate):
    hashed_pw = hash_password(user_create.password)

    user_role = user_create.role or "일반유저"
    user_category = user_create.category
    user_company_id = user_create.company_id

    # 회원가입 코드가 입력된 경우 자동 역할/카테고리 바인딩
    code_obj = None
    if user_create.code:
        code_obj = db.query(SignupCode).filter(SignupCode.code == user_create.code).first()
        if not code_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 회원가입 코드입니다."
            )
        if code_obj.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용된 회원가입 코드입니다."
            )
        user_role = code_obj.role
        user_category = code_obj.category

    db_user = User(
        user_id=user_create.user_id,
        company_id=user_company_id,
        name=user_create.name,
        password=hashed_pw,
        role=user_role,
        category=user_category,
        company_code=user_create.company_code
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # 코드 사용 완료 처리
    if code_obj:
        code_obj.is_used = True
        code_obj.used_by_uid = db_user.uid
        db.commit()

    return db_user


def checkid(db: Session, user_id: str):
    user = db.query(User).filter(User.user_id == user_id).first()
    return user is not None


def change_user_password(db: Session, user: User, old_password: str, new_password: str) -> bool:
    if not verify_password(old_password, user.password):
        return False
    user.password = hash_password(new_password)
    db.commit()
    return True


def find_user_password(db: Session, user_id: str, name: str) -> Optional[User]:
    return db.query(User).filter(User.user_id == user_id, User.name == name).first()


def update_user_role(db: Session, uid: int, role: str, company_id: int,) -> Optional[User]:
    user = get_user_by_uid(db, uid, company_id)
    if not user:
        return None
    user.role = role
    db.commit()
    db.refresh(user)
    return user


def update_user_category_and_role(
    db: Session,
    company_id: int,
    uid: int,
    category: Optional[str] = None,
    role: Optional[str] = None,
) -> Optional[User]:
    """안전관리자(총책임자) 전용: 유저 역할 및 일반유저 카테고리 변경"""
    user = get_user_by_uid(db, uid, company_id)
    if not user:
        return None
    if role is not None:
        user.role = role
    if category is not None:
        user.category = category
    db.commit()
    db.refresh(user)
    return user

def withdraw_user(db: Session, user: User, password: str) -> bool:
    """
    유저 본인 회원탈퇴 처리
    - 입력받은 비밀번호 검증 후 삭제
    """
    if not verify_password(password, user.password):
        return False
    
    db.delete(user)
    db.commit()
    return True
