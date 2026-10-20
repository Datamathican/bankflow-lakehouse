import pandas as pd

from bankflow.generate import generate


def test_generator_is_deterministic(tmp_path):
    generate(tmp_path / "a", n_customers=60, days=10, seed=7)
    generate(tmp_path / "b", n_customers=60, days=10, seed=7)
    a = pd.read_csv(tmp_path / "a" / "transactions.csv")
    b = pd.read_csv(tmp_path / "b" / "transactions.csv")
    assert a.equals(b)


def test_generator_injects_dirty_data_and_labels(tmp_path):
    stats = generate(tmp_path, n_customers=100, days=15, seed=1)
    tx = pd.read_csv(tmp_path / "transactions.csv", dtype=str)
    labels = pd.read_csv(tmp_path / "fraud_labels.csv")
    assert tx.txn_id.duplicated().any()
    assert (tx.currency == "XXX").any()
    assert set(labels.pattern) == {"VELOCITY_BURST", "AMOUNT_OUTLIER", "GEO_HOP"}
    assert stats["labelled_fraud_txns"] == len(labels)
