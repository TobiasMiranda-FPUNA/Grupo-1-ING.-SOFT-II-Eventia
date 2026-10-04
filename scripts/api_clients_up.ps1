<#
============================================================
api_clients_up.ps1
Proyecto: Eventia

Versión para PowerShell (Windows) de scripts/api_clients_up.sh.
Levanta el backend con todos los endpoints implementados y
deja listos los archivos para probarlos desde un cliente de
API (Postman, Insomnia, Bruno, Thunder Client, etc.):
  1. Prepara backend\.venv y backend\.env si faltan.
  2. Regenera backend\docs\openapi.json.
  3. Genera backend\docs\eventia.postman_collection.json
     (con login que guarda el token automáticamente).
  4. Levanta el backend (si no está corriendo ya).
  5. Verifica la conexión a la base con un login de prueba.
Cerrá esta ventana o presioná Ctrl+C para detener el backend
(solo si lo levantó este script).

Uso:
  .\scripts\api_clients_up.ps1

Si PowerShell bloquea la ejecución de scripts, corré antes
(una sola vez, por usuario):
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Requisitos previos:
  - Postgres corriendo con la base cargada (ver scripts/setup_local_db.ps1).

Variables de entorno opcionales:
  BACKEND_PORT=8000
============================================================
#>

$ErrorActionPreference = "Stop"

$BackendPort = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }
$env:BACKEND_PORT = $BackendPort

$ScriptDir  = $PSScriptRoot
$RepoRoot   = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RepoRoot "backend"

$BaseUrl        = "http://localhost:$BackendPort"
$HealthUrl      = "$BaseUrl/health"
$CollectionFile = Join-Path $BackendDir "docs\eventia.postman_collection.json"
$OpenApiFile    = Join-Path $BackendDir "docs\openapi.json"

$BackendProcess = $null

# ------------------------------------------------------------
# uvicorn --reload lanza procesos hijos; se recorre el árbol de
# procesos con WMI/CIM para detenerlos todos (ver dev_up.ps1).
# ------------------------------------------------------------
function Stop-ProcessTree {
    param([int]$ProcessId)
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId $child.ProcessId
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Test-Url {
    param([string]$Url)
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Wait-ForUrl {
    param([string]$Url, [int]$TimeoutSeconds)
    $waited = 0
    while (-not (Test-Url -Url $Url)) {
        Start-Sleep -Seconds 1
        $waited++
        if ($waited -ge $TimeoutSeconds) { return $false }
    }
    return $true
}

# Hace un login con el usuario de ejemplo para confirmar que la API llega
# a la base de datos (sql/cargar_datos_ejemplo.sql).
function Test-Database {
    $body = '{"email":"admin@eventia.test","password":"Admin123!"}'
    try {
        Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/auth/login" `
            -ContentType "application/json" -Body $body -TimeoutSec 10 | Out-Null
        Write-Host "==> Base de datos OK (login de admin@eventia.test exitoso)."
    } catch {
        $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        if ($code -eq 401) {
            Write-Host "==> Aviso: la API responde pero admin@eventia.test no existe. Cargá sql/cargar_datos_ejemplo.sql."
        } else {
            Write-Host "==> Aviso: el login de prueba respondió HTTP $code. ¿Está Postgres corriendo? (ver scripts/setup_local_db.ps1)"
        }
    }
}

function Write-Summary {
    $total = (Select-String -Path $CollectionFile -Pattern '"method"').Count
    Write-Host ""
    Write-Host "============================================================"
    Write-Host " Eventia API corriendo en: $BaseUrl"
    Write-Host "============================================================"
    Write-Host " Importar en tu cliente de API (cualquiera de estas opciones):"
    Write-Host ""
    Write-Host "  Postman / Insomnia / Bruno (colección, recomendado):"
    Write-Host "    $CollectionFile"
    Write-Host "    -> Ejecutá primero 'Autenticación > Login como ...' y el"
    Write-Host "       token queda guardado en {{token}} para el resto."
    Write-Host ""
    Write-Host "  OpenAPI (cualquier cliente, desde archivo o URL):"
    Write-Host "    $OpenApiFile"
    Write-Host "    $BaseUrl/openapi.json"
    Write-Host ""
    Write-Host "  Swagger en el navegador: $BaseUrl/docs"
    Write-Host ""
    Write-Host " Usuarios de ejemplo:"
    Write-Host "    admin@eventia.test        / Admin123!        (roles)"
    Write-Host "    organizador@eventia.test  / Organizador123!  (eventos, actividades, conferencistas)"
    Write-Host ""
    Write-Host " Requests en la colección: $total"
    Write-Host "============================================================"
}

try {
    # --- Preparar backend ---
    $uvicornExe = Join-Path $BackendDir ".venv\Scripts\uvicorn.exe"
    $pythonExe  = Join-Path $BackendDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $uvicornExe)) {
        Write-Host "==> No se encontró backend\.venv, creándolo e instalando dependencias..."
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCmd) { $pythonCmd = Get-Command py -ErrorAction SilentlyContinue }
        if (-not $pythonCmd) { throw "No se encontró Python. Instalalo y agregalo al PATH." }
        & $pythonCmd.Source -m venv (Join-Path $BackendDir ".venv")
        & (Join-Path $BackendDir ".venv\Scripts\pip.exe") install -q -r (Join-Path $BackendDir "requirements.txt")
    }

    $envFile = Join-Path $BackendDir ".env"
    if (-not (Test-Path $envFile)) {
        Write-Host "==> No se encontró backend\.env, copiando desde .env.example..."
        Copy-Item (Join-Path $BackendDir ".env.example") $envFile
    }

    # --- Generar OpenAPI y colección ---
    Push-Location $BackendDir
    try {
        Write-Host "==> Regenerando backend\docs\openapi.json ..."
        & $pythonExe (Join-Path "docs" "generate_openapi.py")
        if ($LASTEXITCODE -ne 0) { throw "No se pudo generar openapi.json." }
        Write-Host "==> Generando colección de Postman/Insomnia ..."
        & $pythonExe (Join-Path "docs" "generate_postman_collection.py")
        if ($LASTEXITCODE -ne 0) { throw "No se pudo generar la colección." }
    } finally { Pop-Location }

    # --- Levantar backend (si no está corriendo) ---
    if (Test-Url -Url $HealthUrl) {
        Write-Host "==> El backend ya está corriendo en $BaseUrl"
        Test-Database
        Write-Summary
        return
    }

    Write-Host "==> Iniciando backend en $BaseUrl ..."
    $BackendProcess = Start-Process -FilePath $uvicornExe `
        -ArgumentList "app.main:app", "--reload", "--port", $BackendPort `
        -WorkingDirectory $BackendDir -NoNewWindow -PassThru

    if (-not (Wait-ForUrl -Url $HealthUrl -TimeoutSeconds 30)) {
        throw "El backend no respondió en 30s. Revisá el log del backend arriba."
    }
    Write-Host "==> Backend listo."

    Test-Database
    Write-Summary
    Write-Host "Cerrá esta ventana o presioná Ctrl+C para detener el backend."
    Write-Host ""

    while (-not $BackendProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
    Write-Host "El backend terminó inesperadamente."
} finally {
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        Write-Host ""
        Write-Host "Deteniendo backend..."
        Stop-ProcessTree -ProcessId $BackendProcess.Id
    }
}
