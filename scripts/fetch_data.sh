#!/usr/bin/env bash
# Descarga los datos públicos usados en los experimentos a data/ (no versionado).
#   emphysema: Sørensen et al. 2010, 115 cortes HRCT y 168 parches de 39 sujetos.
#              Uso libre para investigación; no se puede redistribuir.
#   lidc:      volúmenes de tórax de LIDC-IDRI (TCIA, CC BY 3.0).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)/data"

fetch_emphysema() {
  local dir="$root/emphysema" page="https://lauge-soerensen.github.io/emphysema-database/"
  mkdir -p "$dir/slices" "$dir/patches"
  curl -fsS "$page" |
    grep -oE '<a href="https://sid.erda.dk/share_redirect/[A-Za-z0-9]+"[^>]*>[^<]+' |
    sed -E 's/<a href="([^"]+)"[^>]*>(.*)/\1 \2/' |
    while read -r url name; do
      curl -fsSL -o "$dir/$name" "$url"
    done
  unzip -q -o -j "$dir/slices.zip" -d "$dir/slices"
  unzip -q -o -j "$dir/patches.zip" -d "$dir/patches"
}

fetch_lidc() {
  local dir="$root/lidc" api="https://services.cancerimagingarchive.net/nbia-api/services/v1"
  # paciente:SeriesInstanceUID, series de TC con más de 200 cortes
  local series=(
    "LIDC-IDRI-0002:1.3.6.1.4.1.14519.5.2.1.6279.6001.619372068417051974713149104919"
    "LIDC-IDRI-0004:1.3.6.1.4.1.14519.5.2.1.6279.6001.323541312620128092852212458228"
    "LIDC-IDRI-0009:1.3.6.1.4.1.14519.5.2.1.6279.6001.286061375572911414226912429210"
    "LIDC-IDRI-0010:1.3.6.1.4.1.14519.5.2.1.6279.6001.416701701108520592702405866796"
  )
  for entry in "${series[@]}"; do
    local patient="${entry%%:*}" uid="${entry#*:}"
    [[ -d "$dir/$patient" ]] && continue
    mkdir -p "$dir/$patient"
    curl -fsS -o "$dir/$patient.zip" "$api/getImage?SeriesInstanceUID=$uid"
    unzip -q -o "$dir/$patient.zip" -d "$dir/$patient"
    rm "$dir/$patient.zip"
  done
}

case "${1:-all}" in
  emphysema) fetch_emphysema ;;
  lidc) fetch_lidc ;;
  all) fetch_emphysema; fetch_lidc ;;
  *) echo "uso: $0 [emphysema|lidc|all]" >&2; exit 2 ;;
esac
