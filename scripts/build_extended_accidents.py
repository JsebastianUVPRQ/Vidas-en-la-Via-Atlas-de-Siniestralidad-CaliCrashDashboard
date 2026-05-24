"""Build processed Valle-wide and Cali-only crash datasets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.etl_extended import write_extended_outputs


def main() -> None:
    """Run the extended accident ETL."""
    parser = argparse.ArgumentParser(
        description="Normalize external crash sources into processed CSV files.",
    )
    parser.add_argument("--input-dir", default="data/raw/external")
    parser.add_argument("--output-dir", default="data/processed")
    parser.add_argument(
        "--exclude-optional",
        action="store_true",
        help="Exclude optional broad sources such as the RUNT vehicle-level view.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print row counts by municipality and source after building.",
    )
    args = parser.parse_args()

    include_optional = not args.exclude_optional
    extended_path, cali_path = write_extended_outputs(
        output_dir=Path(args.output_dir),
        input_dir=Path(args.input_dir),
        include_optional=include_optional,
    )
    print(extended_path)
    print(cali_path)

    if args.summary:
        extended = pd.read_csv(
            extended_path,
            usecols=["municipio", "source_id"],
            dtype=str,
        )
        print("\nRegistros por municipio:")
        print(extended["municipio"].value_counts().to_string())
        print("\nRegistros por fuente:")
        print(extended["source_id"].value_counts().to_string())


if __name__ == "__main__":
    main()
