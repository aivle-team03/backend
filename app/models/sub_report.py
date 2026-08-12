from sqlalchemy import Column, BigInteger, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.db import Base


class SubReport(Base):
    __tablename__ = "sub_report"

    sub_report_id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_id = Column(BigInteger, ForeignKey("company.company_id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, nullable=False)
    path = Column(Text, nullable=False)

    company = relationship("Company")
