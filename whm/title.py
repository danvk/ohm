"""Parse and categorize WHM feature title strings."""

import re
from dataclasses import dataclass

# --- Date-range detection ---

_YEAR_TOK = r"c?\d+(?:BCE?|CE?|AD)?"
_DATE_RANGE_RE = re.compile(
    r"(?:" + _YEAR_TOK + r")\s*-\s*(?:" + _YEAR_TOK + r"|Present)",
    re.IGNORECASE,
)
# A "span" part starts with an optional 'c' followed by digits, or "Before"
_SPAN_START_RE = re.compile(r"^\s*(?:c?\d|Before\s)", re.IGNORECASE)


def _is_span(part: str) -> bool:
    """Does this comma-part look like a standalone date range (not a name or title)?"""
    return bool(_SPAN_START_RE.match(part))


def _has_date_range(part: str) -> bool:
    """Does this comma-part contain a year–dash–year range?"""
    return bool(_DATE_RANGE_RE.search(part))


# --- Post-span part classification ---

_DYNASTY_RE = re.compile(r"\b(?:Dynasty|Caliphate|House|Family)\b", re.IGNORECASE)
_TITLE_RE = re.compile(
    r"\b(?:Pharaoh|King|Queen|Emperor|Empress|Sultan|Caliph|Emir|Khan|"
    r"Tsar|Czar|Shah|Shogun|Pope|Duke|Earl|Count|Baron|Governor|"
    r"President|Prime\s+Minister|Regent|Lord|Prince|Princess|"
    r"Archon|Doge|Elector|Viceroy|Vizier)\b",
    re.IGNORECASE,
)


def _is_dynasty_part(part: str) -> bool:
    return bool(_DYNASTY_RE.search(part)) and _has_date_range(part)


def _is_leader_title_part(part: str) -> bool:
    return bool(_TITLE_RE.search(part)) and _has_date_range(part)


# --- Main dataclass and parser ---


@dataclass
class TitleParts:
    name: str
    span: str | None
    leader: str | None
    dynasty: str | None
    note: str | None


def parse_whm_title(title: str) -> TitleParts:
    """Parse a WHM feature title string into structured fields.

    WHM titles have the form:
      Name[, Qualifier][, Span][, LeaderName, LeaderTitle Dates][, Dynasty Dates][.]

    Examples:
      "Kish, c2900 - 2350BCE."
        → TitleParts(name="Kish", span="c2900 - 2350BCE", ...)
      "Egypt, Old Kingdom, 2925 - c2150BCE + -50 years, Snefru, Pharaoh c2575 - c2551BCE,
       Fourth Dynasty of Egypt c2575 - c2465BCE."
        → TitleParts(name="Egypt, Old Kingdom", span="2925 - c2150BCE + -50 years",
                     leader="Snefru, Pharaoh c2575 - c2551BCE",
                     dynasty="Fourth Dynasty of Egypt c2575 - c2465BCE")
    """
    # Split on commas; strip trailing punctuation and whitespace; drop empty parts
    parts = [p.strip().rstrip(".,") for p in title.split(",")]
    parts = [p for p in parts if p]

    # Step 1: Collect name parts; locate the span.
    # A span part starts with a year-like token (digit or 'c'+digit or 'Before').
    # A part that contains a date range but doesn't start with a year (e.g.
    # "Satomi Family 1467 - 1590") ends the name accumulation without setting span.
    name_parts: list[str] = []
    span: str | None = None
    post_start = len(parts)

    for i, part in enumerate(parts):
        if _is_span(part):
            span = part
            post_start = i + 1
            break
        elif _has_date_range(part):
            # Date-containing non-span part (dynasty or leader without explicit span)
            post_start = i
            break
        else:
            name_parts.append(part)

    name = ", ".join(name_parts)

    # Step 2: Classify post-span parts into leader / dynasty / note.
    leader: str | None = None
    dynasty: str | None = None
    note_parts: list[str] = []
    leader_buffer: str | None = None  # pending leader personal name

    for part in parts[post_start:]:
        if _is_dynasty_part(part):
            if dynasty is None:
                dynasty = part
        elif _is_leader_title_part(part):
            if leader is None:
                if leader_buffer is not None:
                    # "LeaderName" was buffered; combine with this title+date part
                    leader = f"{leader_buffer}, {part}"
                    leader_buffer = None
                else:
                    # Fused form: "Tailapa Ahavamalla King 973 - 997"
                    leader = part
        elif _has_date_range(part):
            # Date range but no classifying keyword → treat as leader name buffer
            if leader is None:
                leader_buffer = part
        elif leader is not None or dynasty is not None:
            # Free text after structured fields → note
            note_parts.append(part)
        else:
            # Plain name-only part (leader personal name before their title)
            if leader is None:
                if leader_buffer is not None:
                    # Two consecutive name-only parts; previous goes to note
                    note_parts.append(leader_buffer)
                leader_buffer = part

    # Unmatched leader_buffer with no following title → note
    if leader_buffer is not None and leader is None:
        note_parts.append(leader_buffer)

    note = ", ".join(note_parts) if note_parts else None
    return TitleParts(name=name, span=span, leader=leader, dynasty=dynasty, note=note)


def extract_base_name(title: str) -> str:
    """Return the first comma-delimited part of a WHM title.

    Used for chronology relation naming so that e.g. "Egypt, Old Kingdom" and
    "Egypt, New Kingdom" group under a single "Egypt" chronology entry.
    """
    return title.split(",")[0].strip()
