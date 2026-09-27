<#
============================================================
swagger_up.ps1
Proyecto: Eventia

Versión para PowerShell (Windows) de scripts/swagger_up.sh.
Abre la documentación interactiva de la API (Swagger) en un
solo paso:
  1. Prepara backend\.venv y backend\.env si faltan.
  2. Regenera backend\docs\openapi.json a partir del código.
  3. Levanta el backend (si no está corriendo ya).
  4. Abre el navegador en http://localhost:8000/api-docs/
Cerrá esta ventana o presioná Ctrl+C para detener el backend
(solo si lo levantó este script).

Uso:
  .\scripts\swagger_up.ps1

Si PowerShell bloquea la ejecución de scripts, corré antes
(una sola vez, por usuario):
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Requisitos previos:
  - Postgres corriendo con la base cargada (ver scripts/setup_local_db.ps1)
    para poder ejecutar los endpoints con "Try it out".

Variables de entorno opcionales:
  BACKEND_PORT=8000
============================================================
#>

$ErrorActionPreference = "Stop"

$BackendPort = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }

$ScriptDir  = $PSScriptRoot
$RepoRoot   = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RepoRoot "backend"

$SwaggerUrl = "http://localhost:$BackendPort/api-docs/"
$HealthUrl  = "http://localhost:$BackendPort/health"

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

    # --- Regenerar openapi.json ---
    Write-Host "==> Regenerando backend\docs\openapi.json ..."
    Push-Location $BackendDir
    try {
        & $pythonExe (Join-Path "docs" "generate_openapi.py")
        if ($LASTEXITCODE -ne 0) { throw "No se pudo generar openapi.json." }
    } finally { Pop-Location }

    # --- Levantar backend (si no está corriendo) ---
    if (Test-Url -Url $HealthUrl) {
        Write-Host "==> El backend ya está corriendo en http://localhost:$BackendPort"
        Start-Process $SwaggerUrl
        Write-Host ""
        Write-Host "Swagger: $SwaggerUrl"
        return
    }

    Write-Host "==> Iniciando backend en http://localhost:$BackendPort ..."
    $BackendProcess = Start-Process -FilePath $uvicornExe `
        -ArgumentList "app.main:app", "--reload", "--port", $BackendPort `
        -WorkingDirectory $BackendDir -NoNewWindow -PassThru

    if (-not (Wait-ForUrl -Url $HealthUrl -TimeoutSeconds 30)) {
        throw "El backend no respondió en 30s. Revisá el log del backend arriba."
    }
    Write-Host "==> Backend listo."

    Start-Process $SwaggerUrl

    Write-Host ""
    Write-Host "Swagger (docs/index.html): $SwaggerUrl"
    Write-Host "Swagger en vivo (FastAPI): http://localhost:$BackendPort/docs"
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
