#!/usr/bin/env bash
# ============================================================
# setup_local_db.sh
# Proyecto: Eventia
#
# Crea (si no existen) el rol y la base de datos locales que
# espera backend/.env.example, y aplica todos los scripts de
# sql/ en el orden correcto. Es seguro volver a ejecutarlo:
# todas las tablas usan IF NOT EXISTS y todas las cargas de
# datos usan ON CONFLICT / WHERE NOT EXISTS.
#
# Uso:
#   ./scripts/setup_local_db.sh
#
# Variables de entorno opcionales (con sus valores por defecto,
# tomados de backend/.env.example):
#   DB_HOST=localhost
#   DB_PORT=5432
#   DB_NAME=eventia
#   DB_USER=eventia
#   DB_PASSWORD=eventia
#   PG_SUPERUSER=postgres           # rol admin usado solo para crear el rol/DB
#   PGSUPERUSER_PASSWORD=           # si no se define, se pide por teclado
# ============================================================

set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-eventia}"
DB_USER="${DB_USER:-eventia}"
DB_PASSWORD="${DB_PASSWORD:-eventia}"
PG_SUPERUSER="${PG_SUPERUSER:-postgres}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SQL_DIR="$REPO_ROOT/sql"

# Orden de ejecución: primero las tablas, después las cargas de
# datos (los catálogos antes que los datos de ejemplo, porque
# estos últimos dependen de ellos).
SQL_FILES=(
    "crear_usuario_rol_sistema_usuario_rol.sql"
    "crear_rol_participante_y_catalogo.sql"
    "crear_tipo_evento_evento_politica.sql"
    "crear_participante_inscripcion.sql"
    "cargar_catalogos_iniciales.sql"
    "cargar_datos_ejemplo.sql"
)

# ------------------------------------------------------------
# Ubicar psql. El instalador de EDB no lo agrega al PATH por
# defecto, así que se busca en las rutas típicas de macOS.
# ------------------------------------------------------------
find_psql() {
    if command -v psql >/dev/null 2>&1; then
        command -v psql
        return
    fi
    local candidate
    for candidate in /Library/PostgreSQL/*/bin/psql /opt/homebrew/opt/postgresql*/bin/psql /usr/local/opt/postgresql*/bin/psql; do
        if [ -x "$candidate" ]; then
            echo "$candidate"
            return
        fi
    done
    echo ""
}

PSQL="$(find_psql)"
if [ -z "$PSQL" ]; then
    echo "No se encontró psql. Instalá PostgreSQL o agregá su carpeta bin/ al PATH." >&2
    exit 1
fi
echo "Usando psql: $PSQL"

# ------------------------------------------------------------
# Contraseña del superusuario, para crear el rol y la base.
# ------------------------------------------------------------
if [ -z "${PGSUPERUSER_PASSWORD:-}" ]; then
    read -r -s -p "Contraseña del rol '$PG_SUPERUSER' de PostgreSQL: " PGSUPERUSER_PASSWORD
    echo
fi

psql_admin() {
    PGPASSWORD="$PGSUPERUSER_PASSWORD" "$PSQL" \
        -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d postgres \
        -v ON_ERROR_STOP=1 "$@"
}

psql_app() {
    PGPASSWORD="$DB_PASSWORD" "$PSQL" \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -v ON_ERROR_STOP=1 "$@"
}

# ------------------------------------------------------------
# 1) Rol de aplicación (idempotente).
# ------------------------------------------------------------
echo "Verificando rol '$DB_USER'..."
psql_admin <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;
SQL

# ------------------------------------------------------------
# 2) Base de datos (idempotente; CREATE DATABASE no admite
#    IF NOT EXISTS, así que se verifica antes).
# ------------------------------------------------------------
echo "Verificando base de datos '$DB_NAME'..."
DB_EXISTS="$(psql_admin -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'")"
if [ "$DB_EXISTS" != "1" ]; then
    psql_admin -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    echo "Base de datos '$DB_NAME' creada."
else
    echo "Base de datos '$DB_NAME' ya existe, se omite creación."
fi

# ------------------------------------------------------------
# 3) Aplicar los scripts de sql/ en orden, como el rol de la app.
# ------------------------------------------------------------
for file in "${SQL_FILES[@]}"; do
    path="$SQL_DIR/$file"
    if [ ! -f "$path" ]; then
        echo "Aviso: no se encontró $path, se omite." >&2
        continue
    fi
    echo "Aplicando $file..."
    psql_app -f "$path"
done

echo
echo "Listo. La base '$DB_NAME' está preparada en $DB_HOST:$DB_PORT."
echo "Verificá que backend/.env tenga:"
echo "  DATABASE_URL=postgresql+psycopg://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
