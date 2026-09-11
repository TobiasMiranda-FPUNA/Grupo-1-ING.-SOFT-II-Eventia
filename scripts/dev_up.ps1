<#
============================================================
dev_up.ps1
Proyecto: Eventia

Versión para PowerShell (Windows) de scripts/dev_up.sh.
Levanta el backend (FastAPI/uvicorn) y el frontend (Angular),
cada uno en su propia ventana de PowerShell (en Windows no hay
forma robusta de intercalar la salida de dos procesos con
prefijos [backend]/[frontend] como en bash), espera a que
ambos respondan, y abre el navegador automáticamente en la
app. Cerrá esta ventana o presioná Ctrl+C para detener ambos
procesos.

Uso:
  .\scripts\dev_up.ps1

Si PowerShell bloquea la ejecución de scripts, corré antes
(una sola vez, por usuario):
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Requisitos previos:
  - backend\.venv creado con las dependencias instaladas
    (ver README: python -m venv .venv; .venv\Scripts\pip install -r requirements.txt).
    Si no existe, este script lo crea automáticamente.
  - backend\.env presente (se copia de .env.example si falta).
  - Postgres corriendo con la base cargada (ver scripts/setup_local_db.ps1).

Variables de entorno opcionales:
  BACKEND_PORT=8000
  FRONTEND_PORT=4200   (si se cambia, actualizar también el CORS
                         allow_origins en backend/app/main.py)
============================================================
#>

$ErrorActionPreference = "Stop"

$BackendPort  = if ($env:BACKEND_PORT)  { $env:BACKEND_PORT }  else { "8000" }
$FrontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "4200" }

$ScriptDir   = $PSScriptRoot
$RepoRoot    = Split-Path -Parent $ScriptDir
$BackendDir  = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

$BackendProcess = $null
$FrontendProcess = $null

# ------------------------------------------------------------
# Windows no tiene un equivalente directo a "kill $PID" que
# también mate a los hijos (uvicorn --reload y ng serve lanzan
# procesos hijos). Se recorre el árbol de procesos con WMI/CIM.
# ------------------------------------------------------------
function Stop-ProcessTree {
    param([int]$ProcessId)
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId $child.ProcessId
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Invoke-Cleanup {
    Write-Host ""
    Write-Host "Deteniendo backend y frontend..."
    if ($BackendProcess)  { Stop-ProcessTree -ProcessId $BackendProcess.Id }
    if ($FrontendProcess) { Stop-ProcessTree -ProcessId $FrontendProcess.Id }
}

function Wait-ForUrl {
    param([string]$Url, [int]$TimeoutSeconds)
    $waited = 0
    while ($true) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds 1
            $waited++
            if ($waited -ge $TimeoutSeconds) { return $false }
        }
    }
}

try {
    # --- Preparar backend ---
    $uvicornExe = Join-Path $BackendDir ".venv\Scripts\uvicorn.exe"
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

    # --- Preparar frontend ---
    $nodeModules = Join-Path $FrontendDir "node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Host "==> No se encontró frontend\node_modules, instalando dependencias (npm install)..."
        Push-Location $FrontendDir
        try { npm install } finally { Pop-Location }
    }

    # --- Levantar backend (en su propia ventana) ---
    Write-Host "==> Iniciando backend en http://localhost:$BackendPort ..."
    $backendCmd = "-NoExit -Command `"Set-Location '$BackendDir'; & '$uvicornExe' app.main:app --reload --port $BackendPort`""
    $BackendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $backendCmd -WindowStyle Normal -PassThru

    if (-not (Wait-ForUrl -Url "http://localhost:$BackendPort/health" -TimeoutSeconds 30)) {
        throw "El backend no respondió en 30s. Revisá la ventana del backend."
    }
    Write-Host "==> Backend listo."

    # --- Levantar frontend (en su propia ventana) ---
    Write-Host "==> Iniciando frontend en http://localhost:$FrontendPort ..."
    $ngCmd = Join-Path $FrontendDir "node_modules\.bin\ng.cmd"
    $frontendCmd = "-NoExit -Command `"Set-Location '$FrontendDir'; & '$ngCmd' serve --port $FrontendPort`""
    $FrontendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $frontendCmd -WindowStyle Normal -PassThru

    if (-not (Wait-ForUrl -Url "http://localhost:$FrontendPort" -TimeoutSeconds 120)) {
        throw "El frontend no respondió en 120s. Revisá la ventana del frontend."
    }
    Write-Host "==> Frontend listo."

    Start-Process "http://localhost:$FrontendPort"

    Write-Host ""
    Write-Host "Backend:  http://localhost:$BackendPort/docs"
    Write-Host "Frontend: http://localhost:$FrontendPort"
    Write-Host "Cerrá esta ventana o presioná Ctrl+C para detener ambos."
    Write-Host ""

    while ($true) {
        Start-Sleep -Seconds 1
        if ($BackendProcess.HasExited -or $FrontendProcess.HasExited) {
            Write-Host "Uno de los procesos terminó inesperadamente."
            break
        }
    }
} finally {
    Invoke-Cleanup
}
