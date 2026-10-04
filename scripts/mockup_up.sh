#!/usr/bin/env bash
# ============================================================
# mockup_up.sh
# Proyecto: Eventia
#
# Abre en el navegador el mockup interactivo de las pantallas
# (carpeta mockup/). Permite elegir la pantalla por argumento o
# desde un menú, levanta un servidor HTTP local para servir la
# carpeta y abre el navegador directamente en esa pantalla.
# Con Ctrl+C se detiene el servidor.
#
# Uso:
#   ./scripts/mockup_up.sh              # menú interactivo
#   ./scripts/mockup_up.sh <pantalla>   # abre esa pantalla
#   ./scripts/mockup_up.sh --list       # lista las pantallas
#
# Pantallas: todas, login, roles, eventos, evento-nuevo, evento-editar,
#            expositores
#
# Requisitos: python3 (si no está, se abre el archivo HTML
# directamente, sin servidor).
#
# Variables de entorno opcionales:
#   MOCKUP_PORT=4300
# ============================================================

set -euo pipefail

MOCKUP_PORT="${MOCKUP_PORT:-4300}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MOCKUP_DIR="$REPO_ROOT/mockup"

PANTALLAS=(todas login roles eventos evento-nuevo evento-editar expositores)

SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    echo
    echo "Deteniendo servidor del mockup..."
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

pagina_de() {
  case "$1" in
    todas)         echo "index.html" ;;
    login)         echo "login.html" ;;
    roles)         echo "roles.html" ;;
    eventos)       echo "eventos.html" ;;
    evento-nuevo)  echo "evento-form.html" ;;
    evento-editar) echo "evento-form.html?id=1" ;;
    expositores)   echo "expositores.html" ;;
    *)             return 1 ;;
  esac
}

descripcion_de() {
  case "$1" in
    todas)         echo "Índice con todas las pantallas" ;;
    login)         echo "Login (/login)" ;;
    roles)         echo "Administración de roles (/roles)" ;;
    eventos)       echo "Catálogo de eventos (/eventos)" ;;
    evento-nuevo)  echo "Crear evento (/eventos/nuevo)" ;;
    evento-editar) echo "Editar evento (/eventos/:id/editar)" ;;
    expositores)   echo "Gestión de expositores (/expositores)" ;;
  esac
}

listar() {
  local i=1
  for p in "${PANTALLAS[@]}"; do
    printf "  %d) %-14s %s\n" "$i" "$p" "$(descripcion_de "$p")"
    i=$((i + 1))
  done
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

# --- Elegir pantalla ---
PANTALLA="${1:-}"

if [[ "$PANTALLA" == "--list" || "$PANTALLA" == "-l" ]]; then
  echo "Pantallas disponibles:"
  listar
  exit 0
fi

if [[ -z "$PANTALLA" ]]; then
  echo "Mockup de Eventia - elegí la pantalla a abrir:"
  listar
  read -r -p "Opción [1-${#PANTALLAS[@]}] (Enter = 1): " OPCION
  OPCION="${OPCION:-1}"
  if [[ "$OPCION" =~ ^[0-9]+$ ]] && (( OPCION >= 1 && OPCION <= ${#PANTALLAS[@]} )); then
    PANTALLA="${PANTALLAS[$((OPCION - 1))]}"
  else
    PANTALLA="$OPCION"
  fi
fi

if ! PAGINA="$(pagina_de "$PANTALLA")"; then
  echo "Pantalla desconocida: '$PANTALLA'"
  echo "Pantallas disponibles:"
  listar
  exit 1
fi

if [[ ! -f "$MOCKUP_DIR/index.html" ]]; then
  echo "No se encontró la carpeta del mockup en $MOCKUP_DIR"
  exit 1
fi

# --- Sin Python: abrir el archivo directamente ---
if ! command -v python3 >/dev/null 2>&1; then
  # Al abrir un archivo local no se puede pasar ?id=, así que
  # evento-editar se abre en modo creación.
  echo "==> python3 no está disponible; abriendo el archivo sin servidor."
  trap - EXIT INT TERM
  open_browser "$MOCKUP_DIR/${PAGINA%%\?*}"
  exit 0
fi

# --- Levantar servidor ---
BASE_URL="http://localhost:$MOCKUP_PORT"
if curl --silent --fail --output /dev/null "$BASE_URL/index.html" 2>/dev/null; then
  echo "==> Ya hay un servidor en $BASE_URL; se reutiliza."
else
  echo "==> Sirviendo mockup/ en $BASE_URL ..."
  python3 -m http.server "$MOCKUP_PORT" --bind 127.0.0.1 --directory "$MOCKUP_DIR" >/dev/null 2>&1 &
  SERVER_PID=$!
  if ! wait_for_url "$BASE_URL/index.html" 10; then
    echo "El servidor no respondió en 10s. ¿El puerto $MOCKUP_PORT está ocupado? Probá con MOCKUP_PORT=otro."
    exit 1
  fi
fi

URL="$BASE_URL/$PAGINA"
echo "==> Abriendo $(descripcion_de "$PANTALLA"): $URL"
open_browser "$URL"

if [[ -n "$SERVER_PID" ]]; then
  echo "==> Presioná Ctrl+C para detener el servidor."
  wait "$SERVER_PID"
fi
