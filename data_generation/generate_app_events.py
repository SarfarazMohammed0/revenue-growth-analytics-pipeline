"""
Generates synthetic app event logs (DAU, feature usage, funnel events).
Output: data/raw_app_events.csv

Funnel modeled: page_view -> sign_up_started -> sign_up_completed
              -> activated -> upgraded
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)

EVENT_TYPES = [
    ("page_view", 0.40),
    ("feature_used", 0.25),
    ("sign_up_started", 0.10),
    ("sign_up_completed", 0.08),
    ("activated", 0.10),
    ("upgraded", 0.04),
    ("churned", 0.03),
]
PLATFORMS = ["web", "ios", "android"]
PLATFORM_WEIGHTS = [0.55, 0.25, 0.20]

def load_customers(path: Path):
    with open(path) as f:
        return [r["customer_id"] for r in csv.DictReader(f)]

def gen_events(customer_ids, n: int = 150_000, seed: int = 7):
    random.seed(seed)
    events, weights = zip(*EVENT_TYPES)
    start = datetime(2025, 1, 1)
    end = datetime(2026, 5, 1)
    span = (end - start).total_seconds()

    rows = []
    for i in range(1, n + 1):
        cid = random.choice(customer_ids)
        ts = start + timedelta(seconds=random.random() * span)
        rows.append({
            "event_id": f"E{i:09d}",
            "customer_id": cid,
            "event_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": random.choices(events, weights=weights)[0],
            "platform": random.choices(PLATFORMS, weights=PLATFORM_WEIGHTS)[0],
            "session_id": f"S{random.randint(1, 200_000):08d}",
        })
    return rows

def main():
    base = Path(__file__).resolve().parents[1] / "data"
    customers = load_customers(base / "raw_crm_customers.csv")
    rows = gen_events(customers)
    path = base / "raw_app_events.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows):,} events -> {path}")

if __name__ == "__main__":
    main()
