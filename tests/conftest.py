# tests/conftest.py
import os
import pytest

@pytest.fixture(autouse=True)
def set_esg_data_path(monkeypatch):
    monkeypatch.setenv(
        "ESG_DATA_PATH",
        "/Users/robin/Desktop/Weefinnn/weefin-esg-search/Dossier_Weefin_Cours_M1/weefin-esg-search 2/public/companies.json"
    )
