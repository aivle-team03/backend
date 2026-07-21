from sqlalchemy.orm import Session
from app.models.cctv import CCTV

def get_cctv(db: Session, camera_id: int):
    return db.query(CCTV).filter(CCTV.camera_id == camera_id).first()

def get_cctvs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(CCTV).offset(skip).limit(limit).all()
