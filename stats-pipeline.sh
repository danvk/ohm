#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -x

date=$1  # 2026-03-01
dashdir=$2

# remove any previous download (no error on a fresh run)
rm -f planet-*.osm.pbf

yymmdd=${date//-/}
yymmdd=${yymmdd/#20/}  # 260301

# Fetch the planet for this specific date. The wildcard resolves the time suffix
# (planet-260301_0301.osm.pbf). If it isn't there yet, the run fails instead of
# falling back to an older planet, so we never run twice on the same planet file.
s3cmd get --force s3://planet.openhistoricalmap.org/planet/planet-${yymmdd}*
planet=planet-${yymmdd}_*.osm.pbf

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
