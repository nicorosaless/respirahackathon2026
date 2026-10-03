#!/bin/bash
# Recalcula las medidas desde las máscaras guardadas, en un nodo de CPU y con el entorno ligero.
#   sbatch -A <cuenta> -q gp_debug mn5/remeasure.sbatch outputs/manifiesto.csv outputs/cohorte outputs/cohorte_v2 [outputs/calidad_series.csv]
#SBATCH --job-name=maps-remeasure
#SBATCH --cpus-per-task=56
#SBATCH --time=00:30:00
#SBATCH --output=logs/remeasure-%j.out
set -euo pipefail
export PATH="$PWD/bundle-lite/python/bin:$PATH" PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1 OMP_NUM_THREADS=2 NUMEXPR_MAX_THREADS=64
python3 scripts/remeasure.py "$1" --masks "$2" --out "$3" --workers 28
python3 scripts/collect_cohort.py "$3" ${4:+--calidad "$4"}
