from models.watchlist import SessionLocal, WatchlistItem
from models.scanner import ScannerAlert, ScannerConfig
from data.esg_loader import get_company_by_isin


def run_screener():
    db = SessionLocal()
    try:
        config = db.query(ScannerConfig).filter(ScannerConfig.id == 1).first()
        esg_min = config.esg_min if config else 0.0
        sectors_exclude = (
            [s.strip().lower() for s in config.sectors_exclude.split(",") if s.strip()]
            if config else []
        )
        coverage_min = config.coverage_min if config else 0.0

        watchlist = db.query(WatchlistItem).all()

        for item in watchlist:
            company = get_company_by_isin(item.isin)
            if not company:
                continue

            alert_messages = _check_company(company, esg_min, sectors_exclude, coverage_min)
            for msg in alert_messages:
                existing = (
                    db.query(ScannerAlert)
                    .filter(
                        ScannerAlert.isin == item.isin,
                        ScannerAlert.type == "screener",
                        ScannerAlert.headline == msg,
                    )
                    .order_by(ScannerAlert.created_at.desc())
                    .first()
                )
                if not existing:
                    db.add(ScannerAlert(
                        isin=item.isin,
                        company=item.name,
                        type="screener",
                        headline=msg,
                        sentiment="negative",
                        score=None,
                        source_url=None,
                    ))

        db.commit()
    finally:
        db.close()


def _check_company(company: dict, esg_min: float, sectors_exclude: list, coverage_min: float) -> list[str]:
    alerts = []

    score = company.get("totalScore") or company.get("score") or 0
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0

    if score < esg_min:
        alerts.append(f"ESG score {score:.1f} below minimum {esg_min:.1f}")

    sector = str(company.get("sector") or company.get("industry") or "").lower()
    for excl in sectors_exclude:
        if excl in sector:
            alerts.append(f"Sector '{sector}' matches exclusion '{excl}'")
            break

    return alerts
