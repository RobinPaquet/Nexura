import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

def test_scanner_alert_model_has_required_fields():
    from models.scanner import ScannerAlert
    cols = {c.name for c in ScannerAlert.__table__.columns}
    assert {"id", "isin", "company", "type", "sentiment", "headline", "source_url", "score", "created_at"} <= cols

def test_scanner_config_model_has_required_fields():
    from models.scanner import ScannerConfig
    cols = {c.name for c in ScannerConfig.__table__.columns}
    assert {"id", "esg_min", "sectors_exclude", "countries", "coverage_min", "updated_at"} <= cols

def test_create_scanner_tables_runs_without_error():
    from models.scanner import create_scanner_tables
    create_scanner_tables()  # must not raise
