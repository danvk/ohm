#!/usr/bin/env python3
"""
Build countries.json from all WHM SVG files.

Scans ~/Documents/ohm/whm/W[AB]*.svg, extracts the raw SVG path data,
fill colour, and tooltip title for every <path> in the 'ctry' and 'terr'
groups, and groups consecutive years where all three properties are unchanged
into a single segment.

To minimise repetition, each segment only carries the properties that changed
relative to the previous segment for the same ID.  The first segment always
carries all three.  start_date and end_date are always present.

Output: whm/countries.json
  {
    "<path-id>": [
      {"fill": "#RRGGBB", "path": "M ...", "title": "Egypt, ...", "start_date": -3000, "end_date": -2500},
      {"title": "Egypt (Roman Province), ...",                     "start_date": -2499, "end_date": -30},
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
from tqdm import tqdm

OUTPUT = Path(__file__).parent / "countries.json"

PROPS = ("fill", "path", "title")


def year_from_name(name: str) -> int:
    """Derive astronomical year from a WHM SVG filename.

    WA1234.svg  ->  1234  (AD)
    WB1234.svg  ->  1-1234 = -1233  (BC; 1 BC = year 0, 2 BC = year -1, …)
    """
    m = re.match(r"^W([AB])(\d+)\.svg$", name, re.IGNORECASE)
    if not m:
        raise ValueError(f"Unexpected filename: {name!r}")
    n = int(m.group(2))
    return n if m.group(1).upper() == "A" else 1 - n


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build countries.json from WHM SVG files"
    )
    parser.add_argument(
        "--svg-dir",
        type=Path,
        required=True,
        help="Directory containing W[AB]*.svg files.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUTPUT,
        help=f"Output JSON path (default: {OUTPUT})",
    )
    args = parser.parse_args()

    svg_files = sorted(
        args.svg_dir.glob("W[AB]*.svg"),
        key=lambda p: year_from_name(p.name),
    )
    if not svg_files:
        print(f"No SVG files found in {args.svg_dir}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Processing {len(svg_files)} SVG files "
        f"(years {year_from_name(svg_files[0].name)} "
        f"to {year_from_name(svg_files[-1].name)})…"
    )

    # current_values[id] = full current state of all three tracked properties.
    # current_seg[id]    = the open segment dict (only changed props + dates).
    current_values: dict[str, dict] = {}
    current_seg: dict[str, dict] = {}
    segments: dict[str, list] = defaultdict(list)

    for i, svg_path in enumerate(tqdm(svg_files, smoothing=0)):
        year = year_from_name(svg_path.name)
        paths = extract_paths(svg_path)
        current_ids = {p["id"] for p in paths}

        # Close segments for IDs absent from this year
        for pid in list(current_seg.keys()):
            if pid not in current_ids:
                segments[pid].append(current_seg.pop(pid))
                del current_values[pid]

        for p in paths:
            pid = p["id"]
            new_vals = {prop: p.get(prop, "") for prop in PROPS}

            if pid not in current_values:
                # First appearance: emit all properties
                current_values[pid] = new_vals
                current_seg[pid] = {**new_vals, "start_date": year, "end_date": year}
            else:
                changed = {
                    k: v for k, v in new_vals.items() if v != current_values[pid][k]
                }
                if changed:
                    # At least one property changed: close old segment, open new one
                    segments[pid].append(current_seg[pid])
                    current_values[pid].update(changed)
                    current_seg[pid] = {**changed, "start_date": year, "end_date": year}
                else:
                    # Nothing changed: extend the current segment
                    current_seg[pid]["end_date"] = year

    # Flush still-open segments
    for pid, seg in current_seg.items():
        segments[pid].append(seg)

    result = dict(segments)
    args.out.write_text(json.dumps(result, separators=(",", ":")))

    total_segs = sum(len(v) for v in result.values())
    size_mb = args.out.stat().st_size / 1024 / 1024
    print(
        f"Wrote {len(result):,} IDs, {total_segs:,} segments → {args.out}  ({size_mb:.1f} MB)"
    )


if __name__ == "__main__":
    main()
