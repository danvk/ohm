"""Shared SVG parsing utilities for WHM files."""

import re
from pathlib import Path
from xml.etree import ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"


def svg_tag(local: str) -> str:
    """Return SVG-namespace-qualified tag name."""
    return f"{{{SVG_NS}}}{local}"


def parse_id(path_id: str) -> tuple[str, str]:
    """
    Split a path id like '30439186-egypt' into (osm_id, name).
    Handles plain names without a numeric prefix.
    """
    m = re.match(r"^(\d+)-(.+)$", path_id)
    if m:
        return m.group(1), m.group(2)
    return "", path_id


def extract_paths(svg_path: Path) -> list[dict]:
    """Extract raw path data from a WHM SVG file.

    Returns one dict per <path> element that has a non-'none' fill color,
    drawn from any named <g> group in the file.  Each dict has keys:
      'id'    - the path element's id attribute
      'path'  - the raw SVG d= string (unprojected pixel coordinates)
      'fill'  - the fill color (always present and not 'none')
      'type'  - the id of the enclosing <g> group (e.g. 'ctry', 'area', 'polis')
      'title' - from the matching <text id="…"><title> element (may be absent)
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Build id -> title lookup from <text> elements (one pass)
    titles: dict[str, str] = {}
    for text_el in root.iter(svg_tag("text")):
        tid = text_el.get("id", "")
        if not tid:
            continue
        title_el = text_el.find(svg_tag("title"))
        if title_el is not None and title_el.text:
            titles[tid] = title_el.text

    results: list[dict] = []
    for group_el in root.iter(svg_tag("g")):
        group_id = group_el.get("id", "")
        if not group_id:
            continue
        for path_el in group_el.findall(svg_tag("path")):
            pid = path_el.get("id", "")
            d = path_el.get("d", "")
            fill = path_el.get("fill", "")
            if not (pid and d and fill and fill != "none"):
                continue
            entry: dict = {"id": pid, "path": d, "fill": fill, "type": group_id}
            if pid in titles:
                entry["title"] = titles[pid]
            results.append(entry)

    return results
