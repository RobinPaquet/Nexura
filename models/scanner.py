from sqlalchemy import Column, String, Float, DateTime, Integer
from datetime import datetime, timezone
from models.watchlist import Base, engine


class ScannerAlert(Base):
    __tablename__ = "scanner_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    isin = Column(String, nullable=False)
    company = Column(String, nullable=False)
    type = Column(String, nullable=False)       # 'screener' | 'news'
    sentiment = Column(String, nullable=True)   # 'positive' | 'negative' | 'neutral'
    headline = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ScannerConfig(Base):
    __tablename__ = "scanner_config"

    id = Column(Integer, primary_key=True, default=1)
    esg_min = Column(Float, default=0.0)
    sectors_exclude = Column(String, default="")  # comma-separated
    countries = Column(String, default="")         # comma-separated, empty = all
    coverage_min = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def create_scanner_tables():
    Base.metadata.create_all(bind=engine)
