from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.checklist import Checklist
from app.models.user import User
from app.schemas.checklist import ChecklistCreate

def get_checklists_by_role(
    db: Session, 
    user: User, 
    checklist_type: Optional[str] = None
) -> List[Checklist]:
    query = db.query(Checklist)

    if user.role != "안전 관리자":
        query = query.filter(Checklist.uid == user.uid)
    if checklist_type:
        if checklist_type in ["점검", "regular", "ROUTINE"]:
            query = query.filter(Checklist.type == "점검")
        elif checklist_type in ["조치", "action", "ACTION"]:
            query = query.filter(Checklist.type == "조치")
        else:
            query = query.filter(Checklist.status == checklist_type)
    else:
        query = query.filter(
            or_(
                Checklist.type == "점검",
                and_(
                    Checklist.type == "조치",
                    Checklist.status != "승인 완료"
                )
            )
        )

    return query.order_by(Checklist.date.desc()).all()

def get_action_history_by_role(
    db: Session, 
    user: User, 
    skip: int = 0, 
    limit: int = 100
) -> List[Checklist]:
    query = db.query(Checklist)

    # 🚀 type이 '조치'이거나, 상태가 조치 진행/완료 관련 단계인 건들을 모두 가져옴
    query = query.filter(
        or_(
            Checklist.type == "조치",
            Checklist.status.in_(["조치 중", "승인 대기", "조치 완료", "승인 완료", "조치 필요"])
        )
    )

    # 일반 현장 작업자일 경우 본인 조치 이력만 조회
    if user.role != "안전 관리자":
        query = query.filter(Checklist.uid == user.uid)

    return query.order_by(Checklist.date.desc()).offset(skip).limit(limit).all()

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

def complete_checklist(
    db: Session, 
    checklist_id: int, 
    image_url: str, 
    content: str
) -> Optional[Checklist]:
    db_checklist = db.query(Checklist).filter(Checklist.checklist_id == checklist_id).first()
    if not db_checklist:
        return None
        
    db_checklist.image_url = image_url
    db_checklist.content = content
    db_checklist.status = "승인 대기"  # 승인 대기 상태로 전환
    
    db.commit()
    db.refresh(db_checklist)
    return db_checklist

def update_checklist_status(
    db: Session, 
    checklist_id: int, 
    status: str, 
    reason: Optional[str] = None
) -> Optional[Checklist]:
    db_checklist = db.query(Checklist).filter(Checklist.checklist_id == checklist_id).first()
    if not db_checklist:
        return None
        
    if status in ["반려", "REJECTED"]:
        db_checklist.status = "조치 필요"
        if reason:
            db_checklist.content = f"{db_checklist.content} [반려사유: {reason}]"
    else:
        db_checklist.status = status

    db.commit()
    db.refresh(db_checklist)
    return db_checklist

def get_my_checklists(db: Session, uid: int, skip: int = 0, limit: int = 100):
    return db.query(Checklist).filter(Checklist.uid == uid)\
             .order_by(Checklist.date.desc())\
             .offset(skip).limit(limit).all()

def create_checklist(db: Session, checklist_in: ChecklistCreate) -> Checklist:
    evt_id = getattr(checklist_in, 'event_id', None)
    if evt_id == 0:
        evt_id = None

    chk_type = getattr(checklist_in, 'type', None)
    if not chk_type:
        chk_type = "조치" if evt_id is not None else "점검"

    db_checklist = Checklist(
        event_id=evt_id,
        camera_id=checklist_in.camera_id,
        content=checklist_in.content,
        image_url=checklist_in.image_url,
        status="미조치" if chk_type == "조치" else "점검 대기",
        type=chk_type,
        date=datetime.now(),
        uid=1
    )
    
    db.add(db_checklist)
    db.commit()
    db.refresh(db_checklist)
    return db_checklist

def delete_checklist(db: Session, checklist_id: int) -> bool:
    db_checklist = db.query(Checklist).filter(Checklist.checklist_id == checklist_id).first()
    if not db_checklist:
        return False
    
    db.delete(db_checklist)
    db.commit()
    return True
