from sqlalchemy.orm import Session
from app.models import User
from datetime import datetime
from typing import Optional
from app.schemas.user import UserCreate
from app.core.crypt import hash_password, verify_password


def get_users(db: Session):
    return db.query(User).all()


def get_user_by_uid(db: Session, uid: int) -> Optional[User]:
    return db.query(User).filter(User.uid == uid).first()


def create_users(db: Session, user_create: UserCreate):
    hashed_pw = hash_password(user_create.password)

    db_user = User(
        user_id=user_create.user_id,
        name=user_create.name,
        password=hashed_pw,
        role=user_create.role,
        company_code=user_create.company_code
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
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


def update_user_role(db: Session, uid: int, role: str) -> Optional[User]:
    user = get_user_by_uid(db, uid)
    if not user:
        return None
    user.role = role
    db.commit()
    db.refresh(user)
    return user