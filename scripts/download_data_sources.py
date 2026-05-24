"""Download external crash datasets configured for CaliCrashDashboard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_sources import DATA_SOURCES, download_sources, selected_sources


def main() -> None:
    """Run the data acquisition CLI."""
    parser = argparse.ArgumentParser(
        description="Download official crash datasets into data/raw/external.",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Source id to download. Can be passed multiple times.",
    )
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Include optional broad sources, such as the RUNT vehicle-level view.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw/external",
        help="Directory where CSV files will be downloaded.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite files that already exist.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List configured sources without downloading.",
    )
    args = parser.parse_args()

    if args.list:
        for source in DATA_SOURCES:
            default = "default" if source.enabled_by_default else "optional"
            print(f"{source.source_id} [{default}] - {source.title}")
        return

    sources = selected_sources(args.sources, include_optional=args.include_optional)
    paths = download_sources(
        sources,
        output_dir=Path(args.output_dir),
        force=args.force,
    )
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
