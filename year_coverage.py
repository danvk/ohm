"""Output the number of features valid in each year from -6000 to 2030.

For each relation/way tagged with boundary=administrative:
- If it lacks a start_date, ignore it.
- If it lacks an end_date, assume it remains valid through the present day.
- Only the first four characters of start_date/end_date are used (year only).

Output is a tab-delimited table: year<TAB>count
"""

import argparse
import sys
from collections import defaultdict

import osmium
import osmium.filter

FIRST_YEAR = -6000
LAST_YEAR = 2030


def parse_year(date_str: str) -> int | None:
    """Extract the year from the first 4 characters of a date string (supports negatives)."""
    if not date_str:
        return None
    s = date_str.strip()
    try:
        # Negative years: "-500-01-01" → split on "-" gives ["", "500", "01", "01"]
        if s.startswith("-"):
            parts = s[1:].split("-")
            return -int(parts[0])
        else:
            return int(s[:4])
    except (ValueError, IndexError):
        return None


class YearCountHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        # year → count of features valid in that year
        self.counts: dict[int, int] = defaultdict(int)
        self._captured_ids: set[tuple[str, int]] = set()
        self.total = 0
        self.skipped_no_start = 0

    def _process(self, tags, orig_type: str, orig_id: int) -> None:
        if tags.get("boundary") != "administrative":
            return

        key = (orig_type, orig_id)
        if key in self._captured_ids:
            return
        self._captured_ids.add(key)

        start_str = tags.get("start_date", "")
        end_str = tags.get("end_date", "")

        start_year = parse_year(start_str)
        if start_year is None:
            self.skipped_no_start += 1
            return

        end_year = parse_year(end_str)
        if end_year is None:
            end_year = LAST_YEAR

        lo = max(start_year, FIRST_YEAR)
        hi = min(end_year, LAST_YEAR)

        for year in range(lo, hi + 1):
            self.counts[year] += 1

        self.total += 1
        if self.total % 1000 == 0:
            print(f"  {self.total} features processed...", file=sys.stderr)

    def relation(self, r) -> None:
        self._process(r.tags, "relation", r.id)

    def way(self, w) -> None:
        self._process(w.tags, "way", w.id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Count features valid in each year from -6000 to 2030."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    args = parser.parse_args()

    print(f"Reading {args.osm_file} ...", file=sys.stderr)
    handler = YearCountHandler()
    handler.apply_file(args.osm_file, filters=[osmium.filter.KeyFilter("start_date")])

    print(
        f"Read {handler.total} features with start_date; "
        f"{handler.skipped_no_start} skipped (no start_date).",
        file=sys.stderr,
    )

    print("year\tcount")
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        print(f"{year}\t{handler.counts.get(year, 0)}")


if __name__ == "__main__":
    main()
