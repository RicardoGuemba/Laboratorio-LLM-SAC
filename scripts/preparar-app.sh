#!/bin/bash
# Gera o app de duplo clique para macOS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="Abrir Laboratorio Personas LLM.app"
APP_PATH="$ROOT/$APP_NAME"
SERVER_APP="Laboratorio-Personas-LLM.app"

echo "Gerando $APP_NAME ..."
rm -rf "$APP_PATH"
osacompile -o "$APP_PATH" "$ROOT/scripts/LaboratorioPersonasLLM.applescript"

chmod +x "$ROOT/$SERVER_APP/Contents/MacOS/launcher"
chmod +x "$ROOT/Laboratorio-Personas-LLM-Stop.command" 2>/dev/null || true

xattr -cr "$APP_PATH" 2>/dev/null || true
xattr -cr "$ROOT/$SERVER_APP" 2>/dev/null || true

codesign --force --deep --sign - "$APP_PATH" 2>/dev/null || true
codesign --force --deep --sign - "$ROOT/$SERVER_APP" 2>/dev/null || true

echo ""
echo "Pronto: $APP_PATH"
echo "Duplo clique em: Abrir Laboratorio Personas LLM.app"
echo ""
