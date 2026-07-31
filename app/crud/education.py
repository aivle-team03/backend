from datetime import date, timedelta # timedelta : 날짜 간격 계산
from typing import Optional, List, Dict # List, Dict : 리스트, 딕셔너리

from sqlalchemy import and_, or_, func # and_, or_ : 조건 결합, func : 함수 사용
from sqlalchemy.orm import Session 

from app.models.education import Education
from app.models.education_status import EducationStatus
from app.models.user import User
from app.crud.signup_code import get_available_categories


INCOMPLETE = "미이수"
IN_PROGRESS = "진행중"
COMPLETED = "이수"
PROGRESS_STATUSES = (INCOMPLETE, IN_PROGRESS, COMPLETED)
ALL_EMPLOYEE_CATEGORIES = {"공통"}


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


# 5. 관리자용 카테고리별 이수 현황 통계 조회
def get_category_completion_stats(db: Session, company_id: int) -> Dict:
    educations = (
        db.query(Education)
        .filter(Education.company_id == company_id)
        .all()
    )

    categories = list(set([edu.category for edu in educations if edu.category]))
    
    user_cats = (
        db.query(User.category)
        .filter(User.company_id == company_id, User.category.isnot(None))
        .distinct()
        .all()
    )
    for (ucat,) in user_cats:
        if ucat and ucat not in categories:
            categories.append(ucat)

    if not categories:
        categories = ["공통", "지게차", "화물트럭"]

    categories.sort()

    total_users_count = (
        db.query(func.count(User.uid))
        .filter(User.company_id == company_id)
        .scalar()
    ) or 0

    category_stats = []
    total_target = 0
    total_completed = 0

    for cat in categories:
        cat_edus = [e for e in educations if e.category == cat]
        if cat_edus:
            cat_edu_ids = [e.education_id for e in cat_edus]
            cat_target = len(cat_edu_ids) * total_users_count
            cat_completed = (
                db.query(func.count(EducationStatus.uid))
                .join(User, User.uid == EducationStatus.uid)
                .filter(
                    User.company_id == company_id,
                    EducationStatus.education_id.in_(cat_edu_ids),
                    EducationStatus.status == COMPLETED,
                )
                .scalar()
            ) or 0
        else:
            cat_users_count = (
                db.query(func.count(User.uid))
                .filter(User.company_id == company_id, User.category == cat)
                .scalar()
            ) or 0
            cat_target = len(educations) * cat_users_count
            cat_completed = (
                db.query(func.count(EducationStatus.uid))
                .join(User, User.uid == EducationStatus.uid)
                .filter(
                    User.company_id == company_id,
                    User.category == cat,
                    EducationStatus.status == COMPLETED,
                )
                .scalar()
            ) or 0

        rate = round(cat_completed / cat_target * 100, 1) if cat_target > 0 else 0.0
        category_stats.append(
            {
                "category": cat,
                "target_count": cat_target,
                "completed_count": cat_completed,
                "completion_rate": rate,
            }
        )
        total_target += cat_target
        total_completed += cat_completed

    overall_rate = round(total_completed / total_target * 100, 1) if total_target > 0 else 0.0

    return {
        "categories": category_stats,
        "total_completion_rate": overall_rate,
    }


def get_admin_education_dashboard(db: Session, company_id: int) -> Dict:
    """교육 관리 화면의 카드, 과정 목록, 상세 모달 데이터를 한 번에 만든다."""
    users = (
        db.query(User)
        .filter(User.company_id == company_id)
        .order_by(User.uid.asc())
        .all()
    )
    educations = (
        db.query(Education)
        .filter(Education.company_id == company_id)
        .order_by(Education.education_id.asc())
        .all()
    )
    education_ids = [education.education_id for education in educations]
    statuses = (
        db.query(EducationStatus)
        .join(User, User.uid == EducationStatus.uid)
        .filter(User.company_id == company_id, EducationStatus.education_id.in_(education_ids))
        .all()
        if education_ids else []
    )
    status_by_assignment = {(status.uid, status.education_id): status for status in statuses}

    def is_all_employee_course(education: Education) -> bool:
        return education.category in ALL_EMPLOYEE_CATEGORIES

    def is_target(user: User, education: Education) -> bool:
        return is_all_employee_course(education) or education.category == user.category

    def attendee_for(user: User, education: Education) -> Dict:
        status = status_by_assignment.get((user.uid, education.education_id))
        return {
            "uid": user.uid,
            "name": user.name,
            "category": user.category,
            "education_id": education.education_id,
            "education_title": education.title,
            "status": status.status if status else INCOMPLETE,
            "completed_date": status.completed_date if status else None,
        }

    courses = []
    for education in educations:
        attendees = [attendee_for(user, education) for user in users if is_target(user, education)]
        completed_count = sum(item["status"] == COMPLETED for item in attendees)
        target_count = len(attendees)
        counts = {progress_status: sum(item["status"] == progress_status for item in attendees) for progress_status in PROGRESS_STATUSES}
        courses.append({
            "education_id": education.education_id,
            "company_id": education.company_id,
            "title": education.title,
            "category": education.category,
            "type": education.type,
            "target_count": target_count,
            "status_counts": [{"status": key, "count": value} for key, value in counts.items()],
            "completion_rate": round(completed_count / target_count * 100, 1) if target_count else 0.0,
            "attendees": attendees,
        })

    categories = [category for category in get_available_categories() if category not in ALL_EMPLOYEE_CATEGORIES]
    for user in users:
        if user.category and user.category not in ALL_EMPLOYEE_CATEGORIES and user.category not in categories:
            categories.append(user.category)

    category_items = []
    for category in categories:
        category_users = [user for user in users if user.category == category]
        applicable_courses = [education for education in educations if is_all_employee_course(education) or education.category == category]
        summary_attendees = []
        for user in category_users:
            assignments = [status_by_assignment.get((user.uid, education.education_id)) for education in applicable_courses]
            is_completed = bool(assignments) and all(item and item.status == COMPLETED for item in assignments)
            completed_dates = [item.completed_date for item in assignments if item and item.completed_date]
            summary_attendees.append({
                "uid": user.uid,
                "name": user.name,
                "category": user.category,
                "education_title": f"{category} 교육 이수 현황",
                "status": COMPLETED if is_completed else INCOMPLETE,
                "completed_date": max(completed_dates) if is_completed and completed_dates else None,
            })
        completed_count = sum(item["status"] == COMPLETED for item in summary_attendees)
        target_count = len(summary_attendees)
        category_items.append({
            "category": category,
            "target_count": target_count,
            "completed_count": completed_count,
            "completion_rate": round(completed_count / target_count * 100, 1) if target_count else 0.0,
            "attendees": [
                attendee_for(user, education)
                for user in category_users
                for education in applicable_courses
            ],
        })

    overall_summary = []
    for user in users:
        applicable_courses = [education for education in educations if is_target(user, education)]
        assignments = [status_by_assignment.get((user.uid, education.education_id)) for education in applicable_courses]
        is_completed = bool(assignments) and all(item and item.status == COMPLETED for item in assignments)
        completed_dates = [item.completed_date for item in assignments if item and item.completed_date]
        overall_summary.append({
            "uid": user.uid,
            "name": user.name,
            "category": user.category,
            "education_title": "전체 교육 이수 현황",
            "status": COMPLETED if is_completed else INCOMPLETE,
            "completed_date": max(completed_dates) if is_completed and completed_dates else None,
        })

    total_target_count = len(users)
    total_completed_count = sum(item["status"] == COMPLETED for item in overall_summary)
    return {
        "courses": courses,
        "categories": category_items,
        "total_target_count": total_target_count,
        "total_completed_count": total_completed_count,
        "total_completion_rate": round(total_completed_count / total_target_count * 100, 1) if total_target_count else 0.0,
        "attendees": [attendee_for(user, education) for user in users for education in educations if is_target(user, education)],
    }

