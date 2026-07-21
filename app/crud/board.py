# app/crud/board.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.models.board import Board

# 생성
def create_board(
    db: Session,
    uid: int,
    title: str,
    board_contents: str,
    event_category_id: Optional[int],
    status: str,
    location: Optional[str],
    image_url: Optional[str]
) -> Board:
    db_board = Board(
        uid=uid,
        title=title,
        board_contents=board_contents,
        event_category_id=event_category_id,
        status=status,
        location=location,
        image_url=image_url
    )
    db.add(db_board)
    db.commit()
    db.refresh(db_board)
    return db_board

# 조회
def get_boards(
    db: Session,
    page: int = 1,
    size: int = 10,
    category: Optional[int] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    keyword: Optional[str] = None
):
    query = db.query(Board)

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
    items = query.order_by(Board.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return total, items

# 게시글 ID로 상세 조회
def get_board_by_id(db: Session, board_id: int) -> Optional[Board]:
    return db.query(Board).filter(Board.board_id == board_id).first()

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

# 게시글 상태 수정
def update_board_status(db: Session, board: Board, status: str) -> Board:
    board.status = status
    db.commit()
    db.refresh(board)
    return board

# 게시글 삭제
def delete_board(db: Session, board: Board):
    db.delete(board)
    db.commit()
