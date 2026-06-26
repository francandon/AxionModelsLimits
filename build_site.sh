#!/usr/bin/env bash
set -euo pipefail

APP_FILE="${1:-app.py}"
OUT_DIR="${OUT_DIR:-docs}"
TITLE="${TITLE:-Axion Limits Explorer}"

if [[ ! -f "$APP_FILE" ]]; then
  echo "Missing $APP_FILE" >&2
  exit 1
fi

if [[ -f assets_core.zip ]]; then
  initial_archive="assets_core.zip"
  lazy_archive="assets_extra.zip"
elif [[ -f assets_fixed.zip ]]; then
  initial_archive="assets_fixed.zip"
  lazy_archive=""
elif [[ -f assets.zip ]]; then
  initial_archive="assets.zip"
  lazy_archive=""
else
  echo "Missing assets_core.zip, assets_fixed.zip, or assets.zip" >&2
  exit 1
fi

if [[ -n "$lazy_archive" && ! -f "$lazy_archive" ]]; then
  echo "Missing $lazy_archive" >&2
  exit 1
fi

if grep -Eq '^[[:space:]]*from[[:space:]]+__future__[[:space:]]+import' "$APP_FILE"; then
  echo "Remove all 'from __future__ import ...' lines before panel convert." >&2
  exit 1
fi

resources=("$initial_archive")
if [[ -f assets/logo_WISP.jpg ]]; then
  resources+=(assets/logo_WISP.jpg)
elif [[ -f assets/logo_WISP.png ]]; then
  resources+=(assets/logo_WISP.png)
fi

rm -rf "$OUT_DIR"

panel convert "$APP_FILE" \
  --to pyodide-worker \
  --compiled \
  --pwa \
  --out "$OUT_DIR" \
  --title "$TITLE" \
  --requirements matplotlib \
  --resources "${resources[@]}" \
  --disable-http-patch

html_name="$(basename "${APP_FILE%.*}").html"
if [[ ! -f "$OUT_DIR/$html_name" ]]; then
  echo "Build completed but $OUT_DIR/$html_name was not generated." >&2
  exit 1
fi
mv "$OUT_DIR/$html_name" "$OUT_DIR/index.html"

if [[ -n "$lazy_archive" ]]; then
  # Deliberately keep the large optional archive out of the initial Panel
  # resource bundle. app.py fetches it only when the bounds catalogue is opened.
  cp "$lazy_archive" "$OUT_DIR/assets_extra.zip"
fi

if [[ -f "$OUT_DIR/images/favicon.ico" && ! -f "$OUT_DIR/favicon.ico" ]]; then
  cp "$OUT_DIR/images/favicon.ico" "$OUT_DIR/favicon.ico"
fi

cat <<MSG
Adaptive-label build complete: $OUT_DIR/index.html

Initial runtime data: $initial_archive
Lazy bounds data:     ${lazy_archive:-already included in the initial archive}

Deploy every file generated in $OUT_DIR, including the worker JS, service worker,
manifest, icons, resource archive, and assets_extra.zip if present.

Local test:
  python -m http.server --directory $OUT_DIR 8000

The first visit must still initialize Pyodide, Panel, NumPy and Matplotlib. The
PWA cache improves later visits. Keep DevTools' "Disable cache" option off.
MSG
