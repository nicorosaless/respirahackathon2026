#!/bin/bash
# Sirve la app con la cohorte real desde un nodo de cómputo. Los datos no salen de MareNostrum:
# el navegador llega por un túnel SSH.
#   sbatch -A <cuenta> -q acc_debug mn5/app.sbatch outputs/cohorte_v2
#   cat logs/app-nodo.txt                                  # nodo y puerto
#   ssh -N -L 8501:<nodo>:8501 <usuario>@alogin1.bsc.es    # en el portátil; luego http://localhost:8501
#
# Los logins matan los procesos de más de 5 minutos de CPU, por eso va en un trabajo.
#SBATCH --job-name=maps-app
#SBATCH --cpus-per-task=20
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --output=logs/app-%j.out
set -euo pipefail

cohort="$1"
port="${2:-8501}"
bundle_tar="${MAPS_BUNDLE_TAR:-$HOME/maps-bundle.tar.gz}"
work="${TMPDIR:-/tmp}/maps-$SLURM_JOB_ID"
mkdir -p "$work" logs

tar -xzf "$bundle_tar" -C "$work"
export MAPS_BUNDLE="$work/bundle"
source mn5/env.sh
echo "$(hostname) $port" > logs/app-nodo.txt
python3 -m streamlit run app/maps_app.py --server.headless true --browser.gatherUsageStats false \
  --server.address 0.0.0.0 --server.port "$port" -- --cohort "$cohort"
