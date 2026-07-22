from sqlalchemy.orm import Session
from app.models.cctv import CCTV
from app.schemas.cctv import CCTVCreate


def get_cctv(db: Session, cctv_id: int):
    return db.query(CCTV).filter(CCTV.cctv_id == cctv_id).first()


def get_cctvs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(CCTV).offset(skip).limit(limit).all()


def create_cctv(db: Session, cctv_create: CCTVCreate) -> CCTV:
    db_cctv = CCTV(
        cctv_name=cctv_create.cctv_name,
        location=cctv_create.location,
        stream_url=cctv_create.stream_url,
        status=cctv_create.status or "정상"
    )
    db.add(db_cctv)
    db.commit()
    db.refresh(db_cctv)
    return db_cctv
