from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.db import get_db
from app.schemas.cctv import CCTVResponse, CCTVStreamResponse
from app.crud.cctv import get_cctv, get_cctvs

router = APIRouter()

@router.get("", response_model=List[CCTVResponse])
def read_cctvs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """CCTV 목록 조회 API - 명세서 URL /api/cctvs (슬래시 생략 반영)"""
    cctvs = get_cctvs(db, skip=skip, limit=limit)
    return cctvs

@router.get("/{cctv_id}/stream", response_model=CCTVStreamResponse)
def read_cctv_stream(cctv_id: int, db: Session = Depends(get_db)):
    """CCTV 실시간 스트리밍 송출 API - 명세서 URL /api/cctvs/{cctv_id}/stream"""
    db_cctv = get_cctv(db, camera_id=cctv_id)
    if db_cctv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CCTV를 찾을 수 없습니다."
        )
    return db_cctv
