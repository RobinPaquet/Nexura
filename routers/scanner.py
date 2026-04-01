from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone

from models.watchlist import get_db
from models.scanner import ScannerAlert, ScannerConfig

router = APIRouter(prefix="/scanner", tags=["scanner"])


class ConfigRequest(BaseModel):
    esg_min: float = 0.0
    sectors_exclude: list[str] = []
    countries: list[str] = []
    coverage_min: float = 0.0


@router.get("/alerts")
def get_alerts(limit: int = 50, db: Session = Depends(get_db)):
    alerts = (
        db.query(ScannerAlert)
        .order_by(ScannerAlert.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "alerts": [
            {
                "id": a.id,
                "isin": a.isin,
                "company": a.company,
                "type": a.type,
                "sentiment": a.sentiment,
                "headline": a.headline,
                "source_url": a.source_url,
                "score": a.score,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ],
        "count": len(alerts),
    }


@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    config = db.query(ScannerConfig).filter(ScannerConfig.id == 1).first()
    if not config:
        return {
            "esg_min": 0.0,
            "sectors_exclude": [],
            "countries": [],
            "coverage_min": 0.0,
        }
    return {
        "esg_min": config.esg_min,
        "sectors_exclude": [s for s in config.sectors_exclude.split(",") if s],
        "countries": [c for c in config.countries.split(",") if c],
        "coverage_min": config.coverage_min,
    }


@router.post("/config")
def save_config(req: ConfigRequest, db: Session = Depends(get_db)):
    config = db.query(ScannerConfig).filter(ScannerConfig.id == 1).first()
    if config:
        config.esg_min = req.esg_min
        config.sectors_exclude = ",".join(req.sectors_exclude)
        config.countries = ",".join(req.countries)
        config.coverage_min = req.coverage_min
        config.updated_at = datetime.now(timezone.utc)
    else:
        config = ScannerConfig(
            id=1,
            esg_min=req.esg_min,
            sectors_exclude=",".join(req.sectors_exclude),
            countries=",".join(req.countries),
            coverage_min=req.coverage_min,
        )
        db.add(config)
    db.commit()
    return {"status": "saved"}
