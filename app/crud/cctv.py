from sqlalchemy.orm import Session
from app.models.cctv import CCTV
from app.schemas.cctv import CCTVCreate

def get_cctv(db: Session, camera_id: int):
    return db.query(CCTV).filter(CCTV.camera_id == camera_id).first()

def get_cctvs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(CCTV).offset(skip).limit(limit).all()

def get_cctv_by_name(db: Session, camera_name: str) -> CCTV | None:
    """카메라 이름 중복 검사용 조회"""
    return db.query(CCTV).filter(CCTV.camera_name == camera_name).first()

def create_cctv(db: Session, cctv_in: CCTVCreate) -> CCTV:
    """CCTV 신규 등록"""
    db_cctv = CCTV(
        camera_name=cctv_in.camera_name,
        location=cctv_in.location,
        stream_url=cctv_in.stream_url,
        status=cctv_in.status or "running",
    )
    db.add(db_cctv)
    db.commit()
    db.refresh(db_cctv)
    return db_cctv
