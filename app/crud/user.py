from sqlalchemy.orm import Session
from app.models.models import User
from datetime import datetime

def get_users(db: Session):
    return db.query(User).all()
