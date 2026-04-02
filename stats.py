import csv
import random
from pathlib import Path


def write_stats(
    out_dir: str | Path,
    name: str,
    examples: dict[str, list[tuple[str, int, str]]],
    other_stats: dict[str, int | float],
):
    out_dir = Path(out_dir)
    with open(out_dir / f"{name}.summary.csv", "w") as f:
        out = csv.DictWriter(f, fieldnames=["type", "count"])
        out.writeheader()
        out.writerows(
            {"type": typ, "count": count} for typ, count in other_stats.items()
        )
        out.writerows({"type": typ, "count": len(rs)} for typ, rs in examples.items())

    for typ, rs in examples.items():
        with open(out_dir / f"{typ}.examples.txt", "w") as f:
            to_out = rs if len(rs) < 5_000 else random.sample(rs, 1_000)
            f.writelines(
                f"{ftype}/{fid}: {problems}\n" for ftype, fid, problems in to_out
            )
