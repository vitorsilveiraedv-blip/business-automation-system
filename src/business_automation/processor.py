"""Validate and process order records from CSV files."""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)
REQUIRED_FIELDS = {"order_id", "customer_email", "amount", "currency", "status"}
VALID_STATUSES = {"paid", "pending", "cancelled"}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class ProcessedOrder:
    order_id: str
    customer_email: str
    amount: str
    currency: str
    status: str


@dataclass(frozen=True)
class RejectedOrder:
    row_number: int
    order_id: str
    errors: tuple[str, ...]


@dataclass(frozen=True)
class ProcessingResult:
    accepted: tuple[ProcessedOrder, ...]
    rejected: tuple[RejectedOrder, ...]


def validate_order(row: dict[str, str], seen_ids: set[str]) -> tuple[ProcessedOrder | None, list[str]]:
    """Return a normalized order or a list of validation errors."""
    errors: list[str] = []
    order_id = (row.get("order_id") or "").strip()
    email = (row.get("customer_email") or "").strip().lower()
    currency = (row.get("currency") or "").strip().upper()
    status = (row.get("status") or "").strip().lower()

    if not order_id:
        errors.append("order_id is required")
    elif order_id in seen_ids:
        errors.append("duplicate order_id")

    if not EMAIL_PATTERN.match(email):
        errors.append("customer_email must be a valid email address")

    try:
        amount = Decimal((row.get("amount") or "").strip())
        if not amount.is_finite() or amount <= 0:
            errors.append("amount must be a positive number")
    except (InvalidOperation, AttributeError):
        amount = Decimal("0")
        errors.append("amount must be a valid number")

    if not re.fullmatch(r"[A-Z]{3}", currency):
        errors.append("currency must be a 3-letter code")

    if status not in VALID_STATUSES:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")

    if errors:
        return None, errors

    return ProcessedOrder(
        order_id=order_id,
        customer_email=email,
        amount=f"{amount:.2f}",
        currency=currency,
        status=status,
    ), []


def process_rows(rows: Iterable[dict[str, str]]) -> ProcessingResult:
    """Validate rows, reject duplicates, and preserve input order."""
    accepted: list[ProcessedOrder] = []
    rejected: list[RejectedOrder] = []
    seen_ids: set[str] = set()

    for row_number, row in enumerate(rows, start=2):
        order, errors = validate_order(row, seen_ids)
        if order is None:
            rejected.append(RejectedOrder(
                row_number=row_number,
                order_id=(row.get("order_id") or "").strip(),
                errors=tuple(errors),
            ))
            logger.warning("Rejected CSV row %s: %s", row_number, "; ".join(errors))
            continue

        seen_ids.add(order.order_id)
        accepted.append(order)

    return ProcessingResult(tuple(accepted), tuple(rejected))


def process_csv(input_path: str | Path) -> ProcessingResult:
    """Read a CSV file and process its records."""
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("The input CSV is empty or has no header")

        missing = REQUIRED_FIELDS.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        result = process_rows(reader)

    logger.info("Processing complete: %s accepted, %s rejected",
                len(result.accepted), len(result.rejected))
    return result


def write_outputs(result: ProcessingResult, output_dir: str | Path) -> dict[str, Path]:
    """Write accepted and rejected records plus a machine-readable summary."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    accepted_path = destination / "processed_orders.csv"
    rejected_path = destination / "rejected_orders.csv"
    summary_path = destination / "summary.json"

    with accepted_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(ProcessedOrder.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(order) for order in result.accepted)

    with rejected_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["row_number", "order_id", "errors"])
        writer.writeheader()
        for item in result.rejected:
            writer.writerow({
                "row_number": item.row_number,
                "order_id": item.order_id,
                "errors": " | ".join(item.errors),
            })

    total = len(result.accepted) + len(result.rejected)
    summary = {
        "total_processed": total,
        "accepted": len(result.accepted),
        "rejected": len(result.rejected),
        "acceptance_rate": round(len(result.accepted) / total, 4) if total else 0,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"processed": accepted_path, "rejected": rejected_path, "summary": summary_path}
