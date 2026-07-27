from sqlalchemy import Column, BigInteger, String, DateTime, func
from sqlalchemy.orm import relationship
from app.db.db import Base

class Company(Base):
    __tablename__ = "companies"

    company_id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_name = Column(String(100), nullable=False)
    company_code = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())

    users = relationship("User", back_populates="company")