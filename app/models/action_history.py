from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.db import Base


class ActionHistory(Base):
    __tablename__ = "action_history"
    __table_args__ = (
        CheckConstraint(
            "type IN ('게시판', '이벤트', '점검이력', '직접추가')",
            name="ck_action_history_type",
        ),
        CheckConstraint(
            """
            (
                type = '게시판'
                AND board_id IS NOT NULL
                AND event_id IS NULL
                AND inspection_history_id IS NULL
            )
            OR (
                type = '이벤트'
                AND board_id IS NULL
                AND event_id IS NOT NULL
                AND inspection_history_id IS NULL
            )
            OR (
                type = '점검이력'
                AND board_id IS NULL
                AND event_id IS NULL
                AND inspection_history_id IS NOT NULL
            )
            OR (
                type = '직접추가'
                AND board_id IS NULL
                AND event_id IS NULL
                AND inspection_history_id IS NULL
            )
            """,
            name="ck_action_history_source",
        ),
        CheckConstraint(
            "action_status IN ('조치 대기', '조치 완료')",
            name="ck_action_history_action_status",
        ),
        CheckConstraint(
            """
            approval_status IS NULL
            OR approval_status IN ('승인 대기', '승인 완료', '반려')
            """,
            name="ck_action_history_approval_status",
        ),
        CheckConstraint(
            """
            (
                action_status = '조치 대기'
                AND (approval_status IS NULL OR approval_status = '반려')
            )
            OR (
                action_status = '조치 완료'
                AND approval_status IN ('승인 대기', '승인 완료')
            )
            """,
            name="ck_action_history_status_flow",
        ),
        CheckConstraint(
            """
            (
                action_status = '조치 대기'
                AND completed_at IS NULL
            )
            OR (
                action_status = '조치 완료'
                AND completed_at IS NOT NULL
            )
            """,
            name="ck_action_history_completed_at",
        ),
        CheckConstraint(
            """
            approval_status IS NULL
            OR approval_status != '반려'
            OR rejection_reason IS NOT NULL
            """,
            name="ck_action_history_rejection",
        ),
        CheckConstraint(
            """
            (
                approval_status IS NULL
                AND approver_uid IS NULL
                AND approval_date IS NULL
            )
            OR (
                approval_status = '승인 대기'
                AND approver_uid IS NULL
                AND approval_date IS NULL
            )
            OR (
                approval_status IN ('승인 완료', '반려')
                AND (approver_uid IS NOT NULL OR approver_name IS NOT NULL)
                AND approval_date IS NOT NULL
            )
            """,
            name="ck_action_history_approver",
        ),
        CheckConstraint(
            """
            action_status != '조치 완료' 
            OR handler_uid IS NOT NULL 
            OR handler_name IS NOT NULL
            """,
            name="ck_action_history_handler",
        ),
        Index(
            "ix_action_history_company_created",
            "company_id",
            "created_at",
        ),
        Index(
            "ix_action_history_company_status",
            "company_id",
            "action_status",
            "approval_status",
        ),
        Index(
            "ix_action_history_handler_status",
            "handler_uid",
            "action_status",
        ),
    )

    action_history_id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_id = Column(
        BigInteger,
        ForeignKey("company.company_id"),
        nullable=False,
    )
    board_id = Column(
        BigInteger,
        ForeignKey("board.board_id"),
        nullable=True,
    )
    event_id = Column(
        BigInteger,
        ForeignKey("event.event_id"),
        nullable=True,
    )
    inspection_history_id = Column(
        BigInteger,
        ForeignKey("inspection_history.inspection_history_id"),
        nullable=True,
    )
    category_id = Column(
        BigInteger,
        ForeignKey("event_category.category_id"),
        nullable=False,
    )
    handler_uid = Column(
        BigInteger,
        ForeignKey("user.uid", ondelete='SET NULL'),
        nullable=True,
    )
    handler_name = Column(String(100), nullable=True)
    approver_uid = Column(
        BigInteger,
        ForeignKey("user.uid", ondelete='SET NULL'),
        nullable=True,
    )
    approver_name = Column(String(100), nullable=True)
    action_name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)
    location = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    completed_at = Column(DateTime, nullable=True)
    action_status = Column(
        String(50),
        nullable=False,
        default="조치 대기",
        server_default="조치 대기",
    )
    image_url = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    approval_status = Column(String(50), nullable=True)
    approval_date = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    company = relationship("Company")
    board = relationship("Board")
    event = relationship("Event")
    inspection_history = relationship("InspectionHistory")
    category = relationship("EventCategory")
    handler = relationship("User", foreign_keys=[handler_uid])
    approver = relationship("User", foreign_keys=[approver_uid])
    report_maps = relationship(
        "ReportActionMap",
        back_populates="action_history",
        cascade="all, delete-orphan",
    )
