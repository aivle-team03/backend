import os
import shutil
import time
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.db import get_db
from app.crud.auth import get_current_user
from app.models import User
from app.schemas.checklist import (
    ChecklistResponse,
    ManagerSearchResponse,
    AssignManagerRequest,
    StatusUpdateRequest
)
from app.crud.checklist import (
    get_checklists,
    search_managers,
    assign_manager,
    complete_checklist,
    update_checklist_status,
    get_my_checklists
)

router = APIRouter()

UPLOAD_DIR = "static/uploads"

@router.get("", response_model=List[ChecklistResponse])
def read_checklists(type: Optional[str] = None, db: Session = Depends(get_db)):
    """체크리스트 조회 API - 명세서 URL /api/checklists (요구사항 ADM-23-57-25)"""
    return get_checklists(db, checklist_type=type)

@router.get("/managers", response_model=List[ManagerSearchResponse])
def read_managers(keyword: str, db: Session = Depends(get_db)):
    """조치 담당자 검색 API - 명세서 URL /api/checklists/managers (요구사항 ADM-23-66-27)"""
    return search_managers(db, keyword=keyword)

@router.patch("/{checklist_id}/assign", response_model=ChecklistResponse)
def patch_assign_manager(
    checklist_id: int,
    assign_req: AssignManagerRequest,
    db: Session = Depends(get_db)
):
    """담당자 배정 API - 명세서 URL /api/checklists/{checklist_id}/assign (요구사항 ADM-23-42-26)"""
    db_checklist = assign_manager(db, checklist_id=checklist_id, user_id=assign_req.user_id)
    if db_checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="체크리스트 또는 담당자(User)를 찾을 수 없습니다."
        )
    return db_checklist

@router.patch("/{checklist_id}/complete", response_model=ChecklistResponse)
def patch_complete_checklist(
    checklist_id: int,
    content: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """조치 완료 등록 API - 명세서 URL /api/checklists/{checklist_id}/complete (요구사항 ADM-23-56-28)"""
    # 1. uploads 폴더 생성 확인
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # 2. 고유 파일명 생성 및 저장
    ext = os.path.splitext(image.filename)[1]
    filename = f"checklist_{checklist_id}_{int(time.time())}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    image_url = f"/static/uploads/{filename}"
    
    # 3. 비즈니스 업데이트 처리
    db_checklist = complete_checklist(db, checklist_id=checklist_id, image_url=image_url, content=content)
    if db_checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="체크리스트를 찾을 수 없습니다."
        )
    return db_checklist

@router.patch("/{checklist_id}/status", response_model=ChecklistResponse)
def patch_checklist_status(
    checklist_id: int,
    status_req: StatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """조치 승인/반려 API - 명세서 URL /api/checklists/{checklist_id}/status (요구사항 ADM-23-81-29)"""
    db_checklist = update_checklist_status(
        db,
        checklist_id=checklist_id,
        status=status_req.status,
        reason=status_req.reason
    )
    if db_checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="체크리스트를 찾을 수 없습니다."
        )
    return db_checklist

@router.get("/me", response_model=List[ChecklistResponse])
def read_my_checklists(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 조치 기록 조회 API - 명세서 URL /api/checklists/me (요구사항 ADM-15-54-6)"""
    return get_my_checklists(db, uid=current_user.uid, skip=skip, limit=limit)
