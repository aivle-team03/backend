from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.db.db import Base

class Notification(Base):
    __tablename__ = "notification"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, index=True, nullable=False) # 같은 사업장 필터링용
    user_id = Column(Integer, nullable=True) # 특정인 대상 알림일 경우 (None이면 전체/관리자 알림)
    
    category = Column(String(50), nullable=False) # 'schedule', 'danger', 'complete' (아이콘 매핑용)
    title = Column(String(100), nullable=False)    # '점검 일정 등록', '위험 신고 접수', '조치 완료'
    message = Column(Text, nullable=False)        # '2구역 방화문 개방 항목의 조치가 완료되었습니다.'
    path = Column(String(200), nullable=True)     # 클릭 시 이동할 URL (e.g. '/actions', '/board')
    is_read = Column(Boolean, default=False)      # 읽음 여부
    created_at = Column(DateTime(timezone=True), server_default=func.now())