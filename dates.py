import re
from typing import Optional, Tuple

DateTuple = Tuple[int, int, int]  # (year, month, day)
Range = Tuple[DateTuple, DateTuple]

NEG_INF: DateTuple = (-(10**12), 1, 1)
POS_INF: DateTuple = (10**12, 1, 1)

# Matches:
# 2026
# 2026-1
# 2026-01-01
# -1234-5-6
DATE_RE = re.compile(r"^(-?\d+)(?:-(\d{1,2})(?:-(\d{1,2}))?)?$")


# ----------------------------
# Normalization (OHM quirks)
# ----------------------------
def normalize_ohm_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None

    s = s.strip().lower()

    # Remove common uncertainty prefixes
    s = re.sub(r"^(c\.|ca\.|~)\s*", "", s)

    # Remove trailing junk (e.g. "1900?", "1900 (est.)")
    s = re.sub(r"[^\d\-].*$", "", s)

    # Reject embedded ranges like "1900-1910"
    if re.match(r"^-?\d{3,}-\d{3,}$", s):
        return None

    return s or None


# ----------------------------
# Parsing
# ----------------------------
def parse_ohm_date(
    s: Optional[str],
) -> Optional[Tuple[int, Optional[int], Optional[int]]]:
    s = normalize_ohm_date(s)
    if not s:
        return None

    m = DATE_RE.match(s)
    if not m:
        return None

    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else None
    day = int(m.group(3)) if m.group(3) else None

    # Basic validation (fail soft)
    if month is not None and not (1 <= month <= 12):
        return None
    if day is not None and not (1 <= day <= 31):
        return None

    return year, month, day


# ----------------------------
# Convert to boundary point
# ----------------------------
def start_of_date(parsed: Tuple[int, Optional[int], Optional[int]]) -> DateTuple:
    year, month, day = parsed

    if month is None:
        return (year, 1, 1)
    if day is None:
        return (year, month, 1)
    return (year, month, day)


# ----------------------------
# Range parsing
# ----------------------------
def parse_ohm_range(start: Optional[str], end: Optional[str]) -> Range:
    start_parsed = parse_ohm_date(start)
    end_parsed = parse_ohm_date(end)

    start_point = start_of_date(start_parsed) if start_parsed else NEG_INF
    end_point = start_of_date(end_parsed) if end_parsed else POS_INF

    return start_point, end_point


# ----------------------------
# Duration
# ----------------------------
def to_fractional_year(d: DateTuple) -> float:
    year, month, day = d
    return year + (month - 1) / 12 + (day - 1) / 365


def duration_years(r: Range) -> float:
    """Return the duration of a date range in fractional years.

    Uses month-precision arithmetic (months / 12) plus day offset (days / 365).
    Returns inf if either bound is unbounded (NEG_INF / POS_INF).
    """
    start, end = r

    if start == NEG_INF or end == POS_INF:
        return float("inf")

    return to_fractional_year(end) - to_fractional_year(start)


# ----------------------------
# Overlap logic
# ----------------------------
def overlaps(a: Range, b: Range) -> bool:
    (a_start, a_end) = a
    (b_start, b_end) = b
    return a_start < b_end and b_start < a_end


# ----------------------------
# Optional: comparison helpers
# ----------------------------
def contains(r: Range, point: DateTuple) -> bool:
    start, end = r
    return start <= point < end


# ----------------------------
# Examples / sanity checks
# ----------------------------
if __name__ == "__main__":
    # Example from your question
    A = parse_ohm_range("1991", "2000")
    B = parse_ohm_range("2000", None)

    print("A:", A)
    print("B:", B)
    print("Overlap?", overlaps(A, B))  # False

    # Partial dates
    C = parse_ohm_range("2000-05", "2001")
    D = parse_ohm_range("2000", "2000-06")

    print("Overlap C/D?", overlaps(C, D))  # True

    # Negative years
    E = parse_ohm_range("-1234", "-1200")
    F = parse_ohm_range("-1200", None)

    print("Overlap E/F?", overlaps(E, F))  # False

    # Messy input
    G = parse_ohm_range("c. 1900?", "1910 (est.)")
    H = parse_ohm_range("1905", None)

    print("Overlap G/H?", overlaps(G, H))  # True
