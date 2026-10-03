#!/usr/bin/env bash
# Construye un Python autónomo con todas las dependencias en bundle/python.
# No depende de los módulos de MareNostrum ni de internet una vez copiado:
# el intérprete es python-build-standalone, que se puede mover de directorio.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
bundle="${1:-$repo/bundle}"
base="$(readlink -f "$(uv python dir)/cpython-3.12-linux-x86_64-gnu")"
[[ -x "$base/bin/python3.12" ]] || { echo "falta el Python gestionado por uv: uv python install 3.12" >&2; exit 1; }

mkdir -p "$bundle"
if [[ ! -x "$bundle/python/bin/python3.12" ]]; then
  cp -a "$base" "$bundle/python"
fi
uv pip install --python "$bundle/python/bin/python3.12" --break-system-packages \
  --index-strategy unsafe-best-match -r "$repo/mn5/requirements.txt"
"$bundle/python/bin/python3.12" -c "import torch, torchvision; print('torch', torch.__version__, 'cuda build', torch.version.cuda)"
