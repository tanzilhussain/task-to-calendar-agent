from __future__ import annotations
from sqlalchemy import create_engine, Column, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    page_id = Column(String, primary_key=True)
    title = Column(String)
    due = Column(String)
    planned = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Event(Base):
    __tablename__ = "events"
    event_id = Column(String, primary_key=True)
    page_id = Column(String, index=True)
    start = Column(DateTime)
    end = Column(DateTime)

def make_session(url: str = "sqlite:///app.db"):
    engine = create_engine(url, echo=False, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()
