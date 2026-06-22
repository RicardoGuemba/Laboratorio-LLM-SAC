#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Instalando dependências Python..."
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt

echo "==> Instalando dependências Node..."
cd frontend
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
cd "$ROOT"

echo "==> Build do frontend..."
bash scripts/build.sh

echo "==> Preparando app macOS..."
bash scripts/preparar-app.sh

echo ""
echo "==> Pronto! Duplo clique em: Abrir Laboratorio Personas LLM.app"
