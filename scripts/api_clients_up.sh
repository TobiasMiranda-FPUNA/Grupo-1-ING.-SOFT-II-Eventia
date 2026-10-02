#!/usr/bin/env bash
# ============================================================
# api_clients_up.sh
# Proyecto: Eventia
#
# Levanta el backend con todos los endpoints implementados y
# deja listos los archivos para probarlos desde un cliente de
# API (Postman, Insomnia, Bruno, Thunder Client, etc.):
#   1. Prepara backend/.venv y backend/.env si faltan.
#   2. Regenera backend/docs/openapi.json.
#   3. Genera backend/docs/eventia.postman_collection.json
#      (con login que guarda el token automáticamente).
#   4. Levanta el backend (si no está corriendo ya).
#   5. Verifica la conexión a la base con un login de prueba.
# Con Ctrl+C se detiene el backend (solo si lo levantó este script).
#
# Uso:
#   ./scripts/api_clients_up.sh
#
# Requisitos previos:
#   - Postgres corriendo con la base cargada (ver scripts/setup_local_db.sh).
#
# Variables de entorno opcionales:
#   BACKEND_PORT=8000
# ============================================================

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
export BACKEND_PORT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"

BASE_URL="http://localhost:$BACKEND_PORT"
HEALTH_URL="$BASE_URL/health"
COLLECTION_FILE="$BACKEND_DIR/docs/eventia.postman_collection.json"
OPENAPI_FILE="$BACKEND_DIR/docs/openapi.json"

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

# Hace un login con el usuario de ejemplo para confirmar que la API llega
# a la base de datos (sql/cargar_datos_ejemplo.sql).
check_database() {
  local code
  code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
    -X POST "$BASE_URL/api/v1/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"admin@eventia.test","password":"Admin123!"}' || true)"
  case "$code" in
    200) echo "==> Base de datos OK (login de admin@eventia.test exitoso)." ;;
    401) echo "==> Aviso: la API responde pero admin@eventia.test no existe. Cargá sql/cargar_datos_ejemplo.sql." ;;
    *)   echo "==> Aviso: el login de prueba respondió HTTP $code. ¿Está Postgres corriendo? (ver scripts/setup_local_db.sh)" ;;
  esac
}

print_summary() {
  local total
  total="$(grep -c '"method"' "$COLLECTION_FILE" || true)"
  cat <<EOF

============================================================
 Eventia API corriendo en: $BASE_URL
============================================================
 Importar en tu cliente de API (cualquiera de estas opciones):

  Postman / Insomnia / Bruno (colección, recomendado):
    $COLLECTION_FILE
    -> Ejecutá primero "Autenticación > Login como ..." y el
       token queda guardado en {{token}} para el resto.

  OpenAPI (cualquier cliente, desde archivo o URL):
    $OPENAPI_FILE
    $BASE_URL/openapi.json

  Swagger en el navegador: $BASE_URL/docs

 Usuarios de ejemplo:
    admin@eventia.test        / Admin123!        (roles)
    organizador@eventia.test  / Organizador123!  (eventos, actividades, conferencistas)

 Requests en la colección: $total
============================================================
EOF
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

# --- Generar OpenAPI y colección ---
echo "==> Regenerando backend/docs/openapi.json ..."
(cd "$BACKEND_DIR" && .venv/bin/python docs/generate_openapi.py)
echo "==> Generando colección de Postman/Insomnia ..."
(cd "$BACKEND_DIR" && .venv/bin/python docs/generate_postman_collection.py)

# --- Levantar backend (si no está corriendo) ---
if curl --silent --fail --output /dev/null "$HEALTH_URL"; then
  echo "==> El backend ya está corriendo en $BASE_URL"
  check_database
  print_summary
  exit 0
fi

echo "==> Iniciando backend en $BASE_URL ..."
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

check_database
print_summary
echo "Ctrl+C para detener el backend."

wait "$BACKEND_PID"
