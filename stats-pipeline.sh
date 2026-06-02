#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -x

dashdir=$1

# remove any previous download (no error on a fresh run)
rm -f planet-*.osm.pbf

# Get the latest planet from state.txt instead of guessing by date.
# state.txt holds the public URL of the latest planet, so download it directly
# (no S3 credentials needed for the planet bucket).
state_url=${PLANET_STATE_TXT_URL:-https://s3.amazonaws.com/planet.openhistoricalmap.org/planet/state.txt}
planet_url=$(curl -fsSL "$state_url")            # http://planet.openhistoricalmap.org.s3.amazonaws.com/planet/planet-260601_0301.osm.pbf
planet=$(basename "$planet_url")                 # planet-260601_0301.osm.pbf
curl -fL -o "$planet" "$planet_url"

# Derive the date from the planet's Last-Modified header (works for any filename,
# e.g. a future planet-latest.osm.pbf).
last_modified=$(curl -fsIL "$planet_url" | grep -i '^last-modified:' | tail -1 | sed 's/^[Ll]ast-[Mm]odified:[ ]*//; s/\r$//')
date=$(date -u -d "$last_modified" +%Y-%m-%d)

dir=$dashdir/daily/$date
# Create the output dirs up front: on a fresh run none of them exist yet.
mkdir -p "$dir" "$dashdir/boundary" "$dashdir/dashboard"
./extract-stats.sh $planet $dir
./update-boundary.sh $planet $dashdir/boundary

uv run collate_stats.py --start_fresh '' $dashdir/daily/'????-??-??'
cp $dir/stats.csv $dashdir/dashboard/

# Show the daily diff (only exists once there are 2+ days)
cat "$dir/diff.txt" 2>/dev/null || echo "no diff yet (need 2+ days of stats)"

# leave today's download for followup work
# rm $planet
