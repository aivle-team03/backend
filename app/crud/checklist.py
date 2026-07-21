from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.checklist import Checklist
from app.models.user import User
from app.schemas.checklist import ChecklistCreate

def get_checklists(db: Session, checklist_type: str = None):
    query = db.query(Checklist)
    if checklist_type:
        if checklist_type in ["regular", "정기", "현장"]:
            query = query.filter(Checklist.event_id == None)
        elif checklist_type in ["event", "이벤트", "이상"]:
            query = query.filter(Checklist.event_id != None)
        else:
            query = query.filter(Checklist.status == checklist_type)
    return query.all()

def search_managers(db: Session, keyword: str):
    return db.query(User).filter(
        or_(
            User.name.contains(keyword),
            User.user_id.contains(keyword)
        )
    ).all()

def assign_manager(db: Session, checklist_id: int, user_id: str):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None
        
    db_checklist = db.query(Checklist).filter(Checklist.checklist_id == checklist_id).first()
    if not db_checklist:
        return None
        
    db_checklist.uid = user.uid
    db_checklist.status = "조치 중"
    db.commit()
    db.refresh(db_checklist)
    return db_checklist

def complete_checklist(db: Session, checklist_id: int, image_url: str, content: str):
    db_checklist = db.query(Checklist).filter(Checklist.checklist_id == checklist_id).first()
    if not db_checklist:
        return None
        
    db_checklist.image_url = image_url
    db_checklist.content = content
    db_checklist.status = "승인 대기"
    db.commit()
    db.refresh(db_checklist)
    return db_checklist

def update_checklist_status(db: Session, checklist_id: int, status: str, reason: str = None):
    db_checklist = db.query(Checklist).filter(Checklist.checklist_id == checklist_id).first()
    if not db_checklist:
        return None
        
    db_checklist.status = status
    if status == "반려" and reason:
        db_checklist.content = f"{db_checklist.content} (반려사유: {reason})"
        
    db.commit()
    db.refresh(db_checklist)
    return db_checklist

def get_my_checklists(db: Session, uid: int, skip: int = 0, limit: int = 100):
    return db.query(Checklist).filter(Checklist.uid == uid)\
             .order_by(Checklist.date.desc())\
             .offset(skip).limit(limit).all()

def create_checklist(db: Session, checklist_in: ChecklistCreate):

    user_id = getattr(checklist_in, 'uid', None)
    if user_id is None:
        user_id = 1  # 1번 유저가 DB에 존재해야 함

    # 2. 🚀 event_id가 0이면 외래키 에러가 나므로 None(NULL)으로 변환
    evt_id = getattr(checklist_in, 'event_id', None)
    if evt_id == 0:
        evt_id = None  

    db_checklist = Checklist(
        event_id=evt_id,
        camera_id=checklist_in.camera_id,
        content=checklist_in.content,
        image_url=checklist_in.image_url,
        status="미조치",
        date=datetime.now(),
        uid=user_id
    )
    
    db.add(db_checklist)
    db.commit()
    db.refresh(db_checklist)
    return db_checklist
