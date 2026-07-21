from sqlalchemy.orm import Session
from app.models import User
from datetime import datetime
from app.schemas.user import UserCreate
from app.core.crypt import hash_password

def get_users(db: Session):
    return db.query(User).all()

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
    if user:
        return True
    else:
        return False