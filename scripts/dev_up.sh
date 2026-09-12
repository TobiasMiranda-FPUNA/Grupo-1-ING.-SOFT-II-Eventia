#!/usr/bin/env bash
# ============================================================
# dev_up.sh
# Proyecto: Eventia
#
# Levanta el backend (FastAPI/uvicorn) y el frontend (Angular),
# espera a que ambos respondan, y abre el navegador automáticamente
# en la app. Con Ctrl+C se detienen los dos procesos.
#
# Uso:
#   ./scripts/dev_up.sh
#
# Requisitos previos:
#   - backend/.venv creado con las dependencias instaladas
#     (ver README: python3 -m venv .venv && pip install -r requirements.txt).
#     Si no existe, este script lo crea automáticamente.
#   - backend/.env presente (se copia de .env.example si falta).
#   - Postgres corriendo con la base cargada (ver scripts/setup_local_db.sh).
#
# Variables de entorno opcionales:
#   BACKEND_PORT=8000
#   FRONTEND_PORT=4200   (si se cambia, actualizar también el CORS
#                          allow_origins en backend/app/main.py)
# ============================================================

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-4200}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo
  echo "Deteniendo backend y frontend..."
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  [[ -n "$BACKEND_PID" ]] && wait "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && wait "$FRONTEND_PID" 2>/dev/null || true
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

# --- Preparar frontend ---
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "==> No se encontró frontend/node_modules, instalando dependencias (npm install)..."
  (cd "$FRONTEND_DIR" && npm install)
fi

# --- Levantar backend ---
echo "==> Iniciando backend en http://localhost:$BACKEND_PORT ..."
(
  cd "$BACKEND_DIR"
  exec .venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT"
) > >(sed -u 's/^/[backend] /') 2>&1 &
BACKEND_PID=$!

if ! wait_for_url "http://localhost:$BACKEND_PORT/health" 30; then
  echo "El backend no respondió en 30s. Revisá el log [backend] arriba."
  exit 1
fi
echo "==> Backend listo."

# --- Levantar frontend ---
echo "==> Iniciando frontend en http://localhost:$FRONTEND_PORT ..."
(
  cd "$FRONTEND_DIR"
  exec node_modules/.bin/ng serve --port "$FRONTEND_PORT"
) > >(sed -u 's/^/[frontend] /') 2>&1 &
FRONTEND_PID=$!

if ! wait_for_url "http://localhost:$FRONTEND_PORT" 120; then
  echo "El frontend no respondió en 120s. Revisá el log [frontend] arriba."
  exit 1
fi
echo "==> Frontend listo."

open_browser "http://localhost:$FRONTEND_PORT"

echo
echo "Backend:  http://localhost:$BACKEND_PORT/docs"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "Ctrl+C para detener ambos."

wait "$BACKEND_PID" "$FRONTEND_PID"
