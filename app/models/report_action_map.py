from sqlalchemy import BigInteger, Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.db import Base


class ReportActionMap(Base):
    __tablename__ = "report_action_map"
    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "action_history_id",
            name="uq_report_action_map_report_action",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    report_id = Column(
        BigInteger,
        ForeignKey("report.report_id", ondelete="CASCADE"),
        nullable=False,
    )
    action_history_id = Column(
        BigInteger,
        ForeignKey("action_history.action_history_id", ondelete="CASCADE"),
        nullable=False,
    )

    report = relationship("Report", back_populates="action_maps")
    action_history = relationship("ActionHistory", back_populates="report_maps")
