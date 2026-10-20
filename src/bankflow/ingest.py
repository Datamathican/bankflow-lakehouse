"""Bronze layer: contract-validated, append-only raw landing in DuckDB.

Raw files are loaded as VARCHAR on purpose. Bronze must never lose or reject
data because of typing; casting and quarantine happen in silver.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"

DATASETS = {
    "customers": "raw_customers",
    "accounts": "raw_accounts",
    "transactions": "raw_transactions",
    "fraud_labels": "raw_fraud_labels",   # ground truth, used only for evaluation
}


class ContractViolation(Exception):
    """Raised when a raw file does not satisfy its data contract."""


def load_contract(dataset: str) -> dict:
    return yaml.safe_load((CONTRACTS_DIR / f"{dataset}.yaml").read_text())


def validate_contract(con: duckdb.DuckDBPyConnection, csv_path: Path, dataset: str) -> None:
    contract = load_contract(dataset)
    cols = {r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_csv('{csv_path}', all_varchar=true, header=true)").fetchall()}
    required = {c for c, spec in contract["columns"].items() if spec.get("required")}
    missing = required - cols
    if missing:
        raise ContractViolation(f"{dataset}: missing required columns {sorted(missing)}")


def ingest(raw_dir: Path, db_path: Path) -> dict[str, int]:
    raw_dir, db_path = Path(raw_dir), Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    counts: dict[str, int] = {}
    for dataset, table in DATASETS.items():
        path = raw_dir / f"{dataset}.csv"
        if dataset != "fraud_labels":
            validate_contract(con, path, dataset)
        con.execute(
            f"CREATE OR REPLACE TABLE bronze.{table} AS "
            f"SELECT * FROM read_csv('{path}', all_varchar=true, header=true)"
        )
        counts[table] = con.execute(f"SELECT count(*) FROM bronze.{table}").fetchone()[0]
    con.close()
    return counts
