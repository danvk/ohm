#!/usr/bin/env python

import argparse
import csv
import sys
from glob import glob
from pathlib import Path

STATS_FILE = "stats.csv"


def main():
    parser = argparse.ArgumentParser(
        prog="Stats collator",
        description="Combine today's stats and yesterday's running stats to make today's running stats.",
    )
    parser.add_argument("yesterday", type=str, help="Path to yesterday dir")
    parser.add_argument("today", type=str, help="Path (or glob) to today dir(s)")
    parser.add_argument(
        "--start_fresh",
        action="store_true",
        help="Ignore yesterday dir and create a fresh, one-day stats file.",
    )
    args = parser.parse_args()

    yesterday_stats = Path(args.yesterday) / STATS_FILE
    if not args.start_fresh:
        assert yesterday_stats.exists()

    todays = [Path(p) for p in glob(args.today)]
    assert todays, f"{args.today} does not exist or match any files"
    todays.sort(key=lambda p: p.name)

    if not args.start_fresh:
        with open(yesterday_stats) as f:
            old_stats = csv.DictReader(f)
            old_rows = [*old_stats]
    else:
        old_rows = []

    new_rows = []
    for today in todays:
        new_row = {"date": today.name}
        for summary in today.glob("*.summary.csv"):
            with open(summary) as f:
                for row in csv.DictReader(f):
                    metric = row["type"]
                    value = row["count"]
                    new_row[metric] = value
        new_rows.append(new_row)

    rows = old_rows + new_rows
    fields = [*set(k for row in rows for k in row.keys())]
    fields.sort(key=lambda k: (k != "date", k))

    out_path = todays[-1] / STATS_FILE
    with open(out_path, "w") as f:
        out = csv.DictWriter(f, fieldnames=fields)
        out.writeheader()
        out.writerows(rows)

    sys.stderr.write(f"Wrote {len(rows)} days of stats to {out_path}\n")


if __name__ == "__main__":
    main()
