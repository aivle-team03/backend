# app/api/endpoints/board.py
import os
import shutil
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.crud.auth import get_current_user
from app.models import User
from app.schemas.board import BoardResponse, BoardListResponse, BoardStatusUpdateRequest
from app.crud.board import (
    create_board,
    get_boards,
    get_board_by_id,
    update_board,
    update_board_status,
    delete_board
)

router = APIRouter()
UPLOAD_DIR = "static/uploads"

# 1. 게시글 등록 (POST /api/boards)
@router.post("", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
def post_board(
    title: str = Form(...),
    board_contents: str = Form(...),
    event_category_id: Optional[int] = Form(None),
    status_val: str = Form("접수", alias="status"),
    location: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    image_url = None
    if image and image.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(image.filename)[1]
        filename = f"board_{int(time.time())}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
            
        image_url = f"/static/uploads/{filename}"

    return create_board(
        db=db,
        uid=current_user.uid,
        title=title,
        board_contents=board_contents,
        event_category_id=event_category_id,
        status=status_val,
        location=location,
        image_url=image_url
    )

# 2. 게시글 목록 조회 (GET /api/boards)
@router.get("", response_model=BoardListResponse)
def read_boards(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    category: Optional[int] = Query(None),
    status_val: Optional[str] = Query(None, alias="status"),
    location: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    total, items = get_boards(
        db, page=page, size=size, category=category,
        status=status_val, location=location, keyword=keyword
    )
    return {"total": total, "page": page, "size": size, "items": items}

# 3. 게시글 상세 조회 (GET /api/boards/{board_id})
@router.get("/{board_id}", response_model=BoardResponse)
def read_board_detail(board_id: int, db: Session = Depends(get_db)):
    board = get_board_by_id(db, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    return board

# 4. 게시글 수정 (PATCH /api/boards/{board_id})
@router.patch("/{board_id}", response_model=BoardResponse)
def patch_board(
    board_id: int,
    title: Optional[str] = Form(None),
    board_contents: Optional[str] = Form(None),
    event_category_id: Optional[int] = Form(None),
    status_val: Optional[str] = Form(None, alias="status"),
    location: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    board = get_board_by_id(db, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    image_url = None
    if image:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(image.filename)[1]
        filename = f"board_{board_id}_{int(time.time())}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/{filename}"

    return update_board(
        db=db, board=board, title=title, board_contents=board_contents,
        event_category_id=event_category_id, status=status_val,
        location=location, image_url=image_url
    )

# 5. 게시글 삭제 (DELETE /api/boards/{board_id})
@router.delete("/{board_id}")
def remove_board(
    board_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    board = get_board_by_id(db, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    
    delete_board(db, board)
    return {"message": "success"}

# 6. 게시글 상태 변경 (PATCH /api/boards/{board_id}/status)
@router.patch("/{board_id}/status", response_model=BoardResponse)
def patch_board_status(
    board_id: int,
    status_req: BoardStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 관리자 전용 권한 확인 조건 추가 필요 시 사용
    # if current_user.role != "ADMIN":
    #     raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
        
    board = get_board_by_id(db, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    return update_board_status(db, board, status=status_req.status)
