#!/usr/bin/env python3
"""
Analyze and display parsed F1 data from persistence files.
"""

import json
import pandas as pd
from pathlib import Path
import sys
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import BASE_DIR


def analyze_parsed_data():
    """Analyze all parsed F1 data."""

    data_dir = BASE_DIR / "data" / "f1_parsed_data"
    debug_dir = BASE_DIR / "data" / "debug_html"

    print(f"\n🔍 F1 DATA ANALYSIS REPORT")
    print(f"=" * 60)
    print(f"Data Directory: {data_dir}")
    print(f"Debug Directory: {debug_dir}")

    if not data_dir.exists():
        print(f"❌ No data directory found!")
        return

    # Analyze JSON files
    json_files = list(data_dir.glob("*.json"))
    print(f"\n📊 Found {len(json_files)} JSON data files:")

    for json_file in sorted(json_files):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            print(f"\n📄 {json_file.name}")
            print(
                f"   Available: {data.get('available', data.get('session_available', 'Unknown'))}"
            )
            print(f"   Results Count: {len(data.get('results', []))}")

            # Show top 3 results if available
            results = data.get("results", [])
            if results:
                print(f"   Top 3:")
                for i, result in enumerate(results[:3], 1):
                    driver = result.get("driver", "Unknown")
                    time = result.get("time", "No time")
                    print(f"     {i}. {driver} - {time}")
            else:
                print(f"   No results extracted")

            # Show parsing attempts if available
            attempts = data.get("parsing_attempts", [])
            if attempts:
                print(f"   Parsing Attempts: {len(attempts)}")
                for attempt in attempts:
                    print(f"     - {attempt}")

        except Exception as e:
            print(f"   ❌ Error reading {json_file.name}: {e}")

    # Analyze CSV files
    csv_files = list(data_dir.glob("*.csv"))
    print(f"\n📈 Found {len(csv_files)} CSV data files:")

    for csv_file in sorted(csv_files):
        try:
            df = pd.read_csv(csv_file)
            print(f"\n📄 {csv_file.name}")
            print(f"   Rows: {len(df)}, Columns: {len(df.columns)}")
            if len(df) > 0:
                print(f"   Columns: {', '.join(df.columns)}")
                print(f"   Sample data:")
                print(df.head(3).to_string(index=False))
        except Exception as e:
            print(f"   ❌ Error reading {csv_file.name}: {e}")

    # Analyze TXT summary files
    txt_files = list(data_dir.glob("*_summary.txt"))
    print(f"\n📝 Found {len(txt_files)} summary files:")

    for txt_file in sorted(txt_files):
        print(f"\n📄 {txt_file.name}")
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            # Show first 15 lines
            for line in lines[:15]:
                if line.strip():
                    print(f"   {line}")

            if len(lines) > 15:
                print(f"   ... ({len(lines) - 15} more lines)")

        except Exception as e:
            print(f"   ❌ Error reading {txt_file.name}: {e}")

    # Analyze HTML debug files
    html_files = list(debug_dir.glob("*.html"))
    print(f"\n🔍 Found {len(html_files)} HTML debug files:")

    for html_file in sorted(html_files):
        size_kb = html_file.stat().st_size / 1024
        print(f"   📄 {html_file.name} ({size_kb:.1f} KB)")

    print(f"\n" + "=" * 60)
    print(f"Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def view_specific_file(filepath: str):
    """View specific parsed data file."""
    path = Path(filepath)

    if not path.exists():
        print(f"❌ File not found: {filepath}")
        return

    print(f"\n📄 VIEWING: {path.name}")
    print(f"=" * 60)

    try:
        if path.suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(json.dumps(data, indent=2))

        elif path.suffix == ".csv":
            df = pd.read_csv(path)
            print(df.to_string(index=False))

        elif path.suffix in [".txt", ".html"]:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            print(content)

        else:
            print(f"Unsupported file type: {path.suffix}")

    except Exception as e:
        print(f"❌ Error viewing file: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze parsed F1 data files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--file", "-f", help="View specific file (provide full path)")

    args = parser.parse_args()

    if args.file:
        view_specific_file(args.file)
    else:
        analyze_parsed_data()


if __name__ == "__main__":
    main()
