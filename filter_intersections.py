"""Filter intersections CSV to those within a lat/lng bounding box.

Usage: python filter_intersections.py <intersections.csv> <min_lon,min_lat,max_lon,max_lat>

Outputs a CSV of street1,street2 for intersections within the bounding box.
"""

import csv
import sys


def filter_intersections(
    csv_path: str, min_lon: float, min_lat: float, max_lon: float, max_lat: float
) -> None:
    writer = csv.writer(sys.stdout)
    writer.writerow(["street1", "street2"])

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = float(row["Lat"])
            lon = float(row["Lon"])
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                writer.writerow([row["Street1"], row["Street2"]])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            f"Usage: {sys.argv[0]} <intersections.csv> <min_lon,min_lat,max_lon,max_lat>"
        )
        sys.exit(1)

    csv_path = sys.argv[1]
    bbox_parts = sys.argv[2].split(",")
    if len(bbox_parts) != 4:
        print(
            "Error: bounding box must be 4 comma-separated values: min_lon,min_lat,max_lon,max_lat"
        )
        sys.exit(1)

    min_lon, min_lat, max_lon, max_lat = (float(v) for v in bbox_parts)
    min_lat, max_lat = min(min_lat, max_lat), max(min_lat, max_lat)
    min_lon, max_lon = min(min_lon, max_lon), max(min_lon, max_lon)
    filter_intersections(csv_path, min_lon, min_lat, max_lon, max_lat)
