import csv
import os
import random
import sys
from datetime import datetime
from pathlib import Path

LOG_COUNTER = 0


def log_to_stderr(name: str, msg: str):
    if os.environ.get("TESTING"):
        global LOG_COUNTER
        timestamp = LOG_COUNTER
        LOG_COUNTER += 1
    else:
        timestamp = datetime.now().isoformat()
    sys.stderr.write(f"{timestamp} {name} {msg}\n")


def log_start(name: str):
    log_to_stderr(name, "starting")


def log_finish(name: str):
    log_to_stderr(name, "completed")


def write_stats(
    out_dir: str | Path,
    name: str,
    examples: dict[str, list[tuple[str, int, str]]],
    other_stats: dict[str, int | float],
    preserve_sort_order=False,
    max_examples=5000,
    sample_size=1000,
):
    out_dir = Path(out_dir)
    with open(out_dir / f"{name}.summary.csv", "w") as f:
        out = csv.DictWriter(f, fieldnames=["type", "count"])
        out.writeheader()
        out.writerows(
            {"type": typ, "count": count} for typ, count in sorted(other_stats.items())
        )
        out.writerows(
            {"type": typ, "count": len(rs)}
            for typ, rs in sorted(examples.items())
            # allow "other_stats" to count differently, e.g. for earth_coverage.py
            if typ not in other_stats
        )

    rng = random.Random(2026)
    for typ, rs in sorted(examples.items()):
        with open(out_dir / f"{typ}.examples.txt", "w") as f:
            if preserve_sort_order:
                to_out = rs if len(rs) < max_examples else rs[:2_500]
            else:
                rs_sorted = sorted(rs)
                to_out = (
                    rs_sorted
                    if len(rs_sorted) < max_examples
                    else rng.sample(rs_sorted, sample_size)
                )
            f.writelines(
                f"{ftype}/{fid}: {problems}\n" for ftype, fid, problems in to_out
            )
    log_finish(name)
