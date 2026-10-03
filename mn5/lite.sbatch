#!/bin/bash
# Ejecuta una orden de análisis en un nodo de cómputo con el entorno ligero (sin torch).
# Para lo que pasa de 5 minutos de CPU, que es el límite de los logins.
#   sbatch -A <cuenta> -q gp_debug mn5/lite.sbatch python3 scripts/export_web.py mn5/cohorte.early.toml ...
#SBATCH --job-name=maps-lite
#SBATCH --cpus-per-task=8
#SBATCH --time=00:45:00
#SBATCH --output=logs/lite-%j.out
set -euo pipefail
export PATH="$PWD/bundle-lite/python/bin:$PATH" PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1 NUMEXPR_MAX_THREADS=64
"$@"
