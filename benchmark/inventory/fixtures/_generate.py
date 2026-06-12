"""Gera a fixture sintética do cenário `inventory` (Gestão de Estoque).

Rodar: uv run --python 3.11 python benchmark/inventory/fixtures/_generate.py

Cria um CSV pequeno e determinístico no schema do Kaggle `car-sales-report` (cada linha é UMA
venda/saída) e grava `expected_metrics.json` com os agregados derivados do MESMO CSV — assim os
checks objetivos têm uma "verdade" reprodutível.

Convenção de custo determinística: custo unitário de cada venda importada = floor(0.8 * Price).
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from math import floor
from pathlib import Path

OUT_DIR = Path(__file__).parent / "car_sales_sample"
CSV_PATH = OUT_DIR / "car_sales.csv"
EXPECTED_PATH = Path(__file__).parent / "expected_metrics.json"

# Cabeçalho exatamente no schema do Kaggle car-sales-report.
HEADER = [
    "Car_id", "Date", "Customer Name", "Gender", "Annual Income", "Dealer_Name",
    "Company", "Model", "Engine", "Transmission", "Color", "Price ($)", "Dealer_No",
    "Body Style", "Phone", "Dealer_Region",
]

# Vendas sintéticas com acentos/edge propositais e várias Company/Model/Region.
# Campos: Date, Customer Name, Gender, Annual Income, Dealer_Name, Company, Model,
#         Engine, Transmission, Color, Price, Dealer_No, Body Style, Phone, Dealer_Region
ROWS = [
    ["1/2/2022", "José Antônio", "Male", "13500", "Buddy Storbeck's", "Ford", "Fiesta",
     "DoubleÂ Overhead Camshaft", "Auto", "Black", "26000", "06457-3834", "Hatchback",
     "8264678", "São Paulo"],
    ["1/2/2022", "Maria Conceição", "Female", "1480000", "C & M Motors Inc", "Ford", "Fiesta",
     "DoubleÂ Overhead Camshaft", "Manual", "Red", "19000", "60504-7114", "Hatchback",
     "6848189", "São Paulo"],
    ["1/3/2022", "João da Silva", "Male", "1035000", "Capitol KIA", "Chevrolet", "Onix",
     "Overhead Camshaft", "Auto", "Pale White", "31000", "38701-8047", "Sedan",
     "7298798", "Rio de Janeiro"],
    ["1/4/2022", "Ana Paula", "Female", "13500", "Chrysler of Tri-Cities", "Chevrolet", "Onix",
     "Overhead Camshaft", "Manual", "Red", "24000", "99301-3882", "Sedan",
     "6257557", "Rio de Janeiro"],
    ["1/5/2022", "Carlos Eduardo", "Male", "1465000", "Chrysler Plymouth", "Toyota", "Corolla",
     "DoubleÂ Overhead Camshaft", "Auto", "Pale White", "42000", "53546-9427", "Sedan",
     "7081483", "Curitiba"],
    ["1/6/2022", "Beatriz Lação", "Female", "850000", "Classic Chevy", "Toyota", "Corolla",
     "DoubleÂ Overhead Camshaft", "Auto", "Black", "38000", "78758-7841", "Sedan",
     "5512888", "Curitiba"],
    ["1/7/2022", "Rafael Gonçalves", "Male", "1500000", "Diehl Motor Co Inc", "Toyota", "Hilux",
     "Overhead Camshaft", "Manual", "Red", "55000", "85257-3102", "Pickup",
     "8009802", "Belo Horizonte"],
    ["1/8/2022", "Fernanda Müller", "Female", "1200000", "Bill Page Toyota", "Volkswagen", "Gol",
     "Overhead Camshaft", "Manual", "Pale White", "21000", "60504-1234", "Hatchback",
     "1234567", "Belo Horizonte"],
    ["1/9/2022", "Lucas Almeida", "Male", "780000", "Buddy Storbeck's", "Volkswagen", "Gol",
     "Overhead Camshaft", "Auto", "Black", "23500", "06457-3834", "Hatchback",
     "8264111", "São Paulo"],
    ["1/10/2022", "Patrícia Nóbrega", "Female", "1650000", "C & M Motors Inc", "Volkswagen",
     "T-Cross", "DoubleÂ Overhead Camshaft", "Auto", "Red", "47000", "60504-7114", "SUV",
     "6848222", "Rio de Janeiro"],
    ["1/11/2022", "Thiago Ávila", "Male", "920000", "Capitol KIA", "Honda", "Civic",
     "DoubleÂ Overhead Camshaft", "Manual", "Pale White", "36000", "38701-8047", "Sedan",
     "7298444", "Curitiba"],
    ["1/12/2022", "Juliana Rezende", "Female", "1340000", "Classic Chevy", "Honda", "Civic",
     "DoubleÂ Overhead Camshaft", "Auto", "Black", "39000", "78758-7841", "Sedan",
     "5512333", "Belo Horizonte"],
    ["1/13/2022", "Marcelo Fróes", "Male", "610000", "Diehl Motor Co Inc", "Honda", "Fit",
     "Overhead Camshaft", "Manual", "Red", "28000", "85257-3102", "Hatchback",
     "8009111", "São Paulo"],
    ["1/14/2022", "Camila Sá", "Female", "1750000", "Bill Page Toyota", "Ford", "Ranger",
     "Overhead Camshaft", "Auto", "Pale White", "62000", "60504-1234", "Pickup",
     "1234999", "Rio de Janeiro"],
]


def _to_csv_rows() -> list[list[str]]:
    rows = []
    for i, r in enumerate(ROWS, start=1):
        car_id = f"C_CND_{i:03d}"
        # r = [Date, Customer, Gender, Income, Dealer, Company, Model, Engine, Trans, Color,
        #      Price, DealerNo, BodyStyle, Phone, Region]
        rows.append([car_id, *r])
    return rows


def _compute_expected(rows: list[list[str]]) -> dict:
    revenue = 0
    cost = 0
    units_sold = 0
    by_company: dict[str, int] = defaultdict(int)
    by_region: dict[str, int] = defaultdict(int)
    products: set[tuple[str, str]] = set()

    col = {name: idx for idx, name in enumerate(HEADER)}
    for r in rows:
        price = int(float(r[col["Price ($)"]]))
        company = r[col["Company"]]
        model = r[col["Model"]]
        region = r[col["Dealer_Region"]]
        revenue += price
        cost += floor(0.8 * price)
        units_sold += 1
        by_company[company] += price
        by_region[region] += price
        products.add((company, model))

    return {
        "revenue": revenue,
        "cost": cost,
        "profit": revenue - cost,
        "units_sold": units_sold,
        "movements": units_sold,
        "by_company": dict(by_company),
        "by_region": dict(by_region),
        "products_count": len(products),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = _to_csv_rows()
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)

    expected = _compute_expected(rows)
    EXPECTED_PATH.write_text(
        json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"CSV gerado em {CSV_PATH} ({len(rows)} vendas)")
    print(f"expected_metrics.json gerado em {EXPECTED_PATH}")
    print(json.dumps(expected, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
