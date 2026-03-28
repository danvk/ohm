import argparse

import osmium
import osmium.filter

from decimaldate import iso2dec


class DateExtractor(osmium.SimpleHandler):
    def __init__(self):
        super(DateExtractor, self).__init__()
        self.id_to_dates = dict[int, tuple[float, float]]()
        self.invalid = 0

    def relation(self, r) -> None:
        start_date = r.tags.get("start_date")
        end_date = r.tags.get("end_date")
        try:
            start_dec = start_date and iso2dec(start_date)
            end_dec = end_date and iso2dec(end_date)
        except ValueError:
            self.invalid += 1
            return

        self.id_to_dates[r.id] = (start_dec, end_dec)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find elements in an OSM PBF file by name."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")

    args = parser.parse_args()

    handler = DateExtractor()
    handler.apply_file(args.osm_file, filters=[osmium.filter.KeyFilter("start_date")])
    print(f"Read {len(handler.id_to_dates)} dated relations.")
    print(f"Found {handler.invalid} invalid dates.")


if __name__ == "__main__":
    main()
