#!/bin/bash
# Vistazo rápido a todas las TC en un nodo de CPU. Usa el entorno ligero, sin torch.
#   sbatch -A <cuenta> -q gp_debug mn5/quicklook.sbatch outputs/manifiesto.csv outputs/eda
#SBATCH --job-name=maps-quicklook
#SBATCH --cpus-per-task=56
#SBATCH --time=00:30:00
#SBATCH --output=logs/quicklook-%j.out
set -euo pipefail
export PATH="$PWD/bundle-lite/python/bin:$PATH" PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1
export MPLCONFIGDIR="${TMPDIR:-/tmp}/mpl-$USER" OMP_NUM_THREADS=2
python3 scripts/quicklook.py "$1" --out "$2" --workers 28
