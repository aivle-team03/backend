from sqlalchemy import Column, BigInteger, String, DateTime, func
from sqlalchemy.orm import relationship
from app.db.db import Base

class Company(Base):
    __tablename__ = "company"

    company_id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())

    signup_codes = relationship("SignupCode", back_populates="company", cascade="all, delete-orphan")
    users = relationship("User", back_populates="company")