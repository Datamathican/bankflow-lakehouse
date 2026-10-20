"""Synthetic retail-banking data generator.

Produces realistic raw extracts (customers, accounts, transactions) with:
  * deliberately dirty records (duplicates, nulls, bad currencies, orphans)
  * injected fraud patterns with ground-truth labels, so the detection
    logic can be measured (precision / recall), not just demonstrated.

Everything is seeded and therefore reproducible.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

CURRENCIES = ["GBP", "EUR", "USD", "INR"]
CURRENCY_WEIGHTS = [0.80, 0.10, 0.07, 0.03]
COUNTRIES = ["GB", "IE", "FR", "DE", "US", "IN", "ES", "NL"]
MERCHANT_CATEGORIES = [
    "GROCERY", "TRANSPORT", "DINING", "UTILITIES", "RETAIL",
    "TRAVEL", "ENTERTAINMENT", "HEALTH", "ATM", "TRANSFER",
]
CHANNELS = ["CARD_PRESENT", "ONLINE", "MOBILE", "ATM", "FASTER_PAYMENTS"]
SEGMENTS = ["RETAIL", "PREMIER", "SME"]
ACCOUNT_TYPES = ["CURRENT", "SAVINGS", "CREDIT_CARD"]
CITIES = ["London", "Manchester", "Leeds", "Edinburgh", "Bristol", "Brighton", "Eastbourne", "Cardiff"]
FIRST = ["Aarav", "Olivia", "Noah", "Priya", "Liam", "Amelia", "Rohan", "Isla", "Arjun", "Mia", "Oliver", "Ananya"]
LAST = ["Patel", "Smith", "Jones", "Singh", "Taylor", "Brown", "Khan", "Davies", "Evans", "Wilson", "Sharma", "Thomas"]


def generate(
    out_dir: Path,
    n_customers: int = 500,
    days: int = 30,
    seed: int = 42,
    start: datetime | None = None,
) -> dict[str, int]:
    rng = random.Random(seed)
    start = start or datetime(2026, 9, 1)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ingested = (start + timedelta(days=days + 1)).isoformat(sep=" ")

    # ---- customers & accounts -------------------------------------------
    customers, accounts = [], []
    for i in range(1, n_customers + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        customers.append({
            "customer_id": f"C{i:06d}",
            "full_name": f"{first} {last}",
            "email": f"{first}.{last}{i}@example.com".lower(),
            "date_of_birth": (datetime(1950, 1, 1) + timedelta(days=rng.randint(0, 20000))).date().isoformat(),
            "segment": rng.choices(SEGMENTS, [0.7, 0.2, 0.1])[0],
            "city": rng.choice(CITIES),
            "created_at": (start - timedelta(days=rng.randint(30, 3000))).isoformat(sep=" "),
            "ingested_at": ingested,
        })
        for _ in range(rng.choice([1, 1, 2])):
            accounts.append({
                "account_id": f"A{len(accounts) + 1:07d}",
                "customer_id": f"C{i:06d}",
                "account_type": rng.choice(ACCOUNT_TYPES),
                "opened_date": (start - timedelta(days=rng.randint(10, 2500))).date().isoformat(),
                "ingested_at": ingested,
            })

    acct_ids = [a["account_id"] for a in accounts]
    home_country = {a: "GB" for a in acct_ids}
    typical = {a: rng.uniform(15, 90) for a in acct_ids}

    # ---- legitimate transactions ----------------------------------------
    txns: list[dict] = []
    labels: list[dict] = []

    def add(account, ts, amount, currency="GBP", country=None, category=None,
            channel=None, direction="DEBIT", pattern=None):
        txn_id = f"T{len(txns) + 1:09d}"
        txns.append({
            "txn_id": txn_id,
            "account_id": account,
            "txn_ts": ts.isoformat(sep=" "),
            "amount": f"{amount:.2f}",
            "currency": currency,
            "direction": direction,
            "merchant_category": category or rng.choice(MERCHANT_CATEGORIES),
            "country": country or home_country[account],
            "channel": channel or rng.choice(CHANNELS),
            "ingested_at": ingested,
        })
        if pattern:
            labels.append({"txn_id": txn_id, "pattern": pattern})
        return txn_id

    for acct in acct_ids:
        for _ in range(rng.randint(40, 100)):
            ts = start + timedelta(seconds=rng.randint(0, days * 86400 - 1))
            amt = max(0.5, rng.gauss(typical[acct], typical[acct] * 0.35))
            cur = rng.choices(CURRENCIES, CURRENCY_WEIGHTS)[0]
            direction = "CREDIT" if rng.random() < 0.1 else "DEBIT"
            add(acct, ts, amt, cur, direction=direction)

    # ---- injected fraud --------------------------------------------------
    # 1) velocity bursts: 6-8 card-not-present spends within ~5 minutes
    n_bursts = max(5, n_customers // 12)
    for acct in rng.sample(acct_ids, n_bursts):
        t0 = start + timedelta(seconds=rng.randint(86400, (days - 1) * 86400))
        for k in range(rng.randint(6, 8)):
            add(acct, t0 + timedelta(seconds=k * rng.randint(20, 45)), rng.uniform(20, 60),
                channel="ONLINE", pattern="VELOCITY_BURST")

    # 2) amount outliers: 12-20x the account's typical spend
    n_out = max(5, n_customers // 16)
    for acct in rng.sample(acct_ids, n_out):
        ts = start + timedelta(seconds=rng.randint(0, days * 86400 - 1))
        add(acct, ts, typical[acct] * rng.uniform(12, 20), channel="ONLINE", pattern="AMOUNT_OUTLIER")

    # 3) geo hops: a domestic spend then a foreign one inside 30 minutes
    n_geo = max(5, n_customers // 25)
    for acct in rng.sample(acct_ids, n_geo):
        ts = start + timedelta(seconds=rng.randint(86400, (days - 1) * 86400))
        add(acct, ts, rng.uniform(10, 40), country="GB", channel="CARD_PRESENT")
        add(acct, ts + timedelta(minutes=rng.randint(10, 30)), rng.uniform(40, 120),
            country=rng.choice(["US", "IN", "FR"]), channel="CARD_PRESENT", pattern="GEO_HOP")

    clean_count = len(txns)

    # ---- dirty data -------------------------------------------------------
    n = len(txns)
    for row in rng.sample(txns, int(n * 0.010)):               # exact duplicates, re-delivered later
        dup = dict(row)
        dup["ingested_at"] = (datetime.fromisoformat(ingested) + timedelta(hours=6)).isoformat(sep=" ")
        txns.append(dup)
    for row in rng.sample(txns[:n], int(n * 0.005)):           # null amounts
        row["amount"] = ""
    for row in rng.sample(txns[:n], int(n * 0.003)):           # unsupported currency
        row["currency"] = "XXX"
    for row in rng.sample(txns[:n], int(n * 0.003)):           # non-positive amounts
        row["amount"] = f"-{abs(float(row['amount'] or 1)):.2f}"
    for row in rng.sample(txns[:n], int(n * 0.002)):           # orphan accounts
        row["account_id"] = "A9999999"
    for row in rng.sample(txns[:n], int(n * 0.002)):           # unparseable timestamps
        row["txn_ts"] = "not-a-timestamp"

    rng.shuffle(txns)
    pd.DataFrame(customers).to_csv(out_dir / "customers.csv", index=False)
    pd.DataFrame(accounts).to_csv(out_dir / "accounts.csv", index=False)
    pd.DataFrame(txns).to_csv(out_dir / "transactions.csv", index=False)
    pd.DataFrame(labels).to_csv(out_dir / "fraud_labels.csv", index=False)

    return {
        "customers": len(customers), "accounts": len(accounts),
        "transactions": len(txns), "clean_transactions": clean_count,
        "labelled_fraud_txns": len(labels),
    }
