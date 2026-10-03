#!/usr/bin/env bash
# Descarga al bundle todos los pesos que el pipeline pide en su primer uso.
# Se ejecuta en una máquina con internet, antes de copiar el bundle a MareNostrum.
set -euo pipefail
cd "$(dirname "$0")/.."
MAPS_ONLINE=1 source mn5/env.sh
mkdir -p "$TORCH_HOME" "$HF_HOME" "$TOTALSEG_HOME_DIR"

python3 - <<'PY'
from huggingface_hub import snapshot_download
from lungmask import LMInferer

from maps.backbone import PatchEncoder

LMInferer(modelname="R231", force_cpu=True)
LMInferer(modelname="LTRCLobes", force_cpu=True)
PatchEncoder("imagenet")
PatchEncoder("radimagenet")
# Encoder 3D de TC con licencia Apache-2.0, por si se quieren embeddings por parche.
snapshot_download("project-lighter/ct_fm_feature_extractor")
PY
# total_fast es el modelo de 3 mm que `total` usa para recortar: sin él intenta descargarlo al ejecutar.
for task in total total_fast lung_vessels; do
  python3 -m totalsegmentator.bin.totalseg_download_weights -t "$task"
done
du -sh "$MAPS_BUNDLE/weights"/*
