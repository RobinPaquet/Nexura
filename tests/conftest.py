# tests/conftest.py
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest

@pytest.fixture(autouse=True)
def set_esg_data_path(monkeypatch):
    monkeypatch.setenv(
        "ESG_DATA_PATH",
        "/Users/robin/Desktop/Weefinnn/weefin-esg-search/Dossier_Weefin_Cours_M1/weefin-esg-search 2/public/companies.json"
    )

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)
