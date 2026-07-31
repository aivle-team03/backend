import shutil
from datetime import date, datetime, time
from pathlib import Path
from typing import List, Literal, Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.crud import action_history as action_history_crud
from app.crud.auth import get_current_admin, get_current_user
from app.db.db import get_db
from app.models import User
from app.schemas.action_history import (
    ActionHistoryAssignRequest,
    ActionHistoryCreateRequest,
    ActionHistoryDetailResponse,
    ActionHistoryListItem,
    ActionHistoryListResponse,
    ActionHistoryRejectRequest,
    ActionStatus,
    ApprovalStatus,
    HandlerListResponse,
    SourceType,
)


router = APIRouter()
UPLOAD_DIR = Path("static/uploads")
IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _raise_http_error(error: Exception):
    if isinstance(error, action_history_crud.ActionHistoryNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    if isinstance(error, action_history_crud.ActionHistoryForbiddenError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    if isinstance(error, action_history_crud.ActionHistoryStateError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    if isinstance(error, action_history_crud.ActionHistoryValidationError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    raise error


def _save_image(action_history_id: int, image: UploadFile):
    extension = IMAGE_EXTENSIONS.get(image.content_type or "")
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="jpg, png, webp, gif 형식의 이미지만 업로드할 수 있습니다.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    filename = (
        f"action_history_{action_history_id}_{timestamp}_{uuid4().hex[:8]}"
        f"{extension}"
    )
    file_path = UPLOAD_DIR / filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    if file_path.stat().st_size == 0:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="빈 이미지 파일은 업로드할 수 없습니다.",
        )

    return f"/static/uploads/{filename}", file_path


def _delete_local_image(image_url: Optional[str]):
    if not image_url or not image_url.startswith("/static/uploads/"):
        return

    upload_root = UPLOAD_DIR.resolve()
    file_path = Path(image_url.lstrip("/")).resolve()
    try:
        file_path.relative_to(upload_root)
    except ValueError:
        return
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        pass


@router.get("", response_model=ActionHistoryListResponse)
def read_action_histories(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    source_type: Optional[SourceType] = Query(None),
    category_id: Optional[int] = Query(None, gt=0),
    action_status: Optional[ActionStatus] = Query(None),
    approval_status: Optional[ApprovalStatus] = Query(None),
    handler_uid: Optional[int] = Query(None, gt=0),
    unassigned: Optional[bool] = Query(None),
    created_from: Optional[date] = Query(None),
    created_to: Optional[date] = Query(None),
    completed_from: Optional[date] = Query(None),
    completed_to: Optional[date] = Query(None),
    sort_by: Literal[
        "created_at", "completed_at", "approval_date"
    ] = Query("created_at"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="created_from은 created_to보다 늦을 수 없습니다.",
        )
    if completed_from and completed_to and completed_from > completed_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="completed_from은 completed_to보다 늦을 수 없습니다.",
        )

    return action_history_crud.get_action_histories(
        db,
        company_id=current_admin.company_id,
        page=page,
        size=size,
        keyword=keyword,
        source_type=source_type.value if source_type else None,
        category_id=category_id,
        action_status=action_status.value if action_status else None,
        approval_status=approval_status.value if approval_status else None,
        handler_uid=handler_uid,
        unassigned=unassigned,
        created_from=(
            datetime.combine(created_from, time.min) if created_from else None
        ),
        created_to=(
            datetime.combine(created_to, time.max) if created_to else None
        ),
        completed_from=(
            datetime.combine(completed_from, time.min)
            if completed_from
            else None
        ),
        completed_to=(
            datetime.combine(completed_to, time.max) if completed_to else None
        ),
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "",
    response_model=ActionHistoryDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_action_history(
    request: ActionHistoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return action_history_crud.create_action_history(
            db,
            request=request,
            company_id=current_user.company_id,
            creator=current_user,
        )
    except Exception as error:
        _raise_http_error(error)


@router.get("/handlers", response_model=HandlerListResponse)
def read_action_handlers(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return action_history_crud.search_action_handlers(
        db,
        company_id=current_admin.company_id,
        keyword=keyword,
        page=page,
        size=size,
    )


@router.patch(
    "/assignments",
    response_model=List[ActionHistoryListItem],
)
def assign_action_handlers(
    request: ActionHistoryAssignRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        return action_history_crud.assign_action_handlers(
            db,
            action_history_ids=request.action_history_ids,
            handler_uid=request.handler_uid,
            company_id=current_admin.company_id,
        )
    except Exception as error:
        _raise_http_error(error)


@router.get("/me", response_model=ActionHistoryListResponse)
def read_my_action_histories(
    action_status: Optional[ActionStatus] = Query(None),
    approval_status: Optional[ApprovalStatus] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return action_history_crud.get_my_action_histories(
        db,
        company_id=current_user.company_id,
        uid=current_user.uid,
        action_status=action_status.value if action_status else None,
        approval_status=approval_status.value if approval_status else None,
        page=page,
        size=size,
    )


@router.get(
    "/{action_history_id}",
    response_model=ActionHistoryDetailResponse,
)
def read_action_history_detail(
    action_history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    action = action_history_crud.get_action_history_detail(
        db,
        action_history_id=action_history_id,
        company_id=current_user.company_id,
    )
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="조치를 찾을 수 없습니다.",
        )
    if (
        current_user.role != "안전관리자"
        and action["handler_uid"] != current_user.uid
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 조치 이력을 조회할 권한이 없습니다.",
        )
    return action


@router.patch(
    "/{action_history_id}/complete",
    response_model=ActionHistoryDetailResponse,
)
def complete_action_history(
    action_history_id: int,
    content: str = Form(...),
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="조치 완료 내용은 필수입니다.",
        )

    previous = action_history_crud.get_action_history_detail(
        db,
        action_history_id=action_history_id,
        company_id=current_user.company_id,
    )
    image_url, new_file_path = _save_image(action_history_id, image)
    try:
        completed = action_history_crud.complete_action_history(
            db,
            action_history_id=action_history_id,
            company_id=current_user.company_id,
            handler_uid=current_user.uid,
            content=content,
            image_url=image_url,
        )
    except Exception as error:
        new_file_path.unlink(missing_ok=True)
        _raise_http_error(error)

    if previous and previous["image_url"] != image_url:
        _delete_local_image(previous["image_url"])
    return completed


@router.patch(
    "/{action_history_id}/approve",
    response_model=ActionHistoryDetailResponse,
)
def approve_action_history(
    action_history_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        return action_history_crud.approve_action_history(
            db,
            action_history_id=action_history_id,
            company_id=current_admin.company_id,
            approver_user=current_admin,
        )
    except Exception as error:
        _raise_http_error(error)


@router.patch(
    "/{action_history_id}/reject",
    response_model=ActionHistoryDetailResponse,
)
def reject_action_history(
    action_history_id: int,
    request: ActionHistoryRejectRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        return action_history_crud.reject_action_history(
            db,
            action_history_id=action_history_id,
            company_id=current_admin.company_id,
            approver_user=current_admin,
            rejection_reason=request.rejection_reason,
        )
    except Exception as error:
        _raise_http_error(error)
