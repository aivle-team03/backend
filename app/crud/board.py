# app/crud/board.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.models.action_history import ActionHistory
from app.models.board import Board
from app.models.user import User
from app.schemas.action_history import ActionStatus, SourceType

# 생성
def create_board(
    db: Session,
    company_id: int,
    uid: int,
    title: str,
    board_contents: str,
    event_category_id: Optional[int],
    status: str,
    location: Optional[str],
    image_url: Optional[str]
) -> Board:
    db_board = Board(
        company_id=company_id,
        uid=uid,
        title=title,
        board_contents=board_contents,
        event_category_id=event_category_id,
        status=status,
        location=location,
        image_url=image_url,
        is_deleted=False,
    )
    db.add(db_board)
    db.commit()
    db.refresh(db_board)
    return db_board

# 조회
def get_boards(
    db: Session,
    company_id: int,
    page: int = 1,
    size: int = 10,
    category: Optional[int] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    keyword: Optional[str] = None
):
    query = (
        db.query(Board, User.name.label("writer_name"))
        .outerjoin(User, Board.uid == User.uid)
        .filter(
            Board.company_id == company_id,
            Board.is_deleted == False,
        )
    )
    
    if category:
        query = query.filter(Board.event_category_id == category)
    if status:
        query = query.filter(Board.status == status)
    if location:
        query = query.filter(Board.location.like(f"%{location}%"))
    if keyword:
        query = query.filter(
            or_(
                Board.title.like(f"%{keyword}%"),
                Board.board_contents.like(f"%{keyword}%")
            )
        )

    total = query.count()
    rows = query.order_by(Board.created_at.desc()).offset((page - 1) * size).limit(size).all()

    items = []
    for board, writer_name in rows:
        item_dict = {
            "board_id": board.board_id,
            "company_id": board.company_id,
            "uid": board.uid,
            "writer": writer_name or "알 수 없음",
            "title": board.title,
            "board_contents": board.board_contents,
            "event_category_id": board.event_category_id,
            "status": board.status,
            "location": board.location,
            "image_url": board.image_url,
            "created_at": board.created_at,
            "updated_at": getattr(board, "updated_at", None),
        }
        items.append(item_dict)

    return total, items

# 게시글 ID로 상세 조회
def get_board_by_id(db: Session, board_id: int, company_id: int):
    row = (
        db.query(Board, User.name.label("writer_name"))
        .outerjoin(User, Board.uid == User.uid)
        .filter(
            Board.board_id == board_id,
            Board.company_id == company_id,
            Board.is_deleted == False,
        )
        .first()
    )

    if not row:
        return None

    board, writer_name = row
    return {
        "board_id": board.board_id,
        "company_id": board.company_id,
        "uid": board.uid,
        "writer": writer_name or "알 수 없음",
        "title": board.title,
        "board_contents": board.board_contents,
        "event_category_id": board.event_category_id,
        "status": board.status,
        "location": board.location,
        "image_url": board.image_url,
        "created_at": board.created_at,
        "updated_at": getattr(board, "updated_at", None),
    }

# 게시글 수정
def update_board(
    db: Session,
    board: Board,
    title: Optional[str] = None,
    board_contents: Optional[str] = None,
    event_category_id: Optional[int] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    image_url: Optional[str] = None
) -> Board:
    if title is not None:
        board.title = title
    if board_contents is not None:
        board.board_contents = board_contents
    if event_category_id is not None:
        board.event_category_id = event_category_id
    if status is not None:
        board.status = status
    if location is not None:
        board.location = location
    if image_url is not None:
        board.image_url = image_url

    db.commit()
    db.refresh(board)
    return board

# 게시글 상태 수정 및 게시판 조치 이력 생성
def update_board_status(
    db: Session,
    board_id: int,
    company_id: int,
    status: str,
) -> Optional[Board]:
    # Lock the board row so concurrent requests cannot create duplicate actions.
    board = db.query(Board).filter(
        Board.board_id == board_id,
        Board.company_id == company_id,
        Board.is_deleted == False,
    ).with_for_update().first()
    if not board:
        return None

    received_status = "\uC811\uC218"
    if status == received_status and board.status != received_status:
        existing_action = db.query(ActionHistory).filter(
            ActionHistory.company_id == company_id,
            ActionHistory.board_id == board.board_id,
            ActionHistory.type == SourceType.BOARD.value,
            ActionHistory.is_deleted == False,
        ).first()

        if not existing_action:
            if not board.event_category_id:
                raise ValueError(
                    "\uAC8C\uC2DC\uAE00 \uCE74\uD14C\uACE0\uB9AC\uAC00 \uC5C6\uC5B4 \uC870\uCE58 \uD56D\uBAA9\uC744 \uC0DD\uC131\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4."
                )

            db.add(ActionHistory(
                company_id=company_id,
                board_id=board.board_id,
                category_id=board.event_category_id,
                action_name=board.title,
                type=SourceType.BOARD.value,
                location=board.location or "\uC704\uCE58 \uBBF8\uC9C0\uC815",
                content=board.board_contents,
                action_status=ActionStatus.WAITING.value,
                before_image_url=board.image_url,
                is_deleted=False,
            ))

    board.status = status
    try:
        db.commit()
        db.refresh(board)
    except Exception:
        db.rollback()
        raise

    return board

# 게시글 삭제
def delete_board(db: Session, board: Board):
    board.is_deleted = True
    db.commit()
