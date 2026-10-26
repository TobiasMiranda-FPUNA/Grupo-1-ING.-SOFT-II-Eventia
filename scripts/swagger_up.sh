#!/usr/bin/env bash
# ============================================================
# swagger_up.sh
# Proyecto: Eventia
#
# Abre la documentación interactiva de la API (Swagger) en un
# solo paso:
#   1. Prepara backend/.venv y backend/.env si faltan.
#   2. Regenera backend/docs/openapi.json a partir del código.
#   3. Levanta el backend (si no está corriendo ya).
#   4. Abre el navegador en http://localhost:8000/api-docs/
# Con Ctrl+C se detiene el backend (solo si lo levantó este script).
#
# Uso:
#   ./scripts/swagger_up.sh
#
# Requisitos previos:
#   - Postgres corriendo con la base cargada (ver scripts/setup_local_db.sh)
#     para poder ejecutar los endpoints con "Try it out".
#
# Variables de entorno opcionales:
#   BACKEND_PORT=8000
# ============================================================

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"

SWAGGER_URL="http://localhost:$BACKEND_PORT/api-docs/"
HEALTH_URL="http://localhost:$BACKEND_PORT/health"

BACKEND_PID=""

cleanup() {
  if [[ -n "$BACKEND_PID" ]]; then
    echo
    echo "Deteniendo backend..."
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

wait_for_url() {
  local url="$1"
  local timeout="$2"
  local waited=0
  while ! curl --silent --fail --output /dev/null "$url"; do
    sleep 1
    waited=$((waited + 1))
    if [[ "$waited" -ge "$timeout" ]]; then
      return 1
    fi
  done
  return 0
}

open_browser() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then
    open "$url"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url"
  else
    echo "Abrí manualmente: $url"
  fi
}

# --- Preparar backend ---
if [[ ! -x "$BACKEND_DIR/.venv/bin/uvicorn" ]]; then
  echo "==> No se encontró backend/.venv, creándolo e instalando dependencias..."
  python3 -m venv "$BACKEND_DIR/.venv"
  "$BACKEND_DIR/.venv/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"
fi

if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  echo "==> No se encontró backend/.env, copiando desde .env.example..."
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

# --- Regenerar openapi.json ---
echo "==> Regenerando backend/docs/openapi.json ..."
(cd "$BACKEND_DIR" && .venv/bin/python docs/generate_openapi.py)

# --- Levantar backend (si no está corriendo) ---
if curl --silent --fail --output /dev/null "$HEALTH_URL"; then
  echo "==> El backend ya está corriendo en http://localhost:$BACKEND_PORT"
  open_browser "$SWAGGER_URL"
  echo
  echo "Swagger: $SWAGGER_URL"
  exit 0
fi

echo "==> Iniciando backend en http://localhost:$BACKEND_PORT ..."
(
  cd "$BACKEND_DIR"
  exec .venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT"
) > >(sed -u 's/^/[backend] /') 2>&1 &
BACKEND_PID=$!

if ! wait_for_url "$HEALTH_URL" 30; then
  echo "El backend no respondió en 30s. Revisá el log [backend] arriba."
  exit 1
fi
echo "==> Backend listo."

open_browser "$SWAGGER_URL"

echo
echo "Swagger (docs/index.html): $SWAGGER_URL"
echo "Swagger en vivo (FastAPI): http://localhost:$BACKEND_PORT/docs"
echo "Ctrl+C para detener el backend."

wait "$BACKEND_PID"
