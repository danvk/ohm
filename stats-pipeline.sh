#!/usr/bin/env bash
set -o errexit

date=2026-03-01
planet=planet-260301_0301.osm.pbf

dir=stats/$date
mkdir -p $dir
uv run chrono_stats.py $planet --output_dir $dir
uv run bad_geometry.py $planet --output_dir $dir
