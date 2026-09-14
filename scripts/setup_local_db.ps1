<#
============================================================
setup_local_db.ps1
Proyecto: Eventia

Versión para PowerShell (Windows) de scripts/setup_local_db.sh.
Crea (si no existen) el rol y la base de datos locales que
espera backend/.env.example, y aplica todos los scripts de
sql/ en el orden correcto. Es seguro volver a ejecutarlo:
todas las tablas usan IF NOT EXISTS y todas las cargas de
datos usan ON CONFLICT / WHERE NOT EXISTS.

Uso:
  .\scripts\setup_local_db.ps1

Si PowerShell bloquea la ejecución de scripts, corré antes
(una sola vez, por usuario):
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Variables de entorno opcionales (con sus valores por defecto,
tomados de backend/.env.example):
  DB_HOST=localhost
  DB_PORT=5432
  DB_NAME=eventia
  DB_USER=eventia
  DB_PASSWORD=eventia
  PG_SUPERUSER=postgres           # rol admin usado solo para crear el rol/DB
  PGSUPERUSER_PASSWORD=           # si no se define, se pide por teclado
============================================================
#>

$ErrorActionPreference = "Stop"

$DbHost      = if ($env:DB_HOST)      { $env:DB_HOST }      else { "localhost" }
$DbPort      = if ($env:DB_PORT)      { $env:DB_PORT }      else { "5432" }
$DbName      = if ($env:DB_NAME)      { $env:DB_NAME }      else { "eventia" }
$DbUser      = if ($env:DB_USER)      { $env:DB_USER }      else { "eventia" }
$DbPassword  = if ($env:DB_PASSWORD)  { $env:DB_PASSWORD }  else { "eventia" }
$PgSuperuser = if ($env:PG_SUPERUSER) { $env:PG_SUPERUSER } else { "postgres" }

$ScriptDir = $PSScriptRoot
$RepoRoot  = Split-Path -Parent $ScriptDir
$SqlDir    = Join-Path $RepoRoot "sql"

# Orden de ejecución: primero las tablas, después las cargas de
# datos (los catálogos antes que los datos de ejemplo, porque
# estos últimos dependen de ellos).
$SqlFiles = @(
    "crear_usuario_rol_sistema_usuario_rol.sql",
    "crear_rol_participante_y_catalogo.sql",
    "crear_tipo_evento_evento_politica.sql",
    "crear_participante_inscripcion.sql",
    "cargar_catalogos_iniciales.sql",
    "cargar_datos_ejemplo.sql"
)

# ------------------------------------------------------------
# Ubicar psql. El instalador oficial de Windows no siempre lo
# agrega al PATH, así que se busca también en las rutas típicas.
# ------------------------------------------------------------
function Find-Psql {
    $cmd = Get-Command psql.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = @(
        "$env:ProgramFiles\PostgreSQL\*\bin\psql.exe",
        "${env:ProgramFiles(x86)}\PostgreSQL\*\bin\psql.exe"
    )
    foreach ($pattern in $candidates) {
        $found = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

$Psql = Find-Psql
if (-not $Psql) {
    Write-Error "No se encontró psql. Instalá PostgreSQL o agregá su carpeta bin\ al PATH."
    exit 1
}
Write-Host "Usando psql: $Psql"

# ------------------------------------------------------------
# Contraseña del superusuario, para crear el rol y la base.
# ------------------------------------------------------------
$PgSuperPassword = $env:PGSUPERUSER_PASSWORD
if (-not $PgSuperPassword) {
    $secure = Read-Host -Prompt "Contraseña del rol '$PgSuperuser' de PostgreSQL" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $PgSuperPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Invoke-PsqlAdmin {
    param([string[]]$Arguments = @())
    $env:PGPASSWORD = $PgSuperPassword
    try {
        & $Psql -h $DbHost -p $DbPort -U $PgSuperuser -d postgres -v ON_ERROR_STOP=1 @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "psql (admin) terminó con código $LASTEXITCODE"
        }
    } finally {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
}

function Invoke-PsqlAdminCapture {
    param([string[]]$Arguments = @())
    $env:PGPASSWORD = $PgSuperPassword
    try {
        $output = & $Psql -h $DbHost -p $DbPort -U $PgSuperuser -d postgres -v ON_ERROR_STOP=1 @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "psql (admin) terminó con código $LASTEXITCODE"
        }
        return ($output -join "")
    } finally {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
}

function Invoke-PsqlApp {
    param([string[]]$Arguments = @())
    $env:PGPASSWORD = $DbPassword
    try {
        & $Psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -v ON_ERROR_STOP=1 @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "psql (app) terminó con código $LASTEXITCODE"
        }
    } finally {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
}

# ------------------------------------------------------------
# 1) Rol de aplicación (idempotente).
# ------------------------------------------------------------
Write-Host "Verificando rol '$DbUser'..."
$roleSql = "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DbUser') THEN CREATE ROLE $DbUser LOGIN PASSWORD '$DbPassword'; END IF; END `$`$;"
Invoke-PsqlAdmin -Arguments @("-c", $roleSql)

# ------------------------------------------------------------
# 2) Base de datos (idempotente; CREATE DATABASE no admite
#    IF NOT EXISTS, así que se verifica antes).
# ------------------------------------------------------------
Write-Host "Verificando base de datos '$DbName'..."
$dbExists = (Invoke-PsqlAdminCapture -Arguments @("-tAc", "SELECT 1 FROM pg_database WHERE datname = '$DbName'")).Trim()
if ($dbExists -ne "1") {
    Invoke-PsqlAdmin -Arguments @("-c", "CREATE DATABASE $DbName OWNER $DbUser;")
    Write-Host "Base de datos '$DbName' creada."
} else {
    Write-Host "Base de datos '$DbName' ya existe, se omite creación."
}

# ------------------------------------------------------------
# 3) Aplicar los scripts de sql/ en orden, como el rol de la app.
# ------------------------------------------------------------
foreach ($file in $SqlFiles) {
    $path = Join-Path $SqlDir $file
    if (-not (Test-Path $path)) {
        Write-Warning "No se encontró $path, se omite."
        continue
    }
    Write-Host "Aplicando $file..."
    Invoke-PsqlApp -Arguments @("-f", $path)
}

Write-Host ""
Write-Host "Listo. La base '$DbName' está preparada en ${DbHost}:${DbPort}."
Write-Host "Verificá que backend\.env tenga:"
Write-Host "  DATABASE_URL=postgresql+psycopg://${DbUser}:${DbPassword}@${DbHost}:${DbPort}/${DbName}"
