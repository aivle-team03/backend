from datetime import date, timedelta # timedelta : 날짜 간격 계산
from typing import Optional, List, Dict # List, Dict : 리스트, 딕셔너리

from sqlalchemy import and_, or_, func # and_, or_ : 조건 결합, func : 함수 사용
from sqlalchemy.orm import Session 

from app.models.education import Education
from app.models.education_status import EducationStatus
from app.models.user import User


INCOMPLETE = "미이수"
IN_PROGRESS = "진행중"
COMPLETED = "이수"
PROGRESS_STATUSES = (INCOMPLETE, IN_PROGRESS, COMPLETED)


def get_user_by_uid(db: Session, uid: int, company_id: int) -> Optional[User]:
    return db.query(User).filter(User.uid == uid, User.company_id == company_id).first()


def get_education_by_id(
    db: Session,
    education_id: int,
    company_id: int,
) -> Optional[Education]:
    return (
        db.query(Education)
        .filter(
            Education.education_id == education_id,
            Education.company_id == company_id
        )
        .first()
    )


def get_my_education_list(
    db: Session,
    user: User,
    category: Optional[str] = None,
):
    query = db.query(Education).filter(Education.company_id == user.company_id)
    if category:
        query = query.filter(Education.category == category)
    return query.order_by(Education.education_id.asc()).all()


def _apply_completion_filter(query, completion_status: Optional[str]):
    if completion_status == COMPLETED:
        return query.filter(EducationStatus.status == COMPLETED)
    if completion_status == INCOMPLETE:
        return query.filter(
            or_(
                EducationStatus.status.is_(None),
                EducationStatus.status.in_([INCOMPLETE, IN_PROGRESS]),
            )
        )
    return query


def _status_response(education: Education, status_row: Optional[EducationStatus]):
    progress_status = status_row.status if status_row else INCOMPLETE
    return {
        "education_id": education.education_id,
        "title": education.title,
        "video_url": education.video_url,
        "category": education.category,
        "type": education.type,
        "status": progress_status,
        "completed_date": status_row.completed_date if status_row else None, # 이수 완료일
    }


def get_user_education_statuses(
    db: Session,
    user: User,
    category: Optional[str] = None,
    completion_status: Optional[str] = None,
):
    query = (
        db.query(Education, EducationStatus)
        .filter(Education.company_id == user.company_id)
        .outerjoin(
            EducationStatus,
            and_(
                EducationStatus.education_id == Education.education_id,
                EducationStatus.uid == user.uid,
            ),
        )
    )
    if category:
        query = query.filter(Education.category == category)
    query = _apply_completion_filter(query, completion_status)

    rows = query.order_by(Education.education_id.asc()).all()
    return [
        _status_response(education, status_row)
        for education, status_row in rows
    ]

# 1. 일반 유저: 이번주 마감, 진행 중, 이수 완료 요약 건수
def get_user_education_summary_counts(db: Session, user: User) -> Dict[str, int]:
    statuses = get_user_education_statuses(db, user=user)

    due_this_week = 0  # due_date가 없어졌으므로 기본 0건 처리 (필요시 '미이수' 건수 등으로 대체 가능)
    in_progress = 0
    completed = 0

    for item in statuses:
        st = item["status"]

        if st == COMPLETED:
            completed += 1
        elif st == IN_PROGRESS:
            in_progress += 1

    return {
        "due_this_week_count": due_this_week,
        "in_progress_count": in_progress,
        "completed_count": completed
    }


# 2. 일반 유저: 필수/정기/전체 교육 이수율(%)
def get_user_completion_rates(db: Session, user: User) -> Dict[str, float]:
    statuses = get_user_education_statuses(db, user=user)

    essential_total = 0
    essential_completed = 0
    regular_total = 0
    regular_completed = 0

    for item in statuses:
        edu_type = item["type"]
        is_done = (item["status"] == COMPLETED)

        if edu_type == "필수":
            essential_total += 1
            if is_done:
                essential_completed += 1
        elif edu_type == "정기":
            regular_total += 1
            if is_done:
                regular_completed += 1

    total_count = len(statuses)
    total_completed = sum(1 for i in statuses if i["status"] == COMPLETED)

    return {
        "essential_rate": round(essential_completed / essential_total * 100, 1) if essential_total else 0.0,
        "regular_rate": round(regular_completed / regular_total * 100, 1) if regular_total else 0.0,
        "total_rate": round(total_completed / total_count * 100, 1) if total_count else 0.0,
    }

def get_user_education_for_admin(
    db: Session,
    user: User,
    category: Optional[str] = None,
    completion_status: Optional[str] = None,
):
    return {
        "uid": user.uid,
        "company_id": user.company_id,
        "user_id": user.user_id,
        "name": user.name,
        "educations": get_user_education_statuses(
            db,
            user=user,
            category=category,
            completion_status=completion_status,
        ),
    }

def get_education_status_summaries(
    db: Session,
    company_id: int,
    education_id: Optional[int] = None,
    completion_status: Optional[str] = None,
):
    education_query = db.query(Education).filter(Education.company_id == company_id)
    if education_id is not None:
        education_query = education_query.filter(
            Education.education_id == education_id
        )

    summaries = []
    for education in education_query.order_by(Education.education_id.asc()).all():

        rows = (
            db.query(User.uid, EducationStatus.status)
            .filter(User.company_id == company_id)
            .outerjoin(
                EducationStatus,
                and_(
                    EducationStatus.uid == User.uid,
                    EducationStatus.education_id == education.education_id,
                ),
            )
            .all()
        )

        counts = {status: 0 for status in PROGRESS_STATUSES}
        for _, progress_status in rows:
            counts[progress_status or INCOMPLETE] += 1

        if completion_status == COMPLETED and counts[COMPLETED] == 0:
            continue
        if (
            completion_status == INCOMPLETE
            and counts[INCOMPLETE] + counts[IN_PROGRESS] == 0
        ):
            continue

        target_count = len(rows)
        completion_rate = (
            round(counts[COMPLETED] / target_count * 100, 1)
            if target_count
            else 0.0
        )
        summaries.append(
            {
                "education_id": education.education_id,
                "company_id": education.company_id,
                "title": education.title,
                "category": education.category,
                "type": education.type,
                "target_count": target_count,
                "status_counts": [
                    {"status": status, "count": counts[status]}
                    for status in PROGRESS_STATUSES
                ],
                "completion_rate": completion_rate,
            }
        )
    return summaries


def get_role_completion_stats(db: Session, company_id: int) -> Dict:
    rows = (
        db.query(User.role, EducationStatus.status)
        .select_from(User)
        .join(Education, Education.company_id == User.company_id)
        .filter(User.company_id == company_id)
        .outerjoin(
            EducationStatus,
            and_(EducationStatus.uid == User.uid, EducationStatus.education_id == Education.education_id),
        )
        .all()
    )
    counts_by_role = {}
    for role, status in rows:
        counts = counts_by_role.setdefault(role or "미분류", {"target": 0, "completed": 0})
        counts["target"] += 1
        if status == COMPLETED:
            counts["completed"] += 1

    roles = [
        {
            "role": role,
            "target_count": counts["target"],
            "completed_count": counts["completed"],
            "completion_rate": round(counts["completed"] / counts["target"] * 100, 1) if counts["target"] else 0.0,
        }
        for role, counts in counts_by_role.items()
    ]
    total_target = sum(item["target_count"] for item in roles)
    total_completed = sum(item["completed_count"] for item in roles)
    return {
        "roles": roles,
        "total_completion_rate": round(total_completed / total_target * 100, 1) if total_target else 0.0,
    }


def get_education_attendees(db: Session, company_id: int, education_id: int) -> Dict:
    rows = (
        db.query(User, EducationStatus)
        .filter(User.company_id == company_id)
        .outerjoin(
            EducationStatus,
            and_(EducationStatus.uid == User.uid, EducationStatus.education_id == education_id),
        )
        .order_by(User.name.asc())
        .all()
    )
    attendees = [
        {
            "uid": user.uid,
            "name": user.name,
            "category": user.category,
            "status": status_row.status if status_row else INCOMPLETE,
            "completed_date": status_row.completed_date if status_row else None,
        }
        for user, status_row in rows
    ]
    completed_count = sum(1 for attendee in attendees if attendee["status"] == COMPLETED)
    target_count = len(attendees)
    return {
        "education_id": education_id,
        "target_count": target_count,
        "completed_count": completed_count,
        "completion_rate": round(completed_count / target_count * 100, 1) if target_count else 0.0,
        "attendees": attendees,
    }


def get_role_education_attendees(db: Session, company_id: int, role: Optional[str] = None) -> Dict:
    query = (
        db.query(User, Education, EducationStatus)
        .select_from(User)
        .join(Education, Education.company_id == User.company_id)
        .outerjoin(
            EducationStatus,
            and_(EducationStatus.uid == User.uid, EducationStatus.education_id == Education.education_id),
        )
        .filter(User.company_id == company_id)
    )
    if role and role != "전체":
        query = query.filter(User.role == role)

    rows = query.order_by(User.name.asc(), Education.title.asc()).all()
    attendees = [
        {
            "uid": user.uid,
            "name": user.name,
            "category": user.category,
            "education_id": education.education_id,
            "education_title": education.title,
            "status": status_row.status if status_row else INCOMPLETE,
            "completed_date": status_row.completed_date if status_row else None,
        }
        for user, education, status_row in rows
    ]
    completed_count = sum(1 for attendee in attendees if attendee["status"] == COMPLETED)
    target_count = len(attendees)
    return {
        "education_id": 0,
        "target_count": target_count,
        "completed_count": completed_count,
        "completion_rate": round(completed_count / target_count * 100, 1) if target_count else 0.0,
        "attendees": attendees,
    }


def complete_education(
    db: Session,
    user: User,
    education: Education,
) -> EducationStatus:
    status_row = (
        db.query(EducationStatus)
        .filter(
            EducationStatus.uid == user.uid,
            EducationStatus.education_id == education.education_id,
        )
        .first()
    )
    if status_row is None:
        status_row = EducationStatus(
            uid=user.uid,
            education_id=education.education_id,
        )
        db.add(status_row)

    status_row.status = COMPLETED
    status_row.completed_date = date.today()
    db.commit()
    db.refresh(status_row)
    return status_row


# 4. AI 교육 자료 자동 생성 로직
def create_ai_generated_education(
    db: Session,
    company_id: int,
    work_type: str,
    equipment: str,
    risk_factor: str
) -> Dict:
    title = f"[{work_type}] {equipment} 사용 시 {risk_factor} 사고 예방 안전수칙"
    summary = f"{work_type} 작업 중 {equipment} 조종 시 발생하기 쉬운 {risk_factor} 사고 방지를 위한 필수 안전 가이드입니다."
    guidelines = [
        f"작업 전 {equipment} 기계 장비의 안전점검 및 보호구 착용 확인",
        f"{work_type} 작업 주변 안전구역 확보 및 서행 운행",
        f"{risk_factor} 위험요소 사전 제거 및 2인 1조 작업 수행"
    ]

    new_edu = Education(
        company_id=company_id,
        title=title,
        video_url="/static/videos/ai_safety_sample.mp4",
        category=work_type,
        type="필수",
    )
    db.add(new_edu)
    db.commit()
    db.refresh(new_edu)

    return {
        "education_id": new_edu.education_id,
        "company_id": new_edu.company_id,
        "title": title,
        "summary": summary,
        "safety_guideline": guidelines,
        "generated_video_url": new_edu.video_url
    }
