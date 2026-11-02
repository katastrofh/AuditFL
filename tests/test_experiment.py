"""Exercise the public quickstart and the documented mock fault semantics."""

from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from bcfl_contract.experiment import RunConfig, run_bcfl


def test_documented_mock_quickstart(tmp_path):
    out = tmp_path / "smoke"
    subprocess.run(
        [
            sys.executable, "-m", "scripts.run_contract_mvp",
            "--backend", "mock", "--dataset", "digits", "--clients", "10",
            "--quick", "--seed", "7", "--out", str(out),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        timeout=120,
    )

    plain = pd.read_csv(out / "plain_fl_rounds.csv")
    audit = pd.read_csv(out / "bcfl_mock_rounds.csv")
    receipts = pd.read_csv(out / "contract_mock_receipts.csv")
    summary_frame = pd.read_csv(out / "contract_mvp_summary.csv")
    assert len(summary_frame) == 1
    summary = summary_frame.iloc[0]

    assert plain["round"].tolist() == audit["round"].tolist() == [0, 1, 2, 3]
    for column in ("test_acc", "val_acc"):
        assert np.isfinite(audit[column]).all()
        assert audit[column].between(0, 1).all()
        np.testing.assert_allclose(audit[column], plain[column], rtol=0, atol=1e-12)
    for column in ("included", "refunds", "published"):
        assert audit[column].eq(10).all()
    for column in ("dropped", "unretrievable", "invalid", "store_get_failures"):
        assert audit[column].eq(0).all()

    assert summary["backend"] == "mock"
    assert summary["dataset"] == "sklearn_digits"
    assert summary["clients"] == 10
    assert summary["rounds"] == 4
    assert summary["tx_count"] == len(receipts) == 99
    assert receipts["status"].eq(1).all()
    assert receipts["event"].value_counts().to_dict() == {
        "ListingCreated": 1, "RoundFunded": 4, "TicketReserved": 40,
        "UpdatePublished": 40, "RoundFinalized": 4, "Claimed": 10,
    }
    assert summary["store_puts"] == 45
    assert summary["store_gets"] == 40
    assert summary["store_get_failures"] == 0
    assert summary["claim_errors_expected_when_no_entitlement"] == 0
    assert summary["accuracy_gap_vs_plain"] == pytest.approx(0, abs=1e-12)
    assert summary["final_test_acc"] == pytest.approx(audit["test_acc"].iloc[-1])
    assert (out / "paper_ready_notes.md").stat().st_size > 0
    for cid in audit["global_cid"]:
        assert (out / "artifact_store" / cid.replace(":", "_")).is_file()


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("dropout_rate", {"published": 0, "dropped": 3, "refunds": 0,
                          "invalid": 0, "unretrievable": 0}),
        ("invalid_rate", {"published": 3, "dropped": 0, "refunds": 3,
                          "invalid": 3, "unretrievable": 0}),
        ("storage_fail_rate", {"published": 3, "dropped": 0, "refunds": 0,
                               "invalid": 0, "unretrievable": 3}),
    ],
)
def test_all_failed_updates_preserve_model_and_account_for_faults(tmp_path, fault, expected):
    cfg = RunConfig(clients=3, rounds=2, local_epochs=1, seed=7, **{fault: 1.0})
    metrics, receipts, summary = run_bcfl(cfg, tmp_path)

    assert len(metrics) == 2
    assert metrics["included"].eq(0).all()
    for column, value in expected.items():
        assert metrics[column].eq(value).all()
    # With no included updates, both rounds keep the same global model.
    assert metrics["global_cid"].nunique() == 1
    assert metrics["test_acc"].nunique() == 1
    assert np.isfinite(metrics["test_acc"]).all()
    assert receipts["event"].eq("RoundFinalized").sum() == cfg.rounds
    expected_get_failures = 6 if fault == "storage_fail_rate" else 0
    assert summary.iloc[0]["store_get_failures"] == expected_get_failures
    # Retrieved malformed updates are refundable under the current runner.
    expected_claims = 3 if fault == "invalid_rate" else 0
    assert receipts["event"].eq("Claimed").sum() == expected_claims
    assert summary.iloc[0]["claim_errors_expected_when_no_entitlement"] == 3 - expected_claims
