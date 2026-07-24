import os
import shutil
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.crud.auth import get_current_user
from app.models import User
from app.schemas.checklist import (
    ChecklistCreate,
    ChecklistResponse,
    ManagerSearchResponse,
    AssignManagerRequest,
    StatusUpdateRequest
)
from app.crud.checklist import (
    create_checklist,
    get_checklists_by_role,
    get_action_history_by_role,
    search_managers,
    assign_manager,
    complete_checklist,
    update_checklist_status,
    delete_checklist
)

router = APIRouter()
UPLOAD_DIR = "static/uploads"

@router.get("", response_model=List[ChecklistResponse])
def read_checklists(
    type: Optional[str] = None, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_checklists_by_role(db, user=current_user, checklist_type=type)

@router.get("/history", response_model=List[ChecklistResponse])
def read_action_history(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    조치 이력 조회 API
    - 조치가 진행/완료/승인된 항목만 조회
    """
    return get_action_history_by_role(db, user=current_user, skip=skip, limit=limit)

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
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    ext = os.path.splitext(image.filename)[1]
    filename = f"checklist_{checklist_id}_{int(time.time())}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    image_url = f"/static/uploads/{filename}"
    
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
    """
    관리자 승인/반려
    - 승인 시: status = "승인 완료"
    - 반려 시: status = "조치 필요" (작업자 체크리스트로 되돌아감)
    """
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

@router.post("", response_model=ChecklistResponse, status_code=status.HTTP_201_CREATED)
def post_checklist(
    checklist_req: ChecklistCreate,
    db: Session = Depends(get_db)
):
    """
    조치(체크리스트) 등록 API - (AI 서버 또는 수동 등록용)
    """
    db_checklist = create_checklist(db, checklist_req)
    return db_checklist

@router.delete("/{checklist_id}", status_code=status.HTTP_200_OK)
def remove_checklist(checklist_id: int, db: Session = Depends(get_db)):
    success = delete_checklist(db, checklist_id=checklist_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="삭제할 체크리스트 항목을 찾을 수 없습니다."
        )
    return {"message": f"체크리스트 #{checklist_id} 항목이 성공적으로 삭제되었습니다."}
