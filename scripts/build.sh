#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"

npm run build

rm -rf "$ROOT/backend/static"
cp -r dist "$ROOT/backend/static"
rm -rf dist

echo "Frontend buildado em backend/static/"
