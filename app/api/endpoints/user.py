from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.db import get_db
from app.models.models import User
from app.crud.user import get_users

router = APIRouter()

@router.get("/users")
def read_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@router.post("/users")
def create_user(name:str):
    return {"message": name}