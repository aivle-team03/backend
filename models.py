from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "User"

    uid = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(50), nullable=True)
    password = Column(String(1000), nullable=False)
    refresh_token = Column(String(255))
    role = Column(String(50), nullable=False, default="user")
    company_code = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CCTV(Base):
    __tablename__ = "CCTV"

    camera_id = Column(BigInteger, primary_key=True, index=True)
    camera_name = Column(String(50), nullable=False)
    location = Column(String(255))
    stream_url = Column(String(255))
    status = Column(String(50), nullable=False, default="active")

class EventCategory(Base):
    __tablename__ = "EventCategory"

    category_id = Column(BigInteger, primary_key=True, index=True)
    category_name = Column(String(50), nullable=False)
    category = Column(String(100))

class Event(Base):
    __tablename__ = "Event"

    event_id = Column(BigInteger, primary_key=True, index=True)
    camera_id = Column(BigInteger, ForeignKey("CCTV.camera_id"), nullable=False)
    category_id = Column(BigInteger, ForeignKey("EventCategory.category_id"), nullable=False)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    image_url = Column(String(255))

    camera = relationship("CCTV", backref="events")
    category = relationship("EventCategory", backref="events")


class Checklist(Base):
    __tablename__ = "Checklist"

    checklist_id = Column(BigInteger, primary_key=True, index=True)
    event_id = Column(BigInteger, ForeignKey("Event.event_id"), nullable=False)
    date = Column(Date, default=datetime.date.today)
    status = Column(String(50), nullable=False)
    uid = Column(BigInteger, ForeignKey("User.uid"))
    camera_id = Column(BigInteger, ForeignKey("CCTV.camera_id"))
    content = Column(String(255))
    image_url = Column(String(255))

    camera = relationship("CCTV", backref="checklists")
    user = relationship("User", backref="checklists")
    event = relationship("Event", backref="checklists")

class Report(Base):
    __tablename__ = "Report"

    report_id = Column(BigInteger, primary_key=True, index=True)
    uid = Column(BigInteger, ForeignKey("User.uid"), nullable=False)
    content = Column(String(1000))
    summary = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", backref="reports")

class ReportEventMapping(Base):
    __tablename__ = "ReportEventMapping"

    mapping_id = Column(BigInteger, primary_key=True, index=True)
    report_id = Column(BigInteger, ForeignKey("Report.report_id"), nullable=False)
    event_id = Column(BigInteger, ForeignKey("Event.event_id"), nullable=False)

    report = relationship("Report", backref="report_event_mappings")
    event = relationship("Event", backref="report_event_mappings")

class ReportChecklistMapping(Base):
    __tablename__ = "ReportChecklistMapping"

    mapping_id = Column(BigInteger, primary_key=True, index=True)
    report_id = Column(BigInteger, ForeignKey("Report.report_id"), nullable=False)
    checklist_id = Column(BigInteger, ForeignKey("Checklist.checklist_id"), nullable=False)

    report = relationship("Report", backref="report_checklist_mappings")
    checklist = relationship("Checklist", backref="report_checklist_mappings")