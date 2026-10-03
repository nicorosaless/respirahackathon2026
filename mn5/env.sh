# Uso: source mn5/env.sh   (desde cualquier sitio; vale en MareNostrum y en local)
# Pone en el PATH el Python autónomo y apunta todas las cachés de pesos al bundle,
# en modo sin conexión: en MareNostrum los nodos no tienen salida a internet.
_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export MAPS_BUNDLE="${MAPS_BUNDLE:-$_repo/bundle}"
export PATH="$MAPS_BUNDLE/python/bin:$PATH"
export PYTHONPATH="$_repo/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONNOUSERSITE=1
export NUMEXPR_MAX_THREADS=64  # numexpr protesta en nodos de más de 64 núcleos si no se fija
export TORCH_HOME="$MAPS_BUNDLE/weights/torch"
export HF_HOME="$MAPS_BUNDLE/weights/huggingface"
export TOTALSEG_HOME_DIR="$MAPS_BUNDLE/weights/totalsegmentator"
export MPLCONFIGDIR="${TMPDIR:-/tmp}/maps-matplotlib-$USER"
if [[ "${MAPS_ONLINE:-0}" != "1" ]]; then
  export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
fi
unset _repo
