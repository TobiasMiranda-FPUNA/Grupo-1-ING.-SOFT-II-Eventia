<#
============================================================
up.ps1
Proyecto: Eventia

Versión para PowerShell (Windows) de scripts/up.sh.
Punto de entrada único para levantar el proyecto completo
(backend FastAPI + frontend Angular), en dos modos:

  local   -> todo en localhost, igual que dev_up.ps1.
  remote  -> además abre un túnel público (cloudflared o ngrok)
             hacia el frontend, para que otras personas entren
             desde internet (demo al profe, compañeros, celular).

En modo remote solo se expone el frontend. El dev server de
Angular reenvía /api, /docs y /health al backend local mediante
frontend\proxy.conf.mjs, así que no hace falta tocar el CORS ni
exponer el puerto del backend.

Backend, frontend y túnel se abren cada uno en su propia ventana
de PowerShell. Cerrá esta ventana o presioná Ctrl+C para detener
todo.

Uso:
  .\scripts\up.ps1            # modo local (por defecto)
  .\scripts\up.ps1 local
  .\scripts\up.ps1 remote

Si PowerShell bloquea la ejecución de scripts, corré antes
(una sola vez, por usuario):
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Requisitos previos:
  - Python, Node.js/npm y Postgres con la base cargada
    (ver scripts/setup_local_db.ps1).
  - Solo modo remote: cloudflared (recomendado, no requiere
    cuenta) o ngrok (requiere "ngrok config add-authtoken ...").
      winget install --id Cloudflare.cloudflared

Variables de entorno opcionales:
  BACKEND_PORT=8000
  FRONTEND_PORT=4200
  TUNNEL=cloudflared|ngrok|vscode   (por defecto, el primero que esté instalado;
                                    vscode = no abre túnel, se reenvía el puerto
                                    desde la pestaña "Puertos" de VS Code)
  NO_BROWSER=1               (no abrir el navegador automáticamente)
============================================================
#>

param(
    [ValidateSet("local", "remote")]
    [string]$Mode = "local"
)

$ErrorActionPreference = "Stop"

$BackendPort  = if ($env:BACKEND_PORT)  { $env:BACKEND_PORT }  else { "8000" }
$FrontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "4200" }
$Tunnel       = $env:TUNNEL
# proxy.conf.mjs lee esta variable para saber a qué puerto reenviar.
$env:BACKEND_PORT = $BackendPort

$ScriptDir   = $PSScriptRoot
$RepoRoot    = Split-Path -Parent $ScriptDir
$BackendDir  = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

$BackendProcess  = $null
$FrontendProcess = $null
$TunnelProcess   = $null
$TunnelLog       = $null

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
    Write-Host "Deteniendo procesos..."
    if ($TunnelProcess)   { Stop-ProcessTree -ProcessId $TunnelProcess.Id }
    if ($FrontendProcess) { Stop-ProcessTree -ProcessId $FrontendProcess.Id }
    if ($BackendProcess)  { Stop-ProcessTree -ProcessId $BackendProcess.Id }
    if ($TunnelLog) {
        Remove-Item $TunnelLog, "$TunnelLog.out" -ErrorAction SilentlyContinue
    }
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

function Test-PortInUse {
    param([string]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return [bool]$conn
}

function Open-Browser {
    param([string]$Url)
    if (-not $env:NO_BROWSER) { Start-Process $Url }
}

try {
    # --- Elegir herramienta de túnel (solo modo remote) ---
    if ($Mode -eq "remote") {
        if (-not $Tunnel) {
            if (Get-Command cloudflared -ErrorAction SilentlyContinue) { $Tunnel = "cloudflared" }
            elseif (Get-Command ngrok -ErrorAction SilentlyContinue)   { $Tunnel = "ngrok" }
        }
        if ($Tunnel -ne "vscode" -and (-not $Tunnel -or -not (Get-Command $Tunnel -ErrorAction SilentlyContinue)))) {
            throw "Modo remote: no se encontró cloudflared ni ngrok. Instalá uno, por ejemplo: winget install --id Cloudflare.cloudflared"
        }
    }

    foreach ($port in @($BackendPort, $FrontendPort)) {
        if (Test-PortInUse -Port $port) {
            throw "El puerto $port ya está en uso. Cerrá el proceso que lo ocupa o cambiá BACKEND_PORT/FRONTEND_PORT."
        }
    }

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
    $backendCmd = "-NoExit -Command `"Set-Location '$BackendDir'; & '$uvicornExe' app.main:app --reload --host 127.0.0.1 --port $BackendPort`""
    $BackendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $backendCmd -WindowStyle Normal -PassThru

    if (-not (Wait-ForUrl -Url "http://localhost:$BackendPort/health" -TimeoutSeconds 30)) {
        throw "El backend no respondió en 30s. Revisá la ventana del backend (¿Postgres está corriendo?)."
    }
    Write-Host "==> Backend listo."

    # --- Levantar frontend (en su propia ventana) ---
    $ngConfig = if ($Mode -eq "remote") { "remote" } else { "development" }
    Write-Host "==> Iniciando frontend ($ngConfig) en http://localhost:$FrontendPort ..."
    $ngCmd = Join-Path $FrontendDir "node_modules\.bin\ng.cmd"
    $frontendCmd = "-NoExit -Command `"`$env:BACKEND_PORT='$BackendPort'; Set-Location '$FrontendDir'; & '$ngCmd' serve --configuration $ngConfig --port $FrontendPort`""
    $FrontendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $frontendCmd -WindowStyle Normal -PassThru

    if (-not (Wait-ForUrl -Url "http://localhost:$FrontendPort" -TimeoutSeconds 120)) {
        throw "El frontend no respondió en 120s. Revisá la ventana del frontend."
    }
    Write-Host "==> Frontend listo."

    $PublicUrl = $null

    # --- Abrir túnel (solo modo remote) ---
    if ($Mode -eq "remote" -and $Tunnel -ne "vscode") {
        Write-Host "==> Abriendo túnel con $Tunnel ..."
        $TunnelLog = [System.IO.Path]::GetTempFileName()

        if ($Tunnel -eq "cloudflared") {
            $TunnelProcess = Start-Process -FilePath "cloudflared" `
                -ArgumentList "tunnel --no-autoupdate --url http://localhost:$FrontendPort" `
                -RedirectStandardError $TunnelLog -RedirectStandardOutput "$TunnelLog.out" `
                -WindowStyle Hidden -PassThru
            for ($i = 0; $i -lt 30 -and -not $PublicUrl; $i++) {
                Start-Sleep -Seconds 1
                # Se excluye api.trycloudflare.com, que aparece en los mensajes de error.
                $match = Select-String -Path $TunnelLog -Pattern 'https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($match) { $PublicUrl = $match.Matches[0].Value }
                if ($TunnelProcess.HasExited) { break }
                if (Select-String -Path $TunnelLog -Pattern 'failed to request quick Tunnel' -Quiet -ErrorAction SilentlyContinue) { break }
            }
        } else {
            $TunnelProcess = Start-Process -FilePath "ngrok" `
                -ArgumentList "http $FrontendPort --log=stdout" `
                -RedirectStandardOutput $TunnelLog -RedirectStandardError "$TunnelLog.out" `
                -WindowStyle Hidden -PassThru
            for ($i = 0; $i -lt 30 -and -not $PublicUrl; $i++) {
                Start-Sleep -Seconds 1
                try {
                    $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 2
                    $PublicUrl = ($tunnels.tunnels | Where-Object { $_.public_url -like "https://*" } | Select-Object -First 1).public_url
                } catch { }
                if ($TunnelProcess.HasExited) { break }
            }
        }

        if (-not $PublicUrl) {
            Get-Content $TunnelLog, "$TunnelLog.out" -ErrorAction SilentlyContinue | Write-Host
            if (Select-String -Path $TunnelLog -Pattern 'no such host' -Quiet -ErrorAction SilentlyContinue) {
                Write-Host ""
                Write-Host "El DNS de tu red no resuelve trycloudflare.com (algunos routers/ISP lo bloquean)."
                Write-Host "Cambiá el DNS del adaptador a 1.1.1.1 / 8.8.8.8, o usá ngrok: `$env:TUNNEL='ngrok'"
            }
            throw "No se pudo obtener la URL pública del túnel (log de $Tunnel arriba)."
        }
        Write-Host "==> Túnel listo."
    }

    Write-Host ""
    if ($Mode -eq "remote" -and $Tunnel -eq "vscode") {
        Write-Host "Modo remote sin túnel propio. En VS Code abrí la pestaña 'Puertos',"
        Write-Host "reenviá el puerto $FrontendPort y poné su visibilidad en 'Público'."
        Write-Host "Local: http://localhost:$FrontendPort"
    } elseif ($Mode -eq "remote") {
        Open-Browser $PublicUrl
        Write-Host "URL pública (compartila): $PublicUrl"
        Write-Host "API pública (Swagger):    $PublicUrl/docs"
        Write-Host "Local:                    http://localhost:$FrontendPort"
        Write-Host ""
        Write-Host "Atención: cualquiera con la URL puede entrar mientras el script esté corriendo."
    } else {
        Open-Browser "http://localhost:$FrontendPort"
        Write-Host "Backend:  http://localhost:$BackendPort/docs"
        Write-Host "Frontend: http://localhost:$FrontendPort"
    }
    Write-Host "Cerrá esta ventana o presioná Ctrl+C para detener todo."
    Write-Host ""

    while ($true) {
        Start-Sleep -Seconds 1
        if ($BackendProcess.HasExited -or $FrontendProcess.HasExited -or ($TunnelProcess -and $TunnelProcess.HasExited)) {
            Write-Host "Uno de los procesos terminó inesperadamente."
            break
        }
    }
} finally {
    Invoke-Cleanup
}
