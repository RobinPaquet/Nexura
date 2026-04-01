from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from models.watchlist import WatchlistItem, get_db, create_tables

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

create_tables()

class AddRequest(BaseModel):
    isin: str
    name: str
    ticker: Optional[str] = None

@router.get("")
def get_watchlist(db: Session = Depends(get_db)):
    items = db.query(WatchlistItem).order_by(WatchlistItem.added_at.desc()).all()
    return [{"isin": i.isin, "name": i.name, "ticker": i.ticker, "added_at": i.added_at.isoformat() if i.added_at else None} for i in items]

@router.post("", status_code=201)
def add_to_watchlist(req: AddRequest, db: Session = Depends(get_db)):
    existing = db.query(WatchlistItem).filter(WatchlistItem.isin == req.isin).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"{req.isin} already in watchlist")
    item = WatchlistItem(isin=req.isin, name=req.name, ticker=req.ticker)
    db.add(item)
    db.commit()
    return {"status": "added", "isin": req.isin}

@router.delete("/{isin}", status_code=200)
def remove_from_watchlist(isin: str, db: Session = Depends(get_db)):
    item = db.query(WatchlistItem).filter(WatchlistItem.isin == isin).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"{isin} not in watchlist")
    db.delete(item)
    db.commit()
    return {"status": "removed", "isin": isin}
