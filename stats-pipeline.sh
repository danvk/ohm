#!/usr/bin/env bash
set -o errexit
set -x

date=$1  # 2026-03-01
yymmdd=${date//-/}
yymmdd=${yymmdd/#20/}  # 260301

s3cmd get s3://planet.openhistoricalmap.org/planet/planet-260331*
planet=planet-${yymmdd}_*.osm.pbf

dir=stats/$date
mkdir -p $dir
uv run chrono_stats.py $planet --output_dir $dir
uv run bad_geometry.py $planet --output_dir $dir

rm $planet
