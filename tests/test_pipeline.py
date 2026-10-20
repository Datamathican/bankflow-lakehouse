"""End-to-end test: full pipeline on a small dataset in an isolated directory."""
import duckdb
import pytest

from bankflow import cli, ingest
from bankflow.generate import generate


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    base = tmp_path_factory.mktemp("bankflow")
    cli.RAW, cli.DB = base / "raw", base / "wh.duckdb"
    generate(cli.RAW, n_customers=120, days=20, seed=3)
    ingest.ingest(cli.RAW, cli.DB)
    cli.cmd_transform(None)
    return cli.DB


def q(db, sql):
    con = duckdb.connect(str(db), read_only=True)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def test_every_bronze_row_is_accounted_for(warehouse):
    m = dict(q(warehouse, "select metric, value from gold.rpt_reconciliation"))
    assert m["bronze_rows"] == m["duplicates_removed"] + m["silver_rows"] + m["quarantined_rows"]
    assert m["quarantined_rows"] > 0 and m["duplicates_removed"] > 0


def test_fraud_patterns_are_detected(warehouse):
    recall = dict(q(warehouse, "select pattern, recall from gold.rpt_fraud_detection_quality"))
    assert recall["VELOCITY_BURST"] > 0.8
    assert recall["AMOUNT_OUTLIER"] > 0.8
    assert recall["GEO_HOP"] > 0.8


def test_gold_has_no_clear_text_pii(warehouse):
    rows = q(warehouse, "select column_name from information_schema.columns where table_schema='gold'")
    assert not {"full_name", "email", "date_of_birth"} & {r[0] for r in rows}


def test_contract_violation_is_caught(tmp_path):
    generate(tmp_path / "raw", n_customers=20, days=5, seed=1)
    p = tmp_path / "raw" / "transactions.csv"
    p.write_text(p.read_text().replace("amount,", "amt,", 1))
    with pytest.raises(ingest.ContractViolation):
        ingest.ingest(tmp_path / "raw", tmp_path / "x.duckdb")
