#!/bin/bash
# Procesa toda la cohorte en un nodo con 4 GPU.
#   sbatch -A <cuenta> -q acc_debug mn5/extract_node.sbatch outputs/manifiesto.csv outputs/cohorte
#
# El entorno se descomprime en el disco local del nodo: en GPFS, crear sus 50.000
# ficheros tarda más de una hora; en el disco local, un par de minutos.
#SBATCH --job-name=maps-extract
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=80
#SBATCH --time=01:30:00
#SBATCH --output=logs/extract-%j.out
set -euo pipefail

manifest="$1"
cohort="$2"
bundle_tar="${MAPS_BUNDLE_TAR:-$HOME/maps-bundle.tar.gz}"
work="${TMPDIR:-/tmp}/maps-$SLURM_JOB_ID"
mkdir -p "$work" logs "$cohort"

echo "descomprimiendo el entorno en $work"
time tar -xzf "$bundle_tar" -C "$work"
export MAPS_BUNDLE="$work/bundle"
source mn5/env.sh
python3 -c "import torch; print('torch', torch.__version__, '| GPU visibles:', torch.cuda.device_count())"

total=$(($(wc -l < "$manifest") - 1))
for gpu in 0 1 2 3; do
  (
    # La GPU g se queda con las líneas g+1, g+5, g+9... del manifiesto.
    for k in $(seq $((gpu + 1)) 4 "$total"); do
      line="$(sed -n "$((k + 1))p" "$manifest")"
      IFS=, read -r subject folder series <<< "$line"
      CUDA_VISIBLE_DEVICES=$gpu python3 scripts/extract_subject.py "$folder" --id "$subject" --out "$cohort" \
        --save-masks ${series:+--series-uid "$series"} || echo "FALLO $subject"
    done
  ) > "logs/extract-$SLURM_JOB_ID-gpu$gpu.log" 2>&1 &
done
wait
echo "procesados: $(ls "$cohort/sujetos" 2>/dev/null | wc -l) de $total"
grep -h "^FALLO" logs/extract-"$SLURM_JOB_ID"-gpu*.log || echo "sin fallos"
