import sys
import os
from datetime import datetime, timedelta
import bcrypt

# 프로젝트 루트 경로 sys.path 추가
sys.path.append("c:/aivle202609/big_project")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.db import DATABASE_URL
from app.models.user import User
from app.models.cctv import CCTV
from app.models.event_category import EventCategory
from app.models.event import Event
from app.models.checklist import Checklist
from app.models.report import Report
from app.models.report_event_map import ReportEventMap
from app.models.report_checklist_map import ReportChecklistMap

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def seed():
    db = SessionLocal()
    try:
        print("DB 시딩을 시작합니다...")

        # 1. 관리자 유저 생성
        admin_user = db.query(User).filter(User.user_id == "admin").first()
        if not admin_user:
            admin_user = User(
                user_id="admin",
                name="최고관리자",
                password=hash_password("admin123"),
                role="admin",
                company_code="AIVLE_TEAM03"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print("관리자 계정 생성 완료 (ID: admin / PW: admin123)")
        else:
            print("관리자 계정이 이미 존재합니다.")

        # 2. CCTV 등록
        cctvs_data = [
            {"camera_name": "A동 복도 CCTV 1", "location": "A동 복도", "stream_url": "/static/streams/corridor_a1.mp4", "status": "정상"},
            {"camera_name": "B동 자재창고 CCTV 2", "location": "B동 자재창고", "stream_url": "/static/streams/warehouse_b2.mp4", "status": "정상"},
            {"camera_name": "C동 하역장 CCTV 3", "location": "C동 하역장", "stream_url": "/static/streams/loading_c3.mp4", "status": "정상"},
            {"camera_name": "D동 정문 CCTV 4", "location": "D동 정문", "stream_url": "/static/streams/main_gate_d4.mp4", "status": "비정상"}
        ]
        
        cctvs = []
        for c_data in cctvs_data:
            existing_cctv = db.query(CCTV).filter(CCTV.camera_name == c_data["camera_name"]).first()
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
            
            # 30일 전부터 오늘까지 골고루 분포된 임의의 날짜에 이벤트 12건 생성
            events = []
            for i in range(12):
                cctv = cctvs[i % len(cctvs)]
                category = categories[i % len(categories)]
                date_offset = timedelta(days=random_offset_days(i), hours=i*2)
                event_date = now - date_offset
                
                new_event = Event(
                    category_id=category.category_id,
                    camera_id=cctv.camera_id,
                    date=event_date,
                    image_url=f"/static/uploads/dummy_event_{i+1}.jpg"
                )
                db.add(new_event)
                db.commit()
                db.refresh(new_event)
                events.append(new_event)
                
            print(f"이상 감지 이벤트 {len(events)}건 적재 완료.")
            
            # Checklist 생성 (10건)
            # 3건: 조치 대기
            # 3건: 조치 중
            # 2건: 승인 대기 (작업자가 보고한 상태)
            # 2건: 승인 완료 (최종 해결 상태)
            # 2건은 Checklist를 만들지 않아 자동으로 "미조치" 상태가 됨
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
            for idx, (status, content) in enumerate(status_list):
                ev = events[idx]
                img_url = f"/static/uploads/action_resolved_{idx+1}.jpg" if status in ["승인 대기", "승인 완료"] else None
                
                chk = Checklist(
                    event_id=ev.event_id,
                    date=ev.date + timedelta(hours=1),
                    status=status,
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
            
            # 5. 보고서(Report) 생성
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
            
            # 리포트 맵핑 적재
            map1 = ReportEventMap(report_id=report1.report_id, event_id=events[0].event_id)
            map2 = ReportEventMap(report_id=report1.report_id, event_id=events[1].event_id)
            map3 = ReportChecklistMap(report_id=report1.report_id, checklist_id=checklists[0].checklist_id)
            db.add_all([map1, map2, map3])
            db.commit()
            print("리포트-이벤트/체크리스트 연동 맵 테이블 적재 완료.")
            
        else:
            print("이미 데이터베이스에 더미 데이터가 충분히 적재되어 있습니다. 데이터 적재 단계를 생략합니다.")
            
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
