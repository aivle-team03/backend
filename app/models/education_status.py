from sqlalchemy import BigInteger, CheckConstraint, Column, Date, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.db import Base


class EducationStatus(Base):
    __tablename__ = "education_status"
    __table_args__ = (
        CheckConstraint(
            "status IN ('미이수', '진행중', '이수')",
            name="ck_education_status_status",
        ),
    )

    uid = Column(
        BigInteger,
        ForeignKey("user.uid", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    education_id = Column(
        BigInteger,
        ForeignKey("education.education_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    status = Column(
        String(20),
        nullable=False,
        default="미이수",
        server_default="미이수",
    )
    completed_date = Column(Date, nullable=True)

    user = relationship("User", backref="education_statuses")
    education = relationship("Education", back_populates="statuses")
