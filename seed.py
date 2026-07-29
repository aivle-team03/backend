import sys
import os
from datetime import datetime, date, timedelta
import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트 경로 sys.path 추가
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from app.db.db import DATABASE_URL, Base
from app.models import (
    Company,
    User,
    CCTV,
    EventCategory,
    Event,
    Checklist,
    Report,
    ReportEventMap,
    ReportChecklistMap,
    Board,
    Education,
    EducationStatus,
    SignupCode,
    Inspection,
    InspectionHistory,
    ReportInspectionMap,
    ActionHistory,
    ReportActionMap
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def auto_migrate():
    """DB 스키마 자동 동기화 (신규 테이블 생성 및 기존 테이블 신규/변경된 컬럼 ALTER)"""
    with engine.connect() as conn:
        # 0. company 테이블 company_id 컬럼 변경/추가 보정
        try:
            conn.execute(text("ALTER TABLE company DROP PRIMARY KEY;"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE company ADD COLUMN company_id BIGINT AUTO_INCREMENT PRIMARY KEY FIRST;"))
            conn.commit()
            print("company 테이블에 company_id 컬럼 추가 완료.")
        except Exception:
            pass

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as me:
        print(f"[Seed] 테이블 일괄 생성 참고 (일부 FK 순서 지연): {me}")

    with engine.connect() as conn:
        # 1. board.updated_at 컬럼 추가
        try:
            conn.execute(text("ALTER TABLE board ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;"))
            conn.commit()
            print("board 테이블에 updated_at 컬럼 추가 완료.")
        except Exception:
            pass

        # 2. education.due_date 및 role 컬럼 변경
        try:
            conn.execute(text("ALTER TABLE education ADD COLUMN due_date DATE NULL;"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE education MODIFY COLUMN role VARCHAR(50) NULL;"))
            conn.commit()
            print("education 테이블 컬럼 조정 완료.")
        except Exception:
            pass

        # 3. cctv 테이블 컬럼 변경 (camera_name -> cctv_name, camera_id -> cctv_id)
        try:
            conn.execute(text("ALTER TABLE cctv CHANGE COLUMN camera_name cctv_name VARCHAR(100) NOT NULL;"))
            conn.commit()
            print("cctv 테이블에 cctv_name 컬럼 변경 완료.")
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE cctv CHANGE COLUMN camera_id cctv_id BIGINT AUTO_INCREMENT;"))
            conn.commit()
            print("cctv 테이블에 cctv_id 컬럼 변경 완료.")
        except Exception:
            pass

        # 4. user 테이블 category 컬럼 추가
        try:
            conn.execute(text("ALTER TABLE user ADD COLUMN category VARCHAR(100) NULL;"))
            conn.commit()
            print("user 테이블에 category 컬럼 추가 완료.")
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE user ADD COLUMN company_id BIGINT NULL;"))
            conn.commit()
            print("user 테이블에 company_id 컬럼 추가 완료.")
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE signup_code ADD COLUMN company_id BIGINT NOT NULL;"))
            conn.commit()
            print("signup_code 테이블에 company_id 컬럼 추가 완료.")
        except Exception:
            pass



def seed():
    # 0. 스키마 자동 동기화
    auto_migrate()

    db = SessionLocal()
    try:
        print("DB 시딩을 시작합니다...")

        company = db.query(Company).filter(Company.company_id == 1).first()
        if not company:
            company = Company(
                company_id=1,  # ID를 1로 명시
                company_name="AIVLE TEAM 03"
            )
            db.add(company)
            db.commit()      # 👈 여기서 DB에 실제 회사가 저장되어야 FK 에러가 안 납니다!
            db.refresh(company)
            print("기본 회사 (Company ID: 1) 세팅 완료.")

        company_id = company.company_id

        admin_invite_code = db.query(SignupCode).filter(SignupCode.code == "INV-ADMIN01").first()
        if not admin_invite_code:
            admin_invite_code = SignupCode(
                company_id=company_id,
                code="INV-ADMIN01",
                role="안전관리자",
                category=None,
                is_used=True
            )
            db.add(admin_invite_code)

        worker_invite_code = db.query(SignupCode).filter(SignupCode.code == "INV-WORKER1").first()
        if not worker_invite_code:
            worker_invite_code = SignupCode(
                company_id=company_id,
                code="INV-WORKER1",
                role="일반유저",
                category="지게차",
                is_used=False
            )
            db.add(worker_invite_code)
        db.commit()
        print("초대 코드 (SignupCode) 세팅 완료.")

        # 1. 유저 계정 생성 (관리자 & 작업자 계정)
        base_users = [
            {
                "user_id": "admin",
                "name": "최고관리자",
                "password": hash_password("admin123"),
                "role": "안전관리자",
                "category": None,
                "company_code": "AIVLE_TEAM03",
                "company_id": company_id
            },
            {
                "user_id": "worker1",
                "name": "김작업",
                "password": hash_password("worker123"),
                "role": "일반유저",
                "category": "지게차",
                "company_code": "AIVLE_TEAM03",
                "company_id": company_id
            },
            {
                "user_id": "worker2",
                "name": "이신규",
                "password": hash_password("worker123"),
                "role": "일반유저",
                "category": "화물트럭",
                "company_code": "AIVLE_TEAM03",
                "company_id": company_id
            }
        ]

        for i in range(3, 30):
            category_type = "지게차" if i % 2 == 0 else "화물트럭"
            base_users.append({
                "user_id": f"worker{i}",
                "name": f"작업자{i}",
                "password": hash_password("worker123"),
                "role": "일반유저",
                "category": category_type,
                "company_code": "AIVLE_TEAM03",
                "company_id": company_id
            })

        users = []

        for u_data in base_users:
            u = db.query(User).filter(User.user_id == u_data["user_id"]).first()
            if not u:
                u = User(**u_data)
                db.add(u)
                db.commit()
                db.refresh(u)
            users.append(u)

        admin_user = users[0]
        worker1_user = users[1]
        worker2_user = users[2]
        print(f"유저 계정 {len(users)}개 세팅 완료.")

        # 2. 이벤트 카테고리 등록
        categories_data = [
            {"category": "소방안전", "category_name": "화재 감지", "level": 9, "company_id": company_id},
            {"category": "시설안전", "category_name": "적재물", "level": 5, "company_id": company_id},
            {"category": "산업안전", "category_name": "충돌", "level": 7, "company_id": company_id},
            {"category": "기타", "category_name": "무단 침입", "level": 4, "company_id": company_id}
        ]
        
        categories = []
        for cat_data in categories_data:
            existing_cat = db.query(EventCategory).filter(
                EventCategory.category_name == cat_data["category_name"]
            ).first()
            if not existing_cat:
                new_cat = EventCategory(**cat_data)
                db.add(new_cat)
                db.commit()
                db.refresh(new_cat)
                categories.append(new_cat)
            else:
                categories.append(existing_cat)
        print(f"이벤트 카테고리 {len(categories)}종 세팅 완료.")

        # 3. CCTV 1대 등록
        existing_cctv = db.query(CCTV).filter(CCTV.company_id == company_id).first()
        if not existing_cctv:
            new_cctv = CCTV(
                company_id=company_id,
                cctv_name="메인 CCTV",
                location="공장 내부",
                stream_url="http://docs.evostream.com/sample_content/assets/bunny.mp4",
                status="정상"
            )
            db.add(new_cctv)
            db.commit()
            db.refresh(new_cctv)
            cctv = new_cctv
        else:
            cctv = existing_cctv
        print(f"CCTV 세팅 완료: {cctv.cctv_name} (id={cctv.cctv_id})")

        # 4. 이상 감지 이벤트 및 조치 Checklist 적재
        now = datetime.utcnow()
        events = db.query(Event).filter(Event.company_id == company_id).all()
        if len(events) < 10:
            print("더미 이상 감지 이벤트 및 점검 Checklist 적재를 시작합니다...")
            events = []
            for i in range(12):
                category = categories[i % len(categories)]
                date_offset = timedelta(days=random_offset_days(i), hours=i*2)
                event_date = now - date_offset
                
                new_event = Event(
                    company_id=company_id,
                    category_id=category.category_id,
                    cctv_id=cctv.cctv_id,
                    date=event_date,
                    image_url=f"/static/uploads/dummy_event_{i+1}.jpg"
                )
                db.add(new_event)
                db.commit()
                db.refresh(new_event)
                events.append(new_event)
                
            print(f"이상 감지 이벤트 {len(events)}건 적재 완료.")
            
            status_list = [
                ("조치 대기", "A동 복도 소화전 장애물 감지, 현장 확인 요청"),
                ("조치 대기", "B동 창고 통로 물품 차단 감지, 대피로 확보 바람"),
                ("조치 대기", "C동 하역장 유기물 불법 방치"),
                ("조치 중", "비상구 통로 적치물 정리 조치 중"),
                ("조치 중", "하역장 대피로 장애 유발 박스 제거 작업 중"),
                ("조치 중", "D동 구역 침입자 신원 확인 중"),
                ("승인 대기", "A동 복도 적치물 소거 조치 완료 및 사진 업로드"),
                ("승인 대기", "자재창고 가연물 이동 조치 완료 보고"),
                ("승인 완료", "화재 센서 오작동 확인 및 경보 해제 조치 완료"),
                ("승인 완료", "안전모 미착용 현장 작업자 안전 지도 완료")
            ]
            
            checklists = []
            for idx, (status_val, content) in enumerate(status_list):
                ev = events[idx]
                img_url = f"/static/uploads/action_resolved_{idx+1}.jpg" if status_val in ["승인 대기", "승인 완료"] else None
                
                chk = Checklist(
                    company_id=company_id,
                    event_id=ev.event_id,
                    date=ev.date + timedelta(hours=1),
                    status=status_val,
                    uid=admin_user.uid,
                    camera_id=ev.cctv_id,
                    content=content,
                    image_url=img_url,
                    type="조치"
                )
                db.add(chk)
                db.commit()
                db.refresh(chk)
                checklists.append(chk)
            print(f"체크리스트 조치 내역 {len(checklists)}건 세팅 완료.")

            # 4-1. 정기 점검 체크리스트 적재
            inspection_list = [
                ("점검 대기", "A동 복도 소화기 배치 상태 정기 점검"),
                ("점검 대기", "B동 자재창고 비상구 개폐 여부 확인"),
                ("점검 대기", "C동 하역장 안전 표지판 마모 상태 점검"),
                ("점검 완료", "D동 정문 CCTV 화각 및 녹화 상태 점검 완료"),
                ("점검 완료", "전 구역 소방 설비 작동 테스트 완료"),
            ]

            for idx, (insp_status, insp_content) in enumerate(inspection_list):
                insp_chk = Checklist(
                    company_id=company_id,
                    event_id=None,
                    date=now - timedelta(days=idx, hours=idx * 3),
                    status=insp_status,
                    uid=admin_user.uid,
                    camera_id=cctv.cctv_id,
                    content=insp_content,
                    image_url=None,
                    type="점검"
                )
                db.add(insp_chk)
                db.commit()
                db.refresh(insp_chk)
                checklists.append(insp_chk)
            print(f"정기 점검 체크리스트 {len(inspection_list)}건 추가 세팅 완료.")

        # 5. 정기 점검 Master (Inspection) 및 수행 이력 (InspectionHistory) 적재
        created_inspections = db.query(Inspection).filter(Inspection.company_id == company_id).all()
        created_histories = db.query(InspectionHistory).filter(InspectionHistory.company_id == company_id).all()

        if not created_inspections:
            print("정기 점검 Master (Inspection) 및 수행 이력 적재를 시작합니다...")
            inspections_data = [
                {
                    "name": "소화기 배치 상태 점검",
                    "category_id": categories[0].category_id,
                    "location": "A동 1층, B동 2층",
                    "cycle": "매주",
                    "content": "구역 내 소화기 압력계 정상 여부 및 적치물 가림 확인"
                },
                {
                    "name": "비상구 및 대피로 장애물 점검",
                    "category_id": categories[1].category_id,
                    "location": "A동 복도, B동 자재창고",
                    "cycle": "매일",
                    "content": "비상구 폐쇄 여부 및 통로 적치물 정리 상태 확인"
                },
                {
                    "name": "작업자 보호구 착용 실태 점검",
                    "category_id": categories[2].category_id,
                    "location": "C동 하역장, D동 정문",
                    "cycle": "매일",
                    "content": "안전모 및 안전화 착용 준수 여부 정기점검"
                },
            ]

            created_inspections = []
            for insp_d in inspections_data:
                insp = Inspection(
                    company_id=company_id,
                    **insp_d
                )
                db.add(insp)
                db.commit()
                db.refresh(insp)
                created_inspections.append(insp)

            print(f"정기 점검 Master {len(created_inspections)}건 생성 완료.")

            history_dummies = [
                {
                    "inspection_id": created_inspections[0].inspection_id,
                    "name": created_inspections[0].name,
                    "date": now - timedelta(days=2),
                    "location": "A동 1층",
                    "uid": admin_user.uid,
                    "status": "점검 완료",
                    "is_action_required": False,
                    "content": "소화기 외관 및 압력 상태 이상 없음 확인"
                },
                {
                    "inspection_id": created_inspections[0].inspection_id,
                    "name": created_inspections[0].name,
                    "date": now - timedelta(days=1),
                    "location": "B동 2층",
                    "uid": admin_user.uid,
                    "status": "점검 완료",
                    "is_action_required": True,
                    "content": "소화기 앞 박스 적치물 발견 -> 제거 조치 필요"
                },
                {
                    "inspection_id": created_inspections[1].inspection_id,
                    "name": created_inspections[1].name,
                    "date": now - timedelta(hours=5),
                    "location": "A동 복도",
                    "uid": worker1_user.uid,  # 점검 대기 건
                    "status": "점검 대기",
                    "is_action_required": False,
                    "content": "[매일 정기점검] A동 복도 자동 생성 건"
                },
                {
                    "inspection_id": created_inspections[1].inspection_id,
                    "name": created_inspections[1].name,
                    "date": now - timedelta(hours=3),
                    "location": "B동 자재창고",
                    "uid": worker1_user.uid,
                    "status": "점검 완료",
                    "is_action_required": False,
                    "content": "비상 통로 확보 양호"
                }
            ]

            created_histories = []
            for h_d in history_dummies:
                hist = InspectionHistory(
                    company_id=company_id,
                    **h_d
                )
                db.add(hist)
                db.commit()
                db.refresh(hist)
                created_histories.append(hist)

            print(f"점검 수행 이력 {len(created_histories)}건 적재 완료.")

        # 6. 게시판(Board) 적재
        boards = db.query(Board).filter(Board.company_id == company_id).all()
        if not boards:
            board1 = Board(
                company_id=company_id,
                uid=admin_user.uid,
                event_category_id=categories[1].category_id,
                title="B동 자재창고 통로 박스 적치 조치 요청",
                board_contents="B동 자재창고 비상구 통로 주변에 불법 가연성 적치물이 쌓여 있어 안전 조치를 요청합니다.",
                status="조치중",
                location="B동 자재창고",
                image_url="/static/uploads/board_sample_1.jpg"
            )
            board2 = Board(
                company_id=company_id,
                uid=worker1_user.uid,
                event_category_id=categories[0].category_id,
                title="A동 복도 소화기 배치 재점검 요청",
                board_contents="소화기 외관 점검 결과 일부 소화기 위치 이동 및 가압 점검이 필요합니다.",
                status="접수",
                location="A동 복도",
                image_url=None
            )
            db.add_all([board1, board2])
            db.commit()
            db.refresh(board1)
            db.refresh(board2)
            boards = [board1, board2]
            print("게시판 더미 데이터 2건 적재 완료.")
            
            
        if db.query(ActionHistory).filter(ActionHistory.company_id == company_id).count() == 0:
            print("조치 이력 (ActionHistory) 적재를 시작합니다 (모든 출처 및 상태 조합)...")
            
            action_dummies = [
                # -------------------------------------------------------------
                # 1) type = "게시판" (board_id 필수, event_id/inspection_history_id 없음)
                # -------------------------------------------------------------
                {
                    "type": "게시판",
                    "board_id": boards[0].board_id,
                    "event_id": None,
                    "inspection_history_id": None,
                    "category_id": categories[1].category_id,
                    "action_name": boards[0].title,
                    "location": boards[0].location,
                    "content": "비상 통로 적치물 정리 조치 요청 건입니다.",
                    "handler_uid": worker1_user.uid,
                    "action_status": "조치 대기",
                    "completed_at": None,
                    "image_url": None,
                    "approval_status": None,
                    "approver_uid": None,
                    "approval_date": None,
                    "rejection_reason": None,
                },
                {
                    "type": "게시판",
                    "board_id": boards[1].board_id,
                    "event_id": None,
                    "inspection_history_id": None,
                    "category_id": categories[0].category_id,
                    "action_name": boards[1].title,
                    "location": boards[1].location,
                    "content": "소화기 위치 재배치 및 가압 상태점검 완료했습니다.",
                    "handler_uid": worker2_user.uid,
                    "action_status": "조치 완료",
                    "completed_at": now - timedelta(hours=2),
                    "image_url": "/static/uploads/action_board_1.jpg",
                    "approval_status": "승인 완료",
                    "approver_uid": admin_user.uid,
                    "approval_date": now - timedelta(hours=1),
                    "rejection_reason": None,
                },

                # -------------------------------------------------------------
                # 2) type = "이벤트" (event_id 필수, board_id/inspection_history_id 없음)
                # -------------------------------------------------------------
                {
                    "type": "이벤트",
                    "board_id": None,
                    "event_id": events[0].event_id,
                    "inspection_history_id": None,
                    "category_id": events[0].category_id,
                    "action_name": "화재 감지 알림 현장 확인",
                    "location": cctv.location,
                    "content": "화재 센서 감지 후 현장 출동 및 단순 오작동 처리 완료.",
                    "handler_uid": worker1_user.uid,
                    "action_status": "조치 완료",
                    "completed_at": now - timedelta(days=1),
                    "image_url": "/static/uploads/action_event_1.jpg",
                    "approval_status": "승인 대기",
                    "approver_uid": None,
                    "approval_date": None,
                    "rejection_reason": None,
                },
                {
                    "type": "이벤트",
                    "board_id": None,
                    "event_id": events[1].event_id,
                    "inspection_history_id": None,
                    "category_id": events[1].category_id,
                    "action_name": "불법 적치물 치우기",
                    "location": cctv.location,
                    "content": "적치물 정리 완료했으나 사진 미비로 반려 처리된 건.",
                    "handler_uid": worker2_user.uid,
                    "action_status": "조치 대기",
                    "completed_at": None,
                    "image_url": None,
                    "approval_status": "반려",
                    "approver_uid": admin_user.uid,
                    "approval_date": now - timedelta(hours=4),
                    "rejection_reason": "조치 전/후 비교 사진이 누락되었습니다. 다시 첨부 바랍니다.",
                },

                # -------------------------------------------------------------
                # 3) type = "점검이력" (inspection_history_id 필수, board_id/event_id 없음)
                # -------------------------------------------------------------
                {
                    "type": "점검이력",
                    "board_id": None,
                    "event_id": None,
                    "inspection_history_id": created_histories[1].inspection_history_id,
                    "category_id": created_inspections[0].category_id,
                    "action_name": created_histories[1].name,
                    "location": created_histories[1].location,
                    "content": "소화기 가림 박스 치우고 통로 확보했습니다.",
                    "handler_uid": worker1_user.uid,
                    "action_status": "조치 완료",
                    "completed_at": now - timedelta(hours=6),
                    "image_url": "/static/uploads/action_inspection_1.jpg",
                    "approval_status": "승인 완료",
                    "approver_uid": admin_user.uid,
                    "approval_date": now - timedelta(hours=2),
                    "rejection_reason": None,
                },

                # -------------------------------------------------------------
                # 4) type = "직접추가" (board_id/event_id/inspection_history_id 모두 없음)
                # -------------------------------------------------------------
                {
                    "type": "직접추가",
                    "board_id": None,
                    "event_id": None,
                    "inspection_history_id": None,
                    "category_id": categories[2].category_id,
                    "action_name": "하역장 근로자 보호구 특별 지도",
                    "location": "C동 하역장",
                    "content": "안전모 미착용 근로자 안전 지도 및 보호구 지급 조치",
                    "handler_uid": worker2_user.uid,
                    "action_status": "조치 대기",
                    "completed_at": None,
                    "image_url": None,
                    "approval_status": None,
                    "approver_uid": None,
                    "approval_date": None,
                    "rejection_reason": None,
                }
            ]

            created_actions = []
            for act_d in action_dummies:
                act = ActionHistory(
                    company_id=company_id,
                    **act_d
                )
                db.add(act)
                db.commit()
                db.refresh(act)
                created_actions.append(act)

            print(f"조치 이력 (ActionHistory) {len(created_actions)}건 적재 완료.")
        else:
            print("조치 이력 데이터가 이미 존재합니다.")
            
        if db.query(Report).filter(Report.company_id == company_id).count() == 0:
            report1 = Report(
                company_id=company_id,
                uid=admin_user.uid,
                content="7월 2주차 사내 소방 안전 및 대피로 장애물 점검 주간 리포트입니다. B동 자재창고의 장애물이 빈번히 조치 대기 상태로 전이되어 부서별 안전 교육을 권장합니다.",
                summary="7월 2주차 사내 소방안전 주간 보고서",
                created_at=now - timedelta(days=2)
            )
            report2 = Report(
                company_id=company_id,
                uid=admin_user.uid,
                content="A동 정기 소화시설 작동 여부 및 복도 비상구 확보 현황 종합 보고서입니다. 감지된 모든 장애물은 현재 조치 완료(승인 완료) 처리되었습니다.",
                summary="A동 비상대피로 정기 점검 리포트",
                created_at=now - timedelta(days=1)
            )
            db.add(report1)
            db.add(report2)
            db.commit()
            db.refresh(report1)
            db.refresh(report2)
            print("종합 안전 통계 리포트 2건 생성 완료.")

            existing_events = db.query(Event).all()
            existing_checklists = db.query(Checklist).all()
            existing_histories = db.query(InspectionHistory).all()
            existing_actions = db.query(ActionHistory).all()

            if existing_events and existing_checklists:
                map1 = ReportEventMap(report_id=report1.report_id, event_id=existing_events[0].event_id)
                map2 = ReportEventMap(report_id=report1.report_id, event_id=existing_events[1].event_id)
                map3 = ReportChecklistMap(report_id=report1.report_id, checklist_id=existing_checklists[0].checklist_id)
                db.add_all([map1, map2, map3])

            if existing_histories:
                map4 = ReportInspectionMap(report_id=report2.report_id, inspection_history_id=existing_histories[0].inspection_history_id)
                db.add(map4)

            if existing_actions:
                map5 = ReportActionMap(report_id=report1.report_id, action_history_id=existing_actions[0].action_history_id)
                db.add(map5)

            db.commit()
            print("리포트-이벤트/체크리스트/점검이력/조치이력 연동 맵 테이블 적재 완료.")

        # 7. 안전 교육(Education) 및 수강 이수 현황(EducationStatus) 적재
        # 기존 교육 상태 데이터 초기화 (다시 채우기 위해)
        db.query(EducationStatus).delete()
        
        if db.query(Education).count() == 0:
            edu1 = Education(
                company_id=company_id,
                title="사업장 정기 소방 안전 필수 교육 2026",
                video_url="https://youtube.com/watch?v=fire_safety_2026",
                category="전체",
                type="필수",
            )
            edu2 = Education(
                company_id=company_id,
                title="비상구 및 대피로 유지관리 현장 실무 가이드",
                video_url="https://youtube.com/watch?v=evacuation_guide",
                category="지게차",
                type="정기",
            )
            edu3 = Education(
                company_id=company_id,
                title="신규 근로자 맞춤형 산업안전 기본 수칙",
                video_url="https://youtube.com/watch?v=ppe_rules",
                category="화물트럭",
                type="필수",
            )
            db.add_all([edu1, edu2, edu3])
            db.commit()

        edus = db.query(Education).all()
        today = date.today()

        if edus:
            statuses = []
            for idx, u in enumerate(users):
                if idx < 18:
                    st = "이수"
                    c_date = today - timedelta(days=idx % 5 + 1)
                elif idx < 26:
                    st = "진행중"
                    c_date = None
                else:
                    st = "미이수"
                    c_date = None
                statuses.append(EducationStatus(uid=u.uid, education_id=edus[0].education_id, status=st, completed_date=c_date))

            if len(edus) > 1:
                for idx, u in enumerate(users):
                    if idx < 22:
                        st = "이수"
                        c_date = today - timedelta(days=idx % 3 + 1)
                    elif idx < 27:
                        st = "진행중"
                        c_date = None
                    else:
                        st = "미이수"
                        c_date = None
                    statuses.append(EducationStatus(uid=u.uid, education_id=edus[1].education_id, status=st, completed_date=c_date))

            if len(edus) > 2:
                new_workers = [u for u in users if u.role == "신규 근로자"]
                for idx, u in enumerate(new_workers):
                    if idx < 10:
                        st = "이수"
                        c_date = today - timedelta(days=idx % 2 + 1)
                    elif idx < 13:
                        st = "진행중"
                        c_date = None
                    else:
                        st = "미이수"
                        c_date = None
                    statuses.append(EducationStatus(uid=u.uid, education_id=edus[2].education_id, status=st, completed_date=c_date))

            db.add_all(statuses)
            db.commit()
            print("교육 수강 이수 현황 데이터 풍성하게 적재 완료!")

        print("DB 시딩이 성공적으로 완료되었습니다!")
    except Exception as e:
        db.rollback()
        print(f"시딩 중 오류 발생: {e}")
        raise e
    finally:
        db.close()


def random_offset_days(i):
    return (i * 2) % 28 + 1


if __name__ == "__main__":
    seed()
