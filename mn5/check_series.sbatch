#!/bin/bash
# Control de calidad de las series: posiciones de corte de todas las TC del manifiesto.
#   sbatch -A <cuenta> -q gp_debug mn5/check_series.sbatch outputs/manifiesto.csv outputs/calidad_series.csv
#SBATCH --job-name=maps-check
#SBATCH --cpus-per-task=56
#SBATCH --time=00:20:00
#SBATCH --output=logs/check-%j.out
set -euo pipefail
export PATH="$PWD/bundle-lite/python/bin:$PATH" PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
python3 scripts/check_series.py "$1" --out "$2" --workers 28
