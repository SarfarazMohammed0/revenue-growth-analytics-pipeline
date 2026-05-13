"""
Generates synthetic payment transactions for revenue KPIs.
Output: data/raw_payments.csv
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)

PLAN_PRICES = {"Pro": 19.0, "Business": 49.0, "Enterprise": 199.0}
STATUSES = ["succeeded", "failed", "refunded"]
STATUS_WEIGHTS = [0.92, 0.05, 0.03]
CURRENCIES = ["USD", "EUR", "GBP", "INR", "JPY"]
CURRENCY_WEIGHTS = [0.60, 0.15, 0.10, 0.10, 0.05]

def load_paying_customers(path: Path):
    paying = []
    with open(path) as f:
        for r in csv.DictReader(f):
            if r["segment"] in PLAN_PRICES:
                paying.append((r["customer_id"], r["segment"]))
    return paying

def gen_payments(paying, n: int = 40_000, seed: int = 11):
    random.seed(seed)
    start = datetime(2025, 1, 1)
    end = datetime(2026, 5, 1)
    span = (end - start).total_seconds()
    rows = []
    for i in range(1, n + 1):
        cid, plan = random.choice(paying)
        ts = start + timedelta(seconds=random.random() * span)
        base_price = PLAN_PRICES[plan]
        # add yearly plan jitter
        amount = base_price * random.choice([1, 1, 1, 12])
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
        rows.append({
            "payment_id": f"PAY{i:09d}",
            "customer_id": cid,
            "payment_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": round(amount, 2),
            "currency": random.choices(CURRENCIES, weights=CURRENCY_WEIGHTS)[0],
            "status": status,
            "plan": plan,
        })
    return rows

def main():
    base = Path(__file__).resolve().parents[1] / "data"
    paying = load_paying_customers(base / "raw_crm_customers.csv")
    rows = gen_payments(paying)
    path = base / "raw_payments.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows):,} payments -> {path}")

if __name__ == "__main__":
    main()
