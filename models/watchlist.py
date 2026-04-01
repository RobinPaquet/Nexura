from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime, timezone
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./weefin.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

class WatchlistItem(Base):
    __tablename__ = "watchlist"
    isin = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=True)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
