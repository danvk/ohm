#!/usr/bin/env bash
set -x
set -o errexit

planet=$1
output_dir=$2

uv run build_connectivity_graph.py $planet
uv run extract_for_web.py \
    --simplify-tolerance-m 1000 \
    --vw-tolerance-m2 100000 \
    --admin-levels 1,2,3,4,5,6,7 \
    --graph graph.json \
    --coloring welsh-powell \
    --output-dir $output_dir \
    $planet
