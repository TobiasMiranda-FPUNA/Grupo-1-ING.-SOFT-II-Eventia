#!/usr/bin/env bash
# ============================================================
# up.sh
# Proyecto: Eventia
#
# Punto de entrada único para levantar el proyecto completo
# (backend FastAPI + frontend Angular), en dos modos:
#
#   local   -> todo en localhost, igual que dev_up.sh.
#   remote  -> además abre un túnel público (cloudflared o ngrok)
#              hacia el frontend, para que otras personas entren
#              desde internet (demo al profe, compañeros, celular).
#
# En modo remote solo se expone el frontend. El dev server de
# Angular reenvía /api, /docs y /health al backend local mediante
# frontend/proxy.conf.mjs, así que no hace falta tocar el CORS ni
# exponer el puerto del backend.
#
# Uso:
#   ./scripts/up.sh            # modo local (por defecto)
#   ./scripts/up.sh local
#   ./scripts/up.sh remote
#
# Requisitos previos:
#   - Python 3, Node.js/npm y Postgres con la base cargada
#     (ver scripts/setup_local_db.sh).
#   - Solo modo remote: cloudflared (recomendado, no requiere
#     cuenta) o ngrok (requiere "ngrok config add-authtoken ...").
#       macOS:  brew install cloudflared
#       Linux:  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
#
# Variables de entorno opcionales:
#   BACKEND_PORT=8000
#   FRONTEND_PORT=4200
#   TUNNEL=cloudflared|ngrok   (por defecto, el primero que esté instalado)
#   NO_BROWSER=1               (no abrir el navegador automáticamente)
# ============================================================

set -euo pipefail

MODE="${1:-local}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-4200}"
TUNNEL="${TUNNEL:-}"
export BACKEND_PORT

case "$MODE" in
  local|remote) ;;
  -h|--help)
    sed -n '2,38p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *)
    echo "Modo desconocido: '$MODE'. Usá 'local' o 'remote'." >&2
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"

BACKEND_PID=""
FRONTEND_PID=""
TUNNEL_PID=""
TUNNEL_LOG=""

cleanup() {
  echo
  echo "Deteniendo procesos..."
  local pid
  for pid in "$TUNNEL_PID" "$FRONTEND_PID" "$BACKEND_PID"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
  for pid in "$TUNNEL_PID" "$FRONTEND_PID" "$BACKEND_PID"; do
    [[ -n "$pid" ]] && wait "$pid" 2>/dev/null || true
  done
  [[ -n "$TUNNEL_LOG" ]] && rm -f "$TUNNEL_LOG"
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
  [[ -n "${NO_BROWSER:-}" ]] && return 0
  if command -v open >/dev/null 2>&1; then
    open "$url"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  else
    echo "Abrí manualmente: $url"
  fi
}

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  else
    curl --silent --output /dev/null "http://localhost:$port"
  fi
}

# --- Elegir herramienta de túnel (solo modo remote) ---
if [[ "$MODE" == "remote" ]]; then
  if [[ -z "$TUNNEL" ]]; then
    if command -v cloudflared >/dev/null 2>&1; then
      TUNNEL="cloudflared"
    elif command -v ngrok >/dev/null 2>&1; then
      TUNNEL="ngrok"
    fi
  fi
  if [[ -z "$TUNNEL" ]] || ! command -v "$TUNNEL" >/dev/null 2>&1; then
    echo "Modo remote: no se encontró cloudflared ni ngrok." >&2
    echo "Instalá uno de los dos, por ejemplo:" >&2
    echo "  brew install cloudflared" >&2
    exit 1
  fi
fi

for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  if port_in_use "$port"; then
    echo "El puerto $port ya está en uso. Cerrá el proceso que lo ocupa o cambiá BACKEND_PORT/FRONTEND_PORT." >&2
    exit 1
  fi
done

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
  exec .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port "$BACKEND_PORT"
) > >(sed -u 's/^/[backend] /') 2>&1 &
BACKEND_PID=$!

if ! wait_for_url "http://localhost:$BACKEND_PORT/health" 30; then
  echo "El backend no respondió en 30s. Revisá el log [backend] arriba (¿Postgres está corriendo?)."
  exit 1
fi
echo "==> Backend listo."

# --- Levantar frontend ---
NG_CONFIG="development"
[[ "$MODE" == "remote" ]] && NG_CONFIG="remote"

echo "==> Iniciando frontend ($NG_CONFIG) en http://localhost:$FRONTEND_PORT ..."
(
  cd "$FRONTEND_DIR"
  exec node_modules/.bin/ng serve --configuration "$NG_CONFIG" --port "$FRONTEND_PORT"
) > >(sed -u 's/^/[frontend] /') 2>&1 &
FRONTEND_PID=$!

if ! wait_for_url "http://localhost:$FRONTEND_PORT" 120; then
  echo "El frontend no respondió en 120s. Revisá el log [frontend] arriba."
  exit 1
fi
echo "==> Frontend listo."

PUBLIC_URL=""

# --- Abrir túnel (solo modo remote) ---
if [[ "$MODE" == "remote" ]]; then
  TUNNEL_LOG="$(mktemp -t eventia-tunnel.XXXXXX)"
  echo "==> Abriendo túnel con $TUNNEL ..."

  if [[ "$TUNNEL" == "cloudflared" ]]; then
    cloudflared tunnel --no-autoupdate --url "http://localhost:$FRONTEND_PORT" >"$TUNNEL_LOG" 2>&1 &
    TUNNEL_PID=$!
    for _ in $(seq 1 30); do
      PUBLIC_URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -n 1 || true)"
      [[ -n "$PUBLIC_URL" ]] && break
      kill -0 "$TUNNEL_PID" 2>/dev/null || break
      sleep 1
    done
  else
    ngrok http "$FRONTEND_PORT" --log=stdout >"$TUNNEL_LOG" 2>&1 &
    TUNNEL_PID=$!
    for _ in $(seq 1 30); do
      PUBLIC_URL="$(curl --silent http://127.0.0.1:4040/api/tunnels 2>/dev/null \
        | grep -oE '"public_url":"https://[^"]+"' | head -n 1 | cut -d'"' -f4 || true)"
      [[ -n "$PUBLIC_URL" ]] && break
      kill -0 "$TUNNEL_PID" 2>/dev/null || break
      sleep 1
    done
  fi

  if [[ -z "$PUBLIC_URL" ]]; then
    echo "No se pudo obtener la URL pública del túnel. Log de $TUNNEL:" >&2
    cat "$TUNNEL_LOG" >&2
    exit 1
  fi
  echo "==> Túnel listo."
fi

if [[ "$MODE" == "remote" ]]; then
  open_browser "$PUBLIC_URL"
  echo
  echo "URL pública (compartila): $PUBLIC_URL"
  echo "API pública (Swagger):    $PUBLIC_URL/docs"
  echo "Local:                    http://localhost:$FRONTEND_PORT"
  echo
  echo "Atención: cualquiera con la URL puede entrar mientras el script esté corriendo."
else
  open_browser "http://localhost:$FRONTEND_PORT"
  echo
  echo "Backend:  http://localhost:$BACKEND_PORT/docs"
  echo "Frontend: http://localhost:$FRONTEND_PORT"
fi
echo "Ctrl+C para detener todo."

# Termina (y limpia) en cuanto cualquiera de los procesos se caiga.
while true; do
  for pid in "$BACKEND_PID" "$FRONTEND_PID" "$TUNNEL_PID"; do
    if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
      echo "Uno de los procesos terminó inesperadamente."
      exit 1
    fi
  done
  sleep 2
done
