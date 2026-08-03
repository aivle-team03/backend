import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.endpoints.agent_inspection_action import router
from app.crud import agent_inspection_action as agent_crud
from app.crud.auth import get_current_admin
from app.db.agent_read_db import get_agent_read_db
from app.models.agent_read import (
    agent_action_history_read,
    agent_event_category_read,
    agent_inspection_history_read,
    agent_inspection_read,
    agent_read_metadata,
    agent_user_display_read,
)


class AgentInspectionActionCrudTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        agent_read_metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.execute(
            agent_event_category_read.insert(),
            [
                {
                    "category_id": 10,
                    "company_id": 1,
                    "category": "점검",
                    "category_name": "전기 안전",
                    "level": 3,
                },
                {
                    "category_id": 20,
                    "company_id": 2,
                    "category": "점검",
                    "category_name": "타사 점검",
                    "level": 1,
                },
            ],
        )
        self.db.execute(
            agent_user_display_read.insert(),
            [
                {"uid": 100, "company_id": 1, "name": "담당자", "role": "현장관리자"},
                {"uid": 200, "company_id": 2, "name": "타사", "role": "현장관리자"},
            ],
        )
        self.db.execute(
            agent_inspection_read.insert(),
            [
                {
                    "inspection_id": 1,
                    "company_id": 1,
                    "category_id": 10,
                    "uid": 100,
                    "name": "배전반 점검",
                    "location": "A동",
                    "cycle": "매일",
                    "content": "온도 확인",
                },
                {
                    "inspection_id": 2,
                    "company_id": 2,
                    "category_id": 20,
                    "uid": 200,
                    "name": "타사 점검",
                    "location": "B동",
                    "cycle": "매주",
                    "content": None,
                },
            ],
        )
        self.db.execute(
            agent_inspection_history_read.insert(),
            {
                "inspection_history_id": 11,
                "company_id": 1,
                "inspection_id": 1,
                "uid": 100,
                "user_name": "이전 담당자명",
                "name": "배전반 점검",
                "location": "A동",
                "date": datetime(2026, 8, 3, 9, 0),
                "status": "점검 완료",
                "is_action_required": True,
                "content": "과열 확인",
            },
        )
        self.db.execute(
            agent_action_history_read.insert(),
            {
                "action_history_id": 21,
                "company_id": 1,
                "inspection_history_id": 11,
                "category_id": 10,
                "handler_uid": 100,
                "handler_name": "담당자",
                "approver_uid": None,
                "approver_name": None,
                "action_name": "배전반 냉각",
                "source_type": "점검이력",
                "source_id": 11,
                "location": "A동",
                "created_at": datetime(2026, 8, 3, 10, 0),
                "completed_at": None,
                "action_status": "조치 대기",
                "content": "냉각팬 교체",
                "approval_status": None,
                "approval_date": None,
                "rejection_reason": None,
            },
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_queries_are_scoped_to_company_and_return_safe_relations(self):
        inspections = agent_crud.get_inspections(
            self.db, company_id=1, offset=0, limit=20
        )
        histories = agent_crud.get_inspection_histories(
            self.db, company_id=1, offset=0, limit=20
        )
        actions = agent_crud.get_action_histories(
            self.db, company_id=1, offset=0, limit=20
        )

        self.assertEqual(inspections["total_items"], 1)
        self.assertEqual(inspections["items"][0]["user_name"], "담당자")
        self.assertEqual(histories["summary"]["action_required_count"], 1)
        self.assertEqual(actions["summary"]["waiting_count"], 1)
        self.assertEqual(actions["items"][0]["source_id"], 11)
        self.assertNotIn("board_id", actions["items"][0])
        self.assertNotIn("event_id", actions["items"][0])


class AgentInspectionActionApiTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/agent-data/inspection-action")
        self.admin = SimpleNamespace(uid=7, company_id=41, role="안전관리자")
        app.dependency_overrides[get_current_admin] = lambda: self.admin
        app.dependency_overrides[get_agent_read_db] = lambda: object()
        self.client = TestClient(app)

    @patch("app.api.endpoints.agent_inspection_action.agent_crud.get_inspections")
    def test_company_id_is_taken_from_authenticated_admin(self, get_inspections):
        get_inspections.return_value = {
            "items": [],
            "total_items": 0,
            "offset": 0,
            "limit": 20,
        }

        response = self.client.get(
            "/api/agent-data/inspection-action/inspections?company_id=999"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_inspections.call_args.kwargs["company_id"], 41)

    @patch("app.db.agent_read_db.AgentReadSessionLocal", None)
    def test_agent_database_fails_closed_without_read_only_configuration(self):
        dependency = get_agent_read_db()
        with self.assertRaises(HTTPException) as context:
            next(dependency)
        self.assertEqual(context.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
