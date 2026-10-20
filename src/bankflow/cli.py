"""bankflow command line: generate -> ingest -> transform (dbt) -> export -> report."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import duckdb

from . import generate as gen
from . import ingest as ing

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "warehouse.duckdb"
EXPORT = ROOT / "data" / "gold_export"
DBT_DIR = ROOT / "dbt"


def _dbt(*args: str) -> None:
    """Run dbt in a subprocess so its DuckDB connection is fully released afterwards."""
    env = {**os.environ, "DUCKDB_PATH": str(DB)}
    cmd = [sys.executable, "-c", "from dbt.cli.main import cli; cli()",
           *args, "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    if subprocess.run(cmd, env=env).returncode != 0:
        raise SystemExit(f"dbt {' '.join(args)} failed")


def cmd_generate(a) -> None:
    print("generated:", gen.generate(RAW, n_customers=a.customers, days=a.days, seed=a.seed))


def cmd_ingest(_a) -> None:
    print("bronze rows:", ing.ingest(RAW, DB))


def cmd_transform(_a) -> None:
    _dbt("seed")
    _dbt("build")          # runs models AND tests, so bad data stops the pipeline


def cmd_export(_a) -> None:
    EXPORT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    for (table,) in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='gold'").fetchall():
        con.execute(f"COPY gold.{table} TO '{EXPORT / (table + '.parquet')}' (FORMAT PARQUET)")
        print(f"exported gold.{table}")
    con.close()


def cmd_report(_a) -> None:
    con = duckdb.connect(str(DB), read_only=True)
    print("\n=== Pipeline reconciliation ===")
    for row in con.execute("SELECT * FROM gold.rpt_reconciliation").fetchall():
        print(f"{row[0]:<32}{row[1]:>10,}")
    print("\n=== Fraud detection quality (vs injected ground truth) ===")
    print(f"{'pattern':<18}{'labelled':>9}{'caught':>8}{'recall':>9}")
    for p, n, c, r in con.execute(
            "SELECT pattern, labelled, detected, recall FROM gold.rpt_fraud_detection_quality ORDER BY 1").fetchall():
        print(f"{p:<18}{n:>9}{c:>8}{r:>9.1%}")
    prec = con.execute("SELECT precision FROM gold.rpt_fraud_precision").fetchone()[0]
    print(f"\nAlert precision: {prec:.1%}")
    con.close()


def cmd_run_all(a) -> None:
    cmd_generate(a)
    cmd_ingest(a)
    cmd_transform(a)
    cmd_export(a)
    cmd_report(a)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bankflow", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in [("generate", cmd_generate), ("ingest", cmd_ingest), ("transform", cmd_transform),
                     ("export", cmd_export), ("report", cmd_report), ("run-all", cmd_run_all)]:
        sp = sub.add_parser(name)
        sp.add_argument("--customers", type=int, default=500)
        sp.add_argument("--days", type=int, default=30)
        sp.add_argument("--seed", type=int, default=42)
        sp.set_defaults(fn=fn)
    args = p.parse_args(argv)
    args.fn(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
