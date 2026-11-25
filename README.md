# Business Automation System

A Python-based order-processing pipeline that validates business records, separates accepted and rejected orders, and generates audit-friendly reports.

## Why this project?

Small businesses often receive operational data in spreadsheets and CSV exports. This project demonstrates how to turn that repetitive manual workflow into a repeatable process with clear validation rules, structured outputs, and automated tests.

## Features

- CSV ingestion with required-column checks
- Email, amount, currency, status, and duplicate-order validation
- Normalization of accepted records
- Separate reports for accepted and rejected records
- JSON processing summary
- Command-line interface and structured logging
- Automated tests with pytest
- GitHub Actions workflow for continuous integration

## Project structure

```text
business-automation-system/
├── .github/workflows/tests.yml
├── data/sample_orders.csv
├── src/business_automation/
│   ├── __init__.py
│   ├── cli.py
│   └── processor.py
├── tests/test_processor.py
├── .env.example
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

## Requirements

- Python 3.10+
- pip

## Setup

```bash
git clone https://github.com/vitorsilveiraedv-blip/business-automation-system.git
cd business-automation-system
python -m venv .venv
```

Activate the virtual environment:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install the project and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

## Run the example

```bash
business-automation data/sample_orders.csv --output-dir output --verbose
```

The command creates:

- `processed_orders.csv`: valid, normalized orders
- `rejected_orders.csv`: rejected rows and validation reasons
- `summary.json`: totals and acceptance rate

The sample data intentionally includes invalid and duplicate records so both processing paths can be inspected.

## Run tests

```bash
pytest -v
```

## Input format

The CSV file must contain these columns:

| Column | Description |
|---|---|
| `order_id` | Unique order identifier |
| `customer_email` | Customer email address |
| `amount` | Positive monetary amount |
| `currency` | Three-letter currency code |
| `status` | `paid`, `pending`, or `cancelled` |

## Design decisions

- The standard library handles CSV, logging, paths, and decimal arithmetic to keep runtime dependencies small.
- `Decimal` is used for monetary values instead of binary floating-point arithmetic.
- Invalid records are reported rather than silently discarded.
- Duplicate identifiers are checked against previously accepted records.
- The processing functions are separated from the CLI to keep the core logic easy to test and reuse.

## Scope and limitations

This is a portfolio demonstration using local CSV files. It does not connect to a live payment provider, send customer messages, or modify a production database. API integrations can be added behind explicit interfaces in a future iteration.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
