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


def get_user_by_uid(db: Session, uid: int) -> Optional[User]:
    return db.query(User).filter(User.uid == uid).first()


def get_education_by_id(
    db: Session,
    education_id: int,
) -> Optional[Education]:
    return (
        db.query(Education)
        .filter(Education.education_id == education_id)
        .first()
    )


def get_my_education_list(
    db: Session,
    user: User,
    category: Optional[str] = None,
):
    query = db.query(Education).filter(
        or_(Education.role == user.role, Education.role == "전체")
    )
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
        "role": education.role,
        "video_url": education.video_url,
        "category": education.category,
        "type": education.type,
        "due_date": education.due_date, # 만료일
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
        .outerjoin(
            EducationStatus,
            and_(
                EducationStatus.education_id == Education.education_id,
                EducationStatus.uid == user.uid,
            ),
        )
        .filter(or_(Education.role == user.role, Education.role == "전체"))
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
    today = date.today()
    week_end = today + timedelta(days=7)

    statuses = get_user_education_statuses(db, user=user)

    due_this_week = 0
    in_progress = 0
    completed = 0

    for item in statuses:
        st = item["status"]
        due = item["due_date"]

        if st == COMPLETED:
            completed += 1
        elif st == IN_PROGRESS:
            in_progress += 1

        if st != COMPLETED and due and today <= due <= week_end:
            due_this_week += 1

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


# 3. 관리자: 직군별 교육 이수 현황 통계
def get_admin_role_completion_stats(db: Session) -> Dict:
    roles = ["신규 근로자", "일반 작업자", "특수 작업자", "안전 관리자"]
    role_results = []
    
    grand_target = 0
    grand_completed = 0

    for r in roles:
        users_in_role = db.query(User).filter(User.role == r).all()
        edus_in_role = db.query(Education).filter(
            or_(Education.role == r, Education.role == "전체")
        ).all()

        target_count = len(users_in_role) * len(edus_in_role)
        if target_count == 0:
            role_results.append({
                "role": r,
                "completion_rate": 0.0,
                "target_count": 0,
                "completed_count": 0
            })
            continue

        completed_count = (
            db.query(EducationStatus)
            .join(User, EducationStatus.uid == User.uid)
            .join(Education, EducationStatus.education_id == Education.education_id)
            .filter(
                User.role == r,
                or_(Education.role == r, Education.role == "전체"),
                EducationStatus.status == COMPLETED
            )
            .count()
        )

        grand_target += target_count
        grand_completed += completed_count

        rate = round(completed_count / target_count * 100, 1) if target_count else 0.0
        role_results.append({
            "role": r,
            "completion_rate": rate,
            "target_count": target_count,
            "completed_count": completed_count
        })

    total_rate = round(grand_completed / grand_target * 100, 1) if grand_target else 0.0
    return {
        "roles": role_results,
        "total_completion_rate": total_rate
    }


def get_user_education_for_admin(
    db: Session,
    user: User,
    category: Optional[str] = None,
    completion_status: Optional[str] = None,
):
    return {
        "uid": user.uid,
        "user_id": user.user_id,
        "name": user.name,
        "role": user.role,
        "educations": get_user_education_statuses(
            db,
            user=user,
            category=category,
            completion_status=completion_status,
        ),
    }


def get_education_status_summaries(
    db: Session,
    education_id: Optional[int] = None,
    completion_status: Optional[str] = None,
    role: Optional[str] = None,
):
    education_query = db.query(Education)
    if education_id is not None:
        education_query = education_query.filter(
            Education.education_id == education_id
        )
    if role and role != "전체":
        education_query = education_query.filter(
            or_(Education.role == role, Education.role == "전체")
        )

    summaries = []
    for education in education_query.order_by(Education.education_id.asc()).all():
        user_filter = (
            (User.role == education.role)
            if education.role != "전체"
            else True
        )

        rows = (
            db.query(User.uid, EducationStatus.status)
            .outerjoin(
                EducationStatus,
                and_(
                    EducationStatus.uid == User.uid,
                    EducationStatus.education_id == education.education_id,
                ),
            )
            .filter(user_filter)
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
                "title": education.title,
                "role": education.role,
                "category": education.category,
                "type": education.type,
                "due_date": education.due_date,
                "target_count": target_count,
                "status_counts": [
                    {"status": status, "count": counts[status]}
                    for status in PROGRESS_STATUSES
                ],
                "completion_rate": completion_rate,
            }
        )
    return summaries


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
        title=title,
        role="전체",
        video_url="/static/videos/ai_safety_sample.mp4",
        category=work_type,
        type="필수",
        due_date=date.today() + timedelta(days=14)
    )
    db.add(new_edu)
    db.commit()
    db.refresh(new_edu)

    return {
        "education_id": new_edu.education_id,
        "title": title,
        "summary": summary,
        "safety_guideline": guidelines,
        "generated_video_url": new_edu.video_url
    }
