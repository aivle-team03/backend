from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.db import get_db
from app.schemas.cctv import CCTVResponse, CCTVCreate
from app.crud.cctv import get_cctv, get_cctvs, create_cctv, delete_cctv, get_cctv_by_name

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


@router.get("/{cctv_id}", response_model=CCTVResponse)
def read_cctv_detail(cctv_id: int, db: Session = Depends(get_db)):
    """CCTV 상세 및 스트리밍 정보 통합 조회 API - 명세서 URL /api/cctvs/{cctv_id}"""
    db_cctv = get_cctv(db, cctv_id=cctv_id)
    if db_cctv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CCTV를 찾을 수 없습니다."
        )
    return db_cctv

@router.delete("/{cctv_id}", status_code=status.HTTP_200_OK)
def remove_cctv(cctv_id: int, db: Session = Depends(get_db)):
    success = delete_cctv(db, cctv_id=cctv_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="삭제할 CCTV를 찾을 수 없습니다."
        )
    return {"message": f"CCTV #{cctv_id}가 성공적으로 삭제되었습니다."}
@router.post("", response_model=CCTVResponse, status_code=status.HTTP_201_CREATED)
def register_cctv(
    cctv_in: CCTVCreate,
    db: Session = Depends(get_db)
):
    """
    CCTV 카메라 신규 등록
    """
    # 1. 중복된 이름 검사
    if get_cctv_by_name(db, cctv_in.camera_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 CCTV 이름입니다.",
        )

    # 2. CRUD 함수 호출하여 DB 생성
    db_cctv = create_cctv(db, cctv_in)
    return db_cctv
