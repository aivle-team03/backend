from datetime import date
from typing import Optional

from sqlalchemy import and_, or_
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
    query = db.query(Education).filter(Education.role == user.role)
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
        "status": progress_status,
        "completed_date": status_row.completed_date if status_row else None,
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
        .filter(Education.role == user.role)
    )
    if category:
        query = query.filter(Education.category == category)
    query = _apply_completion_filter(query, completion_status)

    rows = query.order_by(Education.education_id.asc()).all()
    return [
        _status_response(education, status_row)
        for education, status_row in rows
    ]


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
    if role:
        education_query = education_query.filter(Education.role == role)

    summaries = []
    for education in education_query.order_by(Education.education_id.asc()).all():
        rows = (
            db.query(User.uid, EducationStatus.status)
            .outerjoin(
                EducationStatus,
                and_(
                    EducationStatus.uid == User.uid,
                    EducationStatus.education_id == education.education_id,
                ),
            )
            .filter(User.role == education.role)
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
