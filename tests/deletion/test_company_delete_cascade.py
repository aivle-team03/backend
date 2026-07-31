"""회사 삭제 시 관련 DB 데이터가 연쇄 삭제되는지 검증한다."""

import unittest
from datetime import datetime

from sqlalchemy import create_engine, delete, event, func, select
from sqlalchemy.orm import Session

from app.db.db import Base
from app.models import (
    ActionHistory,
    Board,
    CCTV,
    Checklist,
    Company,
    Education,
    EducationStatus,
    Event,
    EventCategory,
    Inspection,
    InspectionHistory,
    Report,
    ReportActionMap,
    ReportChecklistMap,
    ReportEventMap,
    ReportInspectionMap,
    SignupCode,
    User,
)


class CompanyDeleteCascadeTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_deleting_company_removes_all_owned_rows(self):
        now = datetime(2026, 7, 30, 12, 0, 0)

        with Session(self.engine) as db:
            db.add_all(
                [
                    Company(company_id=1, company_name="삭제 대상"),
                    Company(company_id=2, company_name="유지 대상"),
                    User(
                        uid=101,
                        user_id="delete-user",
                        name="삭제 사용자",
                        password="hashed",
                        role="일반유저",
                        company_id=1,
                    ),
                    User(
                        uid=201,
                        user_id="keep-user",
                        name="유지 사용자",
                        password="hashed",
                        role="일반유저",
                        company_id=2,
                    ),
                ]
            )
            db.flush()

            db.add(
                SignupCode(
                    id=1,
                    company_id=1,
                    code="DELETE-CODE",
                    role="일반유저",
                    is_used=True,
                    used_by_uid=101,
                )
            )
            db.add(
                CCTV(
                    cctv_id=1,
                    cctv_name="삭제 CCTV",
                    location="A동",
                    stream_url="rtsp://example/delete",
                    status="running",
                    company_id=1,
                )
            )
            db.add(
                EventCategory(
                    category_id=1,
                    company_id=1,
                    category="위험",
                    category_name="삭제 카테고리",
                    level=1,
                )
            )
            db.flush()

            db.add(
                Event(
                    event_id=1,
                    company_id=1,
                    category_id=1,
                    cctv_id=1,
                    date=now,
                )
            )
            db.add(
                Board(
                    board_id=1,
                    company_id=1,
                    uid=101,
                    event_category_id=1,
                    title="삭제 게시글",
                    board_contents="삭제 게시글 내용",
                    status="접수",
                )
            )
            db.add(
                Education(
                    education_id=1,
                    company_id=1,
                    title="삭제 교육",
                    video_url="/static/videos/delete.mp4",
                    category="공통",
                    type="필수",
                )
            )
            db.add(
                Inspection(
                    inspection_id=1,
                    company_id=1,
                    category_id=1,
                    name="삭제 점검",
                    location="A동",
                    cycle="매일",
                )
            )
            db.flush()

            db.add(
                Checklist(
                    checklist_id=1,
                    event_id=1,
                    date=now,
                    status="점검 대기",
                    uid=101,
                    camera_id=1,
                    content="삭제 체크리스트",
                    type="점검",
                    company_id=1,
                )
            )
            db.add(
                EducationStatus(
                    uid=101,
                    education_id=1,
                    status="이수",
                )
            )
            db.add(
                InspectionHistory(
                    inspection_history_id=1,
                    company_id=1,
                    inspection_id=1,
                    uid=101,
                    name="삭제 점검 이력",
                    location="A동",
                    date=now,
                    status="점검 완료",
                    is_action_required=True,
                )
            )
            db.flush()

            db.add(
                ActionHistory(
                    action_history_id=1,
                    company_id=1,
                    board_id=1,
                    category_id=1,
                    handler_uid=101,
                    action_name="삭제 조치",
                    type="게시판",
                    location="A동",
                    content="삭제 조치 내용",
                    action_status="조치 대기",
                )
            )
            db.add(
                Report(
                    report_id=1,
                    uid=101,
                    content="삭제 보고서",
                    summary="삭제 요약",
                    company_id=1,
                )
            )
            db.flush()

            db.add_all(
                [
                    ReportEventMap(report_id=1, event_id=1),
                    ReportChecklistMap(report_id=1, checklist_id=1),
                    ReportInspectionMap(
                        report_id=1,
                        inspection_history_id=1,
                    ),
                    ReportActionMap(
                        id=1,
                        report_id=1,
                        action_history_id=1,
                    ),
                ]
            )
            db.commit()

            db.execute(delete(Company).where(Company.company_id == 1))
            db.commit()

            direct_company_models = (
                User,
                SignupCode,
                CCTV,
                EventCategory,
                Event,
                Checklist,
                Board,
                Education,
                Inspection,
                InspectionHistory,
                ActionHistory,
                Report,
            )
            for model in direct_company_models:
                remaining = db.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.company_id == 1)
                )
                self.assertEqual(remaining, 0, model.__tablename__)

            indirect_models = (
                EducationStatus,
                ReportEventMap,
                ReportChecklistMap,
                ReportInspectionMap,
                ReportActionMap,
            )
            for model in indirect_models:
                remaining = db.scalar(
                    select(func.count()).select_from(model)
                )
                self.assertEqual(remaining, 0, model.__tablename__)

            self.assertIsNotNone(db.get(Company, 2))
            self.assertIsNotNone(db.get(User, 201))

    def test_user_reference_rules_do_not_block_company_cascade(self):
        with Session(self.engine) as db:
            db.add(Company(company_id=1, company_name="사용자 참조 테스트"))
            db.add(
                User(
                    uid=101,
                    user_id="referenced-user",
                    name="참조 사용자",
                    password="hashed",
                    role="일반유저",
                    company_id=1,
                )
            )
            db.add(
                EventCategory(
                    category_id=1,
                    company_id=1,
                    category="위험",
                    category_name="사용자 참조 카테고리",
                    level=1,
                )
            )
            db.add(
                Education(
                    education_id=1,
                    company_id=1,
                    title="사용자 참조 교육",
                    video_url="/static/videos/reference.mp4",
                    category="공통",
                    type="필수",
                )
            )
            db.flush()

            db.add_all(
                [
                    SignupCode(
                        id=1,
                        company_id=1,
                        code="REFERENCE-CODE",
                        role="일반유저",
                        is_used=True,
                        used_by_uid=101,
                    ),
                    Board(
                        board_id=1,
                        company_id=1,
                        uid=101,
                        event_category_id=1,
                        title="사용자 참조 게시글",
                        board_contents="사용자 참조 내용",
                        status="접수",
                    ),
                    Report(
                        report_id=1,
                        uid=101,
                        content="사용자 참조 보고서",
                        summary="사용자 참조 요약",
                        company_id=1,
                    ),
                    ActionHistory(
                        action_history_id=1,
                        company_id=1,
                        category_id=1,
                        handler_uid=101,
                        action_name="사용자 참조 조치",
                        type="직접추가",
                        location="A동",
                        content="사용자 참조 조치 내용",
                        action_status="조치 대기",
                    ),
                    EducationStatus(
                        uid=101,
                        education_id=1,
                        status="이수",
                    ),
                ]
            )
            db.commit()

            db.execute(delete(User).where(User.uid == 101))
            db.commit()

            self.assertIsNone(db.get(Board, 1).uid)
            self.assertIsNone(db.get(Report, 1).uid)
            self.assertIsNone(db.get(ActionHistory, 1).handler_uid)
            self.assertIsNone(db.get(SignupCode, 1).used_by_uid)
            self.assertIsNone(db.get(EducationStatus, (101, 1)))

            db.execute(delete(Company).where(Company.company_id == 1))
            db.commit()
            self.assertIsNone(db.get(Company, 1))


if __name__ == "__main__":
    unittest.main()
