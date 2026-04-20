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


def extract_paths(
    svg_path: Path,
    groups: tuple[str, ...] = ("terr", "ctry"),
) -> list[dict]:
    """
    Extract raw path data from a WHM SVG file.

    Returns a list of dicts with keys:
      'id'    – the path element's id attribute
      'path'  – the raw SVG d= string (unprojected pixel coordinates)
      'fill'  – the fill attribute (may be absent)
      'title' – from the matching <text id="…"><title> element (may be absent)

    Only <path> elements inside the named group elements are returned.
    Groups that don't exist in a given file are silently skipped.
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
    for group_id in groups:
        group = root.find(f'.//{svg_tag("g")}[@id="{group_id}"]')
        if group is None:
            continue
        for path_el in group.iter(svg_tag("path")):
            pid = path_el.get("id", "")
            d = path_el.get("d", "")
            if not (pid and d):
                continue
            entry: dict = {"id": pid, "path": d}
            fill = path_el.get("fill")
            if fill:
                entry["fill"] = fill
            if pid in titles:
                entry["title"] = titles[pid]
            results.append(entry)

    return results
