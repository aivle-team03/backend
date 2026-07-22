from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.db import get_db
from app.schemas.cctv import CCTVResponse, CCTVStreamResponse, CCTVCreate
from app.crud.cctv import get_cctv, get_cctvs, create_cctv

router = APIRouter()


@router.get("", response_model=List[CCTVResponse])
def read_cctvs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """CCTV 목록 조회 API - 명세서 URL /api/cctvs"""
    cctvs = get_cctvs(db, skip=skip, limit=limit)
    return cctvs


@router.post("", response_model=CCTVResponse, status_code=status.HTTP_201_CREATED)
def post_create_cctv(cctv_create: CCTVCreate, db: Session = Depends(get_db)):
    """CCTV 연결 및 추가 API - 명세서 URL /api/cctvs"""
    return create_cctv(db, cctv_create)


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


@router.get("/{camera_id}", response_model=CCTVResponse)
def read_cctv_detail(camera_id: int, db: Session = Depends(get_db)):
    """CCTV 상세 조회 API - 명세서 URL /api/cctvs/{camera_id}"""
    db_cctv = get_cctv(db, camera_id=camera_id)
    if db_cctv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CCTV를 찾을 수 없습니다."
        )
    return db_cctv
