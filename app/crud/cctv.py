from sqlalchemy.orm import Session
from app.models.cctv import CCTV
from app.schemas.cctv import CCTVCreate


def get_cctv(db: Session, cctv_id: int, company_id: int):
    return (
        db.query(CCTV)
        .filter(
            CCTV.cctv_id == cctv_id,
            CCTV.company_id == company_id,
            CCTV.is_deleted == False,
        )
        .first()
    )


def get_cctvs(db: Session, company_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(CCTV)
        .filter(CCTV.company_id == company_id, CCTV.is_deleted == False,)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_cctv_by_name(db: Session, camera_name: str, company_id: int) -> CCTV | None:
    """카메라 이름 중복 검사용 조회"""
    return (
        db.query(CCTV)
        .filter(
            CCTV.camera_name == camera_name,
            CCTV.company_id == company_id,
            CCTV.is_deleted == False,
        )
        .first()
    )

def create_cctv(db: Session, cctv_in: CCTVCreate, company_id: int) -> CCTV:
    """CCTV 신규 등록"""
    db_cctv = CCTV(
        company_id=company_id,
        camera_name=cctv_in.camera_name,
        location=cctv_in.location,
        stream_url=cctv_in.stream_url,
        status=cctv_in.status or "running",
        is_deleted=False,
    )
    db.add(db_cctv)
    db.commit()
    db.refresh(db_cctv)
    return db_cctv

def delete_cctv(db: Session, cctv_id: int, company_id: int) -> bool:
    db_cctv = (
        db.query(CCTV)
        .filter(
            CCTV.cctv_id == cctv_id,
            CCTV.company_id == company_id,
            CCTV.is_deleted == False,
        )
        .first()
    )    
    if not db_cctv:
        return False
    
    db_cctv.is_deleted = True
    db.commit()
    return True
