from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from datetime import datetime
from app.models.event import Event
from app.models.checklist import Checklist

def get_monitoring_events(db: Session, cctv_id: int = None, status: str = None, skip: int = 0, limit: int = 100):
    # 1. 각 event_id 별 최신 checklist_id를 찾기 위한 서브쿼리 정의
    subq = db.query(
        Checklist.event_id,
        func.max(Checklist.checklist_id).label("max_checklist_id")
    ).group_by(Checklist.event_id).subquery()

    # 2. 메인 쿼리 (관계 테이블 선제 로딩)
    query = db.query(Event).options(
        joinedload(Event.category),
        joinedload(Event.cctv),
        joinedload(Event.checklists)
    )

    if cctv_id is not None:
        query = query.filter(Event.camera_id == cctv_id)

    # 3. 조치 상태(status) 필터 처리
    if status is not None:
        if status == "미조치":
            # Checklist가 아예 없거나, 최신 Checklist의 status가 "미조치"인 경우
            query = query.outerjoin(subq, Event.event_id == subq.c.event_id)\
                         .outerjoin(Checklist, Checklist.checklist_id == subq.c.max_checklist_id)\
                         .filter(or_(Checklist.status == "미조치", Checklist.checklist_id == None))
        else:
            # 해당 조치 상태인 경우 (예: "조치 완료", "조치 중" 등)
            query = query.join(subq, Event.event_id == subq.c.event_id)\
                         .join(Checklist, Checklist.checklist_id == subq.c.max_checklist_id)\
                         .filter(Checklist.status == status)

    events = query.order_by(Event.date.desc()).offset(skip).limit(limit).all()

    # 4. 각 이벤트 객체에 current_status 동적 바인딩
    for event in events:
        if event.checklists:
            latest_chk = max(event.checklists, key=lambda c: c.checklist_id)
            event.current_status = latest_chk.status
        else:
            event.current_status = "미조치"

    return events

def get_monitoring_event_by_id(db: Session, event_id: int):
    event = db.query(Event).options(
        joinedload(Event.category),
        joinedload(Event.cctv),
        joinedload(Event.checklists)
    ).filter(Event.event_id == event_id).first()

    if event:
        if event.checklists:
            latest_chk = max(event.checklists, key=lambda c: c.checklist_id)
            event.current_status = latest_chk.status
        else:
            event.current_status = "미조치"
    return event

def create_action_request(db: Session, event_id: int, target_uid: int, message: str):
    # 1. 대상 이벤트 조회하여 정보 확보
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        return None
        
    # 2. Checklist 테이블에 조치 요청 내역 생성
    db_checklist = Checklist(
        event_id=event_id,
        date=datetime.utcnow(),
        status="조치 대기",
        uid=target_uid,
        camera_id=event.camera_id,
        content=message,
        image_url=None
    )
    db.add(db_checklist)
    db.commit()
    db.refresh(db_checklist)
    return db_checklist
