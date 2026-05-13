"""
Generates synthetic CRM customer data simulating a B2C SaaS source system.
Output: data/raw_crm_customers.csv
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)

SEGMENTS = ["Free", "Pro", "Business", "Enterprise"]
SEGMENT_WEIGHTS = [0.55, 0.25, 0.15, 0.05]
COUNTRIES = ["US", "GB", "IN", "DE", "BR", "JP", "CA", "AU", "FR", "NG"]
CHANNELS = ["organic", "paid_search", "paid_social", "referral", "direct", "email"]

FIRST = ["Alex","Maya","Jordan","Sam","Priya","Liam","Aisha","Noah","Wei","Sofia",
         "Kai","Rohan","Emma","Diego","Yara","Marcus","Lena","Omar","Ines","Theo"]
LAST = ["Chen","Patel","Kim","Garcia","Singh","Johnson","Nakamura","Silva","Diallo",
        "Schmidt","O'Brien","Ahmed","Rossi","Park","Hassan","Lopez","Andersen","Khan"]

def gen_customers(n: int = 5000, seed: int = 42):
    random.seed(seed)
    start = datetime(2024, 1, 1)
    rows = []
    for cid in range(1, n + 1):
        signup = start + timedelta(days=random.randint(0, 730),
                                   hours=random.randint(0, 23))
        segment = random.choices(SEGMENTS, weights=SEGMENT_WEIGHTS)[0]
        is_active = random.random() > (0.15 if segment == "Free" else 0.05)
        rows.append({
            "customer_id": f"C{cid:06d}",
            "first_name": random.choice(FIRST),
            "last_name": random.choice(LAST),
            "email": f"user{cid}@example.com",
            "signup_date": signup.strftime("%Y-%m-%d %H:%M:%S"),
            "country": random.choice(COUNTRIES),
            "acquisition_channel": random.choice(CHANNELS),
            "segment": segment,
            "is_active": is_active,
        })
    return rows

def main():
    rows = gen_customers()
    path = OUT / "raw_crm_customers.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows):,} customers -> {path}")

if __name__ == "__main__":
    main()
