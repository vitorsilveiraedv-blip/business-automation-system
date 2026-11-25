import csv
import json

import pytest

from business_automation.processor import process_csv, process_rows, write_outputs


def valid_row(order_id="ORD-001"):
    return {
        "order_id": order_id,
        "customer_email": "Customer@Example.com",
        "amount": "125.5",
        "currency": "usd",
        "status": "PAID",
    }


def test_valid_order_is_normalized():
    result = process_rows([valid_row()])
    assert len(result.accepted) == 1
    assert result.accepted[0].customer_email == "customer@example.com"
    assert result.accepted[0].amount == "125.50"
    assert result.accepted[0].currency == "USD"
    assert result.accepted[0].status == "paid"


def test_invalid_order_is_rejected():
    row = valid_row()
    row["customer_email"] = "not-an-email"
    row["amount"] = "-10"
    result = process_rows([row])
    assert len(result.accepted) == 0
    assert len(result.rejected) == 1
    assert len(result.rejected[0].errors) == 2


def test_duplicate_order_id_is_rejected():
    result = process_rows([valid_row(), valid_row()])
    assert len(result.accepted) == 1
    assert "duplicate order_id" in result.rejected[0].errors


def test_write_outputs_creates_reports(tmp_path):
    invalid = {"order_id": "", "customer_email": "", "amount": "x",
               "currency": "", "status": ""}
    result = process_rows([valid_row(), invalid])
    paths = write_outputs(result, tmp_path)
    assert all(path.exists() for path in paths.values())
    summary = json.loads(paths["summary"].read_text())
    assert summary["accepted"] == 1
    assert summary["rejected"] == 1


def test_process_csv_rejects_missing_columns(tmp_path):
    source = tmp_path / "orders.csv"
    source.write_text("order_id,amount\nORD-1,10\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required columns"):
        process_csv(source)


def test_process_csv_reads_valid_row(tmp_path):
    source = tmp_path / "orders.csv"
    with source.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(valid_row().keys()))
        writer.writeheader()
        writer.writerow(valid_row())
    assert len(process_csv(source).accepted) == 1
