#!/usr/bin/env bash
set -euo pipefail

APP_FILE="${1:-app.py}"
OUT_DIR="${OUT_DIR:-docs}"

if [[ ! -f "$APP_FILE" ]]; then
  echo "Missing $APP_FILE" >&2
  exit 1
fi
if [[ ! -f assets_fixed.zip ]]; then
  echo "Missing assets_fixed.zip. Put it next to $APP_FILE." >&2
  exit 1
fi

# Panel embeds the source below its Pyodide bootstrap. A future import in the
# application would therefore no longer be at the start of the generated unit.
if grep -Eq '^[[:space:]]*from[[:space:]]+__future__[[:space:]]+import' "$APP_FILE"; then
  echo "Error: remove all 'from __future__ import ...' lines from $APP_FILE before panel convert." >&2
  exit 1
fi

resources=(assets_fixed.zip)
if [[ -f assets/logo_WISP.jpg ]]; then
  resources+=(assets/logo_WISP.jpg)
elif [[ -f assets/logo_WISP.png ]]; then
  resources+=(assets/logo_WISP.png)
else
  echo "Warning: assets/logo_WISP.jpg was not found; the embedded archive/path fallback will be used." >&2
fi

rm -rf "$OUT_DIR"

panel convert "$APP_FILE" \
  --to pyodide-worker \
  --compiled \
  --out "$OUT_DIR" \
  --title "Axion Limits Explorer" \
  --requirements matplotlib \
  --resources "${resources[@]}" \
  --disable-http-patch

html_name="$(basename "${APP_FILE%.*}").html"
if [[ ! -f "$OUT_DIR/$html_name" ]]; then
  echo "Build finished, but $OUT_DIR/$html_name was not generated." >&2
  exit 1
fi
mv "$OUT_DIR/$html_name" "$OUT_DIR/index.html"

echo
echo "Build complete: $OUT_DIR/index.html"
echo "Deploy every file generated in $OUT_DIR, not only index.html."
echo "Test with: python -m http.server --directory $OUT_DIR 8000"
