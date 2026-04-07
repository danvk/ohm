#!/usr/bin/env bash
set -o errexit
set -x

planet=$1
output_dir=$2

uv run feature_stats.py $planet --output_dir $output_dir
uv run chrono_stats.py $planet --output_dir $output_dir
uv run bad_geometry.py $planet --output_dir $output_dir
uv run earth_coverage.py $planet --output_dir $output_dir
uv run dupe_finder.py $planet --output_dir $output_dir
