#!/usr/bin/env bash
set -o errexit
set -x

date=$1  # 2026-03-01
yymmdd=${date//-/}
yymmdd=${yymmdd/#20/}  # 260301

s3cmd get --force s3://planet.openhistoricalmap.org/planet/planet-${yymmdd}*
planet=planet-${yymmdd}_*.osm.pbf

dir=daily/$date
mkdir -p $dir
./extract_stats $planet $dir

rm $planet
