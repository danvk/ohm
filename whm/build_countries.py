#!/usr/bin/env python3
"""
Build countries.json from all WHM SVG files.

Scans ~/Documents/ohm/whm/W[AB]*.svg, extracts the raw SVG path data
for every <path> in the 'ctry' and 'terr' groups, and groups consecutive
years where the (fill, path) pair is unchanged into a single segment.

Output: whm/countries.json
  {
    "<path-id>": [
      {"fill": "#RRGGBB", "path": "M ...", "start_date": <year>, "end_date": <year>},
      ...
    ],
    ...
  }

Years use astronomical year numbering:
  WA0001.svg -> year   1  (1 AD)
  WB0001.svg -> year   0  (1 BC)
  WB0002.svg -> year  -1  (2 BC)
  WBN.svg    -> year 1-N

Usage:
    python whm/build_countries.py
    python whm/build_countries.py --svg-dir /path/to/svgs
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from svg import extract_paths

DEFAULT_SVG_DIR = Path.home() / "Documents/ohm/whm"
OUTPUT = Path(__file__).parent / "countries.json"


def year_from_name(name: str) -> int:
    """
    Derive astronomical year from a WHM SVG filename.

    WA1234.svg  ->  1234  (AD)
    WB1234.svg  ->  1-1234 = -1233  (BC; 1 BC = year 0, 2 BC = year -1, …)
    """
    m = re.match(r'^W([AB])(\d+)\.svg$', name, re.IGNORECASE)
    if not m:
        raise ValueError(f"Unexpected filename: {name!r}")
    n = int(m.group(2))
    return n if m.group(1).upper() == 'A' else 1 - n


def main() -> None:
    ap = argparse.ArgumentParser(description="Build countries.json from WHM SVG files")
    ap.add_argument(
        "--svg-dir", type=Path, default=DEFAULT_SVG_DIR,
        help=f"Directory containing W[AB]*.svg files (default: {DEFAULT_SVG_DIR})",
    )
    ap.add_argument(
        "--out", type=Path, default=OUTPUT,
        help=f"Output JSON path (default: {OUTPUT})",
    )
    args = ap.parse_args()

    svg_files = sorted(
        args.svg_dir.glob("W[AB]*.svg"),
        key=lambda p: year_from_name(p.name),
    )
    if not svg_files:
        print(f"No SVG files found in {args.svg_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(svg_files)} SVG files "
          f"(years {year_from_name(svg_files[0].name)} "
          f"to {year_from_name(svg_files[-1].name)})…")

    # current[id] = open segment dict with keys fill, path, start_date, end_date
    current: dict[str, dict] = {}
    segments: dict[str, list] = defaultdict(list)

    for i, svg_path in enumerate(svg_files):
        year = year_from_name(svg_path.name)
        paths = extract_paths(svg_path)
        current_ids = {p["id"] for p in paths}

        # Close segments for IDs absent from this year
        for pid in list(current.keys()):
            if pid not in current_ids:
                segments[pid].append(current.pop(pid))

        for p in paths:
            pid = p["id"]
            fill = p.get("fill", "")
            path = p["path"]

            seg = current.get(pid)
            if seg and seg["fill"] == fill and seg["path"] == path:
                seg["end_date"] = year          # extend existing segment
            else:
                if seg:
                    segments[pid].append(seg)   # close changed segment
                current[pid] = {
                    "fill": fill,
                    "path": path,
                    "start_date": year,
                    "end_date": year,
                }

        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(svg_files)}")

    # Flush still-open segments
    for pid, seg in current.items():
        segments[pid].append(seg)

    result = dict(segments)
    args.out.write_text(json.dumps(result, separators=(",", ":")))

    total_segs = sum(len(v) for v in result.values())
    size_mb = args.out.stat().st_size / 1024 / 1024
    print(f"Wrote {len(result):,} IDs, {total_segs:,} segments → {args.out}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
