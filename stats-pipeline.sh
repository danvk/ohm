#!/usr/bin/env bash
set -o errexit
set -x

date=$1  # 2026-03-01
dashdir=$2

# remove yesterday's download
rm $(ls planet-*.osm.pbf | tail -1)

yymmdd=${date//-/}
yymmdd=${yymmdd/#20/}  # 260301

s3cmd get --force s3://planet.openhistoricalmap.org/planet/planet-${yymmdd}*
planet=planet-${yymmdd}_*.osm.pbf

dir=$dashdir/daily/$date
mkdir -p $dir
./extract-stats.sh $planet $dir
./update-boundary.sh $planet $dashdir/boundary

uv run collate_stats.py --start_fresh '' $dashdir/daily/'????-??-??'
cp $dir/stats.csv $dashdir/dashboard/

# Show the daily diff
cat $dir/diff.txt

# leave today's download for followup work
# rm $planet
