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


def _allowed_education_categories(user: User) -> List[str]:
    """이 사용자에게 보여야 할 education.category 값 목록.

    education.category 에는 두 축의 값이 들어온다.
      - 업무 단위: 지게차, 화물트럭 ...  → user.category 와 매칭
      - 직책 단위: 안전관리자, 관제사 ... → user.role 과 매칭
    프론트의 '이수 대상'이 직책 목록이라 role 도 함께 봐야 교육이 노출된다.
    """
    allowed = list(ALL_EMPLOYEE_CATEGORIES)
    for value in (user.category, user.role):
        if value and value not in allowed:
            allowed.append(value)
    return allowed


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
            Education.company_id == company_id,
            Education.is_deleted == False,
        )
        .first()
    )


def get_my_education_list(
    db: Session,
    user: User,
    category: Optional[str] = None,
):
    allowed_categories = _allowed_education_categories(user)

    query = db.query(Education).filter(
        Education.company_id == user.company_id,
        Education.is_deleted == False,
        Education.category.in_(allowed_categories),
    )
    if category:
        query = query.filter(Education.category == category)
    return query.order_by(Education.education_id.desc()).all()


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
        "video_url_en": education.video_url_en,
        "category": education.category,
        "type": education.type,
        "due_date": education.due_date,
        "status": progress_status,
        "completed_date": status_row.completed_date if status_row else None, # 이수 완료일
        "last_position_seconds": status_row.last_position_seconds if status_row else 0,
        "progress_percent": status_row.progress_percent if status_row else 0.0,
    }


def get_user_education_statuses(
    db: Session,
    user: User,
    category: Optional[str] = None,
    completion_status: Optional[str] = None,
):
    allowed_categories = _allowed_education_categories(user)

    query = (
        db.query(Education, EducationStatus)
        .filter(
            Education.company_id == user.company_id,
            Education.is_deleted == False,
            Education.category.in_(allowed_categories),
        )
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

    rows = query.order_by(Education.education_id.desc()).all()
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
    education_query = db.query(Education).filter(Education.company_id == company_id, Education.is_deleted == False,)
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
    education = (
        db.query(Education)
        .filter(
            Education.education_id == education_id,
            Education.company_id == company_id,
            Education.is_deleted == False,
        )
        .first()
    )

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

    # 이 교육이 실제로 노출되는 사람만 대상자로 센다. 전원을 분모로 쓰면
    # 업무별 교육의 이수율이 실제보다 낮게 나온다.
    if education:
        rows = [
            (user, status_row)
            for user, status_row in rows
            if education.category in _allowed_education_categories(user)
        ]

    attendees = [
        {
            "uid": user.uid,
            "name": (
                user.name
                if user
                else (status_row.user_name if status_row else "퇴사자")
            ),
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
            user_name=user.name,
            education_id=education.education_id,
        )
        db.add(status_row)
    else:
        status_row.user_name = user.name

    status_row.status = COMPLETED
    status_row.progress_percent = 100.0
    status_row.completed_date = date.today()
    db.commit()
    db.refresh(status_row)
    return status_row


def update_education_progress(
    db: Session,
    user: User,
    education: Education,
    last_position_seconds: int,
    progress_percent: float,
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
            user_name=user.name,
            education_id=education.education_id,
        )
        db.add(status_row)
    else:
        status_row.user_name = user.name

    status_row.last_position_seconds = max(0, last_position_seconds)
    status_row.progress_percent = min(100.0, max(0.0, progress_percent))

    # 80% 이상시 자동 이수 처리
    if status_row.progress_percent >= 80.0:
        status_row.status = COMPLETED
        if not status_row.completed_date:
            status_row.completed_date = date.today()
    elif status_row.progress_percent > 0.0 and status_row.status == INCOMPLETE:
        status_row.status = IN_PROGRESS

    db.commit()
    db.refresh(status_row)
    return status_row


def save_generated_education(
    db: Session,
    company_id: int,
    video_url: str,
    title: Optional[str] = None,
    category: Optional[str] = None,
    type: Optional[str] = None,
    due_date: Optional[date] = None,
    video_url_en: Optional[str] = None,
) -> Education:
    """영상 생성 서비스가 완료한 결과를 Education 테이블에 적재한다.

    프론트가 상태를 5초마다 폴링하므로 완료 후에도 같은 요청이 여러 번 들어온다.
    video_url은 task_id 기반이라 작업당 유일하므로, 이를 기준으로 기존 레코드를 먼저 찾아
    중복 적재를 막는다.
    """
    existing = (
        db.query(Education)
        .filter(
            Education.company_id == company_id,
            Education.video_url == video_url,
            Education.is_deleted == False,
        )
        .first()
    )
    if existing:
        existing.title = title or existing.title
        existing.category = category or existing.category
        existing.type = type or existing.type
        existing.due_date = due_date
        # 더빙 실패로 None 이 들어올 수 있다. 이미 저장된 더빙판을 지우지 않는다.
        existing.video_url_en = video_url_en or existing.video_url_en
        db.commit()
        db.refresh(existing)
        return existing

    new_edu = Education(
        company_id=company_id,
        title=title or "Veo AI 현장 안전 교육",
        video_url=video_url,
        video_url_en=video_url_en,
        category=category or "공통",
        type=type or "필수",
        due_date=due_date,
        is_deleted=False,
    )
    db.add(new_edu)
    db.commit()
    db.refresh(new_edu)
    return new_edu


# 5. 관리자용 카테고리별 이수 현황 통계 조회
def get_category_completion_stats(db: Session, company_id: int) -> Dict:
    educations = (
        db.query(Education)
        .filter(Education.company_id == company_id, Education.is_deleted == False,)
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
        .filter(Education.company_id == company_id, Education.is_deleted == False,)
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
            "video_url": education.video_url,
            "category": education.category,
            "type": education.type,
            "due_date": education.due_date,
            "target_count": target_count,
            "status_counts": [{"status": key, "count": value} for key, value in counts.items()],
            "completion_rate": round(completed_count / target_count * 100, 1) if target_count else 0.0,
            "attendees": attendees,
        })

    categories = [category for category in get_available_categories() if category not in ALL_EMPLOYEE_CATEGORIES]
    for user in users:
        if user.category and user.category not in ALL_EMPLOYEE_CATEGORIES and user.category not in categories:
            categories.append(user.category)

    def _assignment_counts(target_users, target_courses) -> tuple:
        """(사용자 × 교육) 쌍을 세어 이수 건수와 전체 건수를 돌려준다.

        예전에는 '해당 교육을 하나도 빠짐없이 다 들은 사람 수'로 셌다. 그 방식은
        교육을 하나 새로 등록할 때마다 이수율이 뚝 떨어지고, 5개 중 4개를 끝낸 사람이
        0으로 잡혀 코스별 이수율과 숫자가 크게 어긋나 보였다.
        """
        total = 0
        completed = 0
        for user in target_users:
            for education in target_courses:
                total += 1
                status = status_by_assignment.get((user.uid, education.education_id))
                if status and status.status == COMPLETED:
                    completed += 1
        return completed, total

    category_items = []
    for category in categories:
        category_users = [user for user in users if user.category == category]
        applicable_courses = [education for education in educations if is_all_employee_course(education) or education.category == category]
        completed_count, target_count = _assignment_counts(category_users, applicable_courses)
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

    # 전체 카드도 카테고리 카드와 같은 기준으로 센다. 한쪽만 사람 수로 두면
    # '전체'가 카테고리 합계와 맞지 않아 보인다.
    total_completed_count = 0
    total_target_count = 0
    for user in users:
        applicable_courses = [education for education in educations if is_target(user, education)]
        completed, total = _assignment_counts([user], applicable_courses)
        total_completed_count += completed
        total_target_count += total
    return {
        "courses": courses,
        "categories": category_items,
        "total_target_count": total_target_count,
        "total_completed_count": total_completed_count,
        "total_completion_rate": round(total_completed_count / total_target_count * 100, 1) if total_target_count else 0.0,
        "attendees": [attendee_for(user, education) for user in users for education in educations if is_target(user, education)],
    }

