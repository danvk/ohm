"""Extract GeoJSON features for administrative boundary relations and ways.

Reads a planet.osm.pbf file and outputs a GeoJSON FeatureCollection for every
relation or way tagged with boundary=administrative and admin_level=2.
"""

import argparse
import json
import sys
from typing import Any

import osmium
import osmium.geom


def tags_to_dict(tags) -> dict[str, str]:
    return {tag.k: tag.v for tag in tags}


class AdminBoundaryHandler(osmium.SimpleHandler):
    def __init__(self, max_features: int | None = None):
        super().__init__()
        self.geojson = osmium.geom.GeoJSONFactory()
        self.features: list[dict] = []
        self.max_features = max_features
        # Track which original IDs we've already captured via the area callback
        # so we don't double-count.
        self._captured_ids: set[tuple[str, int]] = set()

    def _is_admin2(self, tags) -> bool:
        return (
            tags.get("boundary") == "administrative" and tags.get("admin_level") == "2"
        )

    def _done(self) -> bool:
        return self.max_features is not None and len(self.features) >= self.max_features

    def area(self, a: Any) -> None:
        """Called for closed ways and relations that form areas."""
        if self._done():
            return
        if not self._is_admin2(a.tags):
            return

        try:
            geometry_str = self.geojson.create_multipolygon(a)
        except Exception:
            return

        geometry = json.loads(geometry_str)
        props = tags_to_dict(a.tags)

        # osmium area IDs are encoded: relation → 2*id+1, way → 2*id
        if a.from_way():
            orig_type = "way"
            orig_id = a.orig_id()
        else:
            orig_type = "relation"
            orig_id = a.orig_id()

        key = (orig_type, orig_id)
        if key in self._captured_ids:
            return
        self._captured_ids.add(key)

        props["@type"] = orig_type
        props["@id"] = orig_id

        self.features.append(
            {
                "type": "Feature",
                "id": f"{orig_type}/{orig_id}",
                "geometry": geometry,
                "properties": props,
            }
        )
        print(
            f"  Captured {orig_type}/{orig_id} ({props.get('name', '<no name>')})",
            file=sys.stderr,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract GeoJSON features for boundary=administrative + admin_level=2 "
            "relations and ways from an OSM PBF file."
        )
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument(
        "-o",
        "--output",
        default="-",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "-n",
        "--max-features",
        type=int,
        default=None,
        metavar="N",
        help="Stop after capturing N features (useful for testing)",
    )
    args = parser.parse_args()

    print(f"Reading {args.osm_file} ...", file=sys.stderr)
    handler = AdminBoundaryHandler(max_features=args.max_features)

    try:
        # locations=True is required so that way nodes have coordinates.
        # The area callback requires a two-pass read (osmium handles this
        # automatically when an area() method is present).
        handler.apply_file(args.osm_file, locations=True)
    except RuntimeError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    feature_collection = {
        "type": "FeatureCollection",
        "features": handler.features,
    }

    output_str = json.dumps(feature_collection, ensure_ascii=False, indent=2)

    if args.output == "-":
        print(output_str)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)
        print(
            f"Wrote {len(handler.features)} features to {args.output}", file=sys.stderr
        )

    print(f"Done. {len(handler.features)} features extracted.", file=sys.stderr)


if __name__ == "__main__":
    main()
