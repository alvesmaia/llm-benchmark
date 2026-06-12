"""Fixtures de teste: banco temporário + CSV de vendas mínimo."""

from __future__ import annotations

import csv
import os

import pytest

HEADER = [
    "Car_id", "Date", "Customer Name", "Gender", "Annual Income", "Dealer_Name",
    "Company", "Model", "Engine", "Transmission", "Color", "Price ($)", "Dealer_No",
    "Body Style", "Phone", "Dealer_Region",
]

ROWS = [
    ["C_001", "1/2/2022", "José", "Male", "13500", "Dealer A", "Ford", "Fiesta",
     "OHC", "Auto", "Black", "26000", "06457", "Hatchback", "8264678", "São Paulo"],
    ["C_002", "1/3/2022", "Maria", "Female", "1480000", "Dealer B", "Ford", "Fiesta",
     "OHC", "Manual", "Red", "19000", "60504", "Hatchback", "6848189", "São Paulo"],
    ["C_003", "1/4/2022", "João", "Male", "1035000", "Dealer C", "Toyota", "Corolla",
     "OHC", "Auto", "White", "42000", "38701", "Sedan", "7298798", "Curitiba"],
]


def _write_csv(path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(ROWS)


@pytest.fixture()
def env_db(tmp_path, monkeypatch):
    csv_path = tmp_path / "car_sales.csv"
    _write_csv(csv_path)
    db_path = tmp_path / "inventory.db"
    monkeypatch.setenv("DATASET_PATH", str(csv_path))
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    os.environ["DATASET_PATH"] = str(csv_path)
    os.environ["DB_PATH"] = str(db_path)
    os.environ["ADMIN_USER"] = "admin"
    os.environ["ADMIN_PASSWORD"] = "admin123"
    return {"csv": csv_path, "db": db_path}
