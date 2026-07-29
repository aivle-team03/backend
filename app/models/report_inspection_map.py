from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base


class ReportInspectionMap(Base):
    __tablename__ = "report_inspection_map"

    report_id = Column(
        BigInteger,
        ForeignKey("report.report_id", ondelete="CASCADE"),
        primary_key=True,
    )
    inspection_history_id = Column(
        BigInteger,
        ForeignKey(
            "inspection_history.inspection_history_id", ondelete="CASCADE"
        ),
        primary_key=True,
    )

    # N:M 관계 연결 (back_populates)
    report = relationship("Report", back_populates="inspection_maps")
    inspection_history = relationship(
        "InspectionHistory", back_populates="report_maps"
    )