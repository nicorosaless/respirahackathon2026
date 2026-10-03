#!/bin/bash
# Una TC por tarea del array. Lanzar con:
#   sbatch -A <cuenta> -q <cola> --array=1-<N>%16 mn5/extract_array.sbatch outputs/manifiesto.csv outputs/cohorte
# El manifiesto es un CSV con cabecera y columnas subject_id,carpeta[,serie_uid].
#SBATCH --job-name=maps-extract
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=20
#SBATCH --time=00:30:00
#SBATCH --output=logs/extract-%A_%a.out
set -euo pipefail

manifest="$1"
cohort="$2"
source mn5/env.sh
export SRUN_CPUS_PER_TASK="${SLURM_CPUS_PER_TASK:-20}"

# La línea 1 es la cabecera: la tarea k lee la línea k+1.
line="$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$manifest")"
IFS=, read -r subject folder series <<< "$line"
[[ -n "$subject" ]] || { echo "sin línea $SLURM_ARRAY_TASK_ID en $manifest" >&2; exit 1; }

python3 scripts/extract_subject.py "$folder" --id "$subject" --out "$cohort" --save-masks ${series:+--series-uid "$series"}
