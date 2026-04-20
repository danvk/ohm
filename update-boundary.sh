#!/usr/bin/env bash
set -x
set -o errexit

planet=$1
output_dir=$2

uv run build_connectivity_graph.py $planet
uv run extract_for_web.py \
    --config boundary-viewer.config.jsonc \
    --output-dir $output_dir \
    $planet
