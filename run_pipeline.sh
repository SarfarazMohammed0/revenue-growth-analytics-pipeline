#!/usr/bin/env bash
# Run the full pipeline end-to-end locally with DuckDB.
# This is what recruiters can clone-and-run in 60 seconds.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "==> 1. Generating synthetic source data..."
python data_generation/generate_crm_data.py
python data_generation/generate_app_events.py
python data_generation/generate_payments.py

echo "==> 2. Seeding raw tables into DuckDB..."
python - <<'PY'
import duckdb
from pathlib import Path
data = Path("data")
con = duckdb.connect(str(data / "warehouse.duckdb"))
for name in ["raw_crm_customers", "raw_app_events", "raw_payments"]:
    con.execute(f"create or replace table main.{name} as "
                f"select * from read_csv_auto('{data}/{name}.csv')")
    n = con.execute(f"select count(*) from main.{name}").fetchone()[0]
    print(f"   loaded {name}: {n:,} rows")
con.close()
PY

echo "==> 3. Running dbt transformations..."
cd dbt_project
dbt deps --quiet
dbt run --profiles-dir .
dbt test --profiles-dir .
cd ..

echo "==> 4. Launching dashboard..."
echo "    streamlit run dashboard/app.py"
echo ""
echo "✅ Pipeline complete. Open the dashboard URL Streamlit prints."
