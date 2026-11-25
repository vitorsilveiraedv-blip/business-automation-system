"""Command-line interface for the order automation pipeline."""

import argparse
import logging

from business_automation.processor import process_csv, write_outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate business orders from a CSV file and generate reports."
    )
    parser.add_argument("input", help="Path to the source CSV file")
    parser.add_argument("--output-dir", default="output",
                        help="Directory for generated reports (default: output)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable detailed log messages")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    try:
        result = process_csv(args.input)
        paths = write_outputs(result, args.output_dir)
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))

    print(f"Accepted: {len(result.accepted)}")
    print(f"Rejected: {len(result.rejected)}")
    for label, path in paths.items():
        print(f"{label.title()} report: {path}")


if __name__ == "__main__":
    main()
