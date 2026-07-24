import sys
import os
from datetime import datetime, date, timedelta
import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트 경로 sys.path 추가
sys.path.append("c:/aivle202609/big_project")

from app.db.db import DATABASE_URL, Base
from app.models import (
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
    EducationStatus
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def auto_migrate():
    """DB 스키마 자동 동기화 (신규 테이블 생성 및 기존 테이블 신규/변경된 컬럼 ALTER)"""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        # 1. board.updated_at 컬럼 추가
        try:
            conn.execute(text("ALTER TABLE board ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;"))
            conn.commit()
            print("board 테이블에 updated_at 컬럼 추가 완료.")
        except Exception:
            pass

        # 2. education.due_date 컬럼 추가
        try:
            conn.execute(text("ALTER TABLE education ADD COLUMN due_date DATE NULL;"))
            conn.commit()
            print("education 테이블에 due_date 컬럼 추가 완료.")
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


def seed():
    # 0. 스키마 자동 동기화
    auto_migrate()

    db = SessionLocal()
    try:
        print("DB 시딩을 시작합니다...")

        # 1. 유저 계정 생성 (관리자 & 작업자 계정)
        users_data = [
            {
                "user_id": "admin",
                "name": "최고관리자",
                "password": hash_password("admin123"),
                "role": "안전 관리자",
                "company_code": "AIVLE_TEAM03"
            },
            {
                "user_id": "worker1",
                "name": "김작업",
                "password": hash_password("worker123"),
                "role": "일반 작업자",
                "company_code": "AIVLE_TEAM03"
            },
            {
                "user_id": "worker2",
                "name": "이신규",
                "password": hash_password("worker123"),
                "role": "신규 근로자",
                "company_code": "AIVLE_TEAM03"
            }
        ]

        users = []
        
        # 필수 기본 유저 3명
        base_users = [
            {"user_id": "admin", "name": "최고관리자", "password": hash_password("admin123"), "role": "안전 관리자", "company_code": "AIVLE_TEAM03"},
            {"user_id": "worker1", "name": "김작업", "password": hash_password("worker123"), "role": "일반 작업자", "company_code": "AIVLE_TEAM03"},
            {"user_id": "worker2", "name": "이신규", "password": hash_password("worker123"), "role": "신규 근로자", "company_code": "AIVLE_TEAM03"}
        ]
        
        # 더미 유저 27명 추가 생성 (총 30명)
        for i in range(3, 30):
            role_type = "일반 작업자" if i % 2 == 0 else "신규 근로자"
            base_users.append({
                "user_id": f"worker{i}",
                "name": f"작업자{i}",
                "password": hash_password("worker123"),
                "role": role_type,
                "company_code": "AIVLE_TEAM03"
            })

        for u_data in base_users:
            u = db.query(User).filter(User.user_id == u_data["user_id"]).first()
            if not u:
                u = User(**u_data)
                db.add(u)
                db.commit()
                db.refresh(u)
            users.append(u)

        admin_user = users[0]
        print(f"유저 계정 {len(users)}개 세팅 완료.")

        # 2. CCTV 등록
        cctvs_data = [
            {"cctv_name": "A동 복도 CCTV 1", "location": "A동 복도", "stream_url": "/static/streams/corridor_a1.mp4", "status": "정상"},
            {"cctv_name": "B동 자재창고 CCTV 2", "location": "B동 자재창고", "stream_url": "/static/streams/warehouse_b2.mp4", "status": "정상"},
            {"cctv_name": "C동 하역장 CCTV 3", "location": "C동 하역장", "stream_url": "/static/streams/loading_c3.mp4", "status": "정상"},
            {"cctv_name": "D동 정문 CCTV 4", "location": "D동 정문", "stream_url": "/static/streams/main_gate_d4.mp4", "status": "비정상"}
        ]
        
        cctvs = []
        for c_data in cctvs_data:
            existing_cctv = db.query(CCTV).filter(CCTV.cctv_name == c_data["cctv_name"]).first()
            if not existing_cctv:
                new_cctv = CCTV(**c_data)
                db.add(new_cctv)
                db.commit()
                db.refresh(new_cctv)
                cctvs.append(new_cctv)
            else:
                cctvs.append(existing_cctv)
        print(f"CCTV {len(cctvs)}대 세팅 완료.")

        # 3. 이벤트 카테고리 등록
        categories_data = [
            {"category": "위험", "category_name": "화재 감지"},
            {"category": "주의", "category_name": "불법 적치물 검지"},
            {"category": "경고", "category_name": "보호구 미착용"},
            {"category": "주의", "category_name": "무단 침입"}
        ]
        
        categories = []
        for cat_data in categories_data:
            existing_cat = db.query(EventCategory).filter(EventCategory.category_name == cat_data["category_name"]).first()
            if not existing_cat:
                new_cat = EventCategory(**cat_data)
                db.add(new_cat)
                db.commit()
                db.refresh(new_cat)
                categories.append(new_cat)
            else:
                categories.append(existing_cat)
        print(f"이벤트 카테고리 {len(categories)}종 세팅 완료.")

        # 4. 이상 감지 이벤트 및 조치 Checklist 적재
        existing_event_count = db.query(Event).count()
        if existing_event_count < 10:
            print("더미 이상 감지 이벤트 및 점검 Checklist 적재를 시작합니다...")
            now = datetime.utcnow()
            
            events = []
            for i in range(12):
                cctv = cctvs[i % len(cctvs)]
                category = categories[i % len(categories)]
                date_offset = timedelta(days=random_offset_days(i), hours=i*2)
                event_date = now - date_offset
                
                new_event = Event(
                    category_id=category.category_id,
                    camera_id=cctv.cctv_id,
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
                    event_id=ev.event_id,
                    date=ev.date + timedelta(hours=1),
                    status=status_val,
                    uid=admin_user.uid,
                    camera_id=ev.camera_id,
                    content=content,
                    image_url=img_url
                )
                db.add(chk)
                db.commit()
                db.refresh(chk)
                checklists.append(chk)
            print(f"체크리스트 조치 내역 {len(checklists)}건 세팅 완료.")
            
            # 5. 보고서(Report) 및 매핑 생성
            report1 = Report(
                uid=admin_user.uid,
                content="7월 2주차 사내 소방 안전 및 대피로 장애물 점검 주간 리포트입니다. B동 자재창고의 장애물이 빈번히 조치 대기 상태로 전이되어 부서별 안전 교육을 권장합니다.",
                summary="7월 2주차 사내 소방안전 주간 보고서",
                created_at=now - timedelta(days=2)
            )
            report2 = Report(
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
            
            map1 = ReportEventMap(report_id=report1.report_id, event_id=events[0].event_id)
            map2 = ReportEventMap(report_id=report1.report_id, event_id=events[1].event_id)
            map3 = ReportChecklistMap(report_id=report1.report_id, checklist_id=checklists[0].checklist_id)
            db.add_all([map1, map2, map3])
            db.commit()
            print("리포트-이벤트/체크리스트 연동 맵 테이블 적재 완료.")
        else:
            print("이상 감지 이벤트 및 점검 데이터가 이미 존재합니다.")

        # 6. 게시판(Board) 적재
        if db.query(Board).count() == 0:
            board1 = Board(
                uid=admin_user.uid,
                event_category_id=categories[1].category_id,
                title="B동 자재창고 통로 박스 적치 조치 요청",
                board_contents="B동 자재창고 비상구 통로 주변에 불법 가연성 적치물이 쌓여 있어 안전 조치를 요청합니다.",
                status="조치중",
                location="B동 자재창고",
                image_url="/static/uploads/board_sample_1.jpg"
            )
            board2 = Board(
                uid=users[1].uid,
                event_category_id=categories[0].category_id,
                title="A동 복도 소화기 배치 재점검 요청",
                board_contents="소화기 외관 점검 결과 일부 소화기 위치 이동 및 가압 점검이 필요합니다.",
                status="접수",
                location="A동 복도",
                image_url=None
            )
            db.add_all([board1, board2])
            db.commit()
            print("게시판 더미 데이터 2건 적재 완료.")
        else:
            print("게시판 데이터가 이미 존재합니다.")

        # 7. 안전 교육(Education) 및 수강 이수 현황(EducationStatus) 적재
        # 기존 교육 상태 데이터 초기화 (다시 채우기 위해)
        db.query(EducationStatus).delete()
        
        if db.query(Education).count() == 0:
            today = date.today()
            edu1 = Education(
                title="사업장 정기 소방 안전 필수 교육 2026",
                role="전체",
                video_url="https://youtube.com/watch?v=fire_safety_2026",
                category="소방안전",
                type="필수",
                due_date=today + timedelta(days=7)
            )
            edu2 = Education(
                title="비상구 및 대피로 유지관리 현장 실무 가이드",
                role="일반 작업자",
                video_url="https://youtube.com/watch?v=evacuation_guide",
                category="피난",
                type="정기",
                due_date=today + timedelta(days=14)
            )
            edu3 = Education(
                title="신규 근로자 맞춤형 산업안전 기본 수칙",
                role="신규 근로자",
                video_url="https://youtube.com/watch?v=ppe_rules",
                category="산업안전",
                type="필수",
                due_date=today + timedelta(days=3)
            )
            db.add_all([edu1, edu2, edu3])
            db.commit()

        edus = db.query(Education).all()
        today = date.today()

        if edus:
            statuses = []
            # 1번 교육: 30명 중 이수 18명, 진행중 8명, 미이수 4명
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

            # 2번 교육: 30명 중 이수 22명, 진행중 5명, 미이수 3명
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
        else:
            print("안전 교육 데이터가 이미 존재합니다.")

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
