<#
============================================================
mockup_up.ps1
Proyecto: Eventia

Versión para PowerShell (Windows) de scripts/mockup_up.sh.
Abre en el navegador el mockup interactivo de las pantallas
(carpeta mockup\). Permite elegir la pantalla por argumento o
desde un menú, levanta un servidor HTTP local para servir la
carpeta y abre el navegador directamente en esa pantalla.
Presioná Ctrl+C para detener el servidor.

Uso:
  .\scripts\mockup_up.ps1              # menú interactivo
  .\scripts\mockup_up.ps1 <pantalla>   # abre esa pantalla
  .\scripts\mockup_up.ps1 -List        # lista las pantallas

Pantallas: todas, login, roles, eventos, evento-nuevo, evento-editar,
           expositores

Si PowerShell bloquea la ejecución de scripts, corré antes
(una sola vez, por usuario):
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Requisitos: Python 3 (python o py). Si no está, se abre el
archivo HTML directamente, sin servidor.

Variables de entorno opcionales:
  MOCKUP_PORT=4300
============================================================
#>

param(
  [string]$Pantalla = "",
  [switch]$List
)

$ErrorActionPreference = "Stop"

$MockupPort = if ($env:MOCKUP_PORT) { $env:MOCKUP_PORT } else { "4300" }
$RepoRoot   = Split-Path -Parent $PSScriptRoot
$MockupDir  = Join-Path $RepoRoot "mockup"

$Pantallas = [ordered]@{
  "todas"         = @{ Pagina = "index.html";            Desc = "Índice con todas las pantallas" }
  "login"         = @{ Pagina = "login.html";            Desc = "Login (/login)" }
  "roles"         = @{ Pagina = "roles.html";            Desc = "Administración de roles (/roles)" }
  "eventos"       = @{ Pagina = "eventos.html";          Desc = "Catálogo de eventos (/eventos)" }
  "evento-nuevo"  = @{ Pagina = "evento-form.html";      Desc = "Crear evento (/eventos/nuevo)" }
  "evento-editar" = @{ Pagina = "evento-form.html?id=1"; Desc = "Editar evento (/eventos/:id/editar)" }
  "expositores"   = @{ Pagina = "expositores.html";      Desc = "Gestión de expositores (/expositores)" }
}
$Nombres = @($Pantallas.Keys)

function Show-Pantallas {
  for ($i = 0; $i -lt $Nombres.Count; $i++) {
    "  {0}) {1,-14} {2}" -f ($i + 1), $Nombres[$i], $Pantallas[$Nombres[$i]].Desc | Write-Host
  }
}

function Test-Url($url) {
  try {
    Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 | Out-Null
    return $true
  } catch {
    return $false
  }
}

# --- Elegir pantalla ---
if ($List) {
  Write-Host "Pantallas disponibles:"
  Show-Pantallas
  exit 0
}

if (-not $Pantalla) {
  Write-Host "Mockup de Eventia - elegí la pantalla a abrir:"
  Show-Pantallas
  $opcion = Read-Host "Opción [1-$($Nombres.Count)] (Enter = 1)"
  if (-not $opcion) { $opcion = "1" }
  if ($opcion -match '^\d+$' -and [int]$opcion -ge 1 -and [int]$opcion -le $Nombres.Count) {
    $Pantalla = $Nombres[[int]$opcion - 1]
  } else {
    $Pantalla = $opcion
  }
}

if (-not $Pantallas.Contains($Pantalla)) {
  Write-Host "Pantalla desconocida: '$Pantalla'"
  Write-Host "Pantallas disponibles:"
  Show-Pantallas
  exit 1
}

if (-not (Test-Path (Join-Path $MockupDir "index.html"))) {
  Write-Host "No se encontró la carpeta del mockup en $MockupDir"
  exit 1
}

$Pagina = $Pantallas[$Pantalla].Pagina
$Desc   = $Pantallas[$Pantalla].Desc

# --- Buscar Python ---
$PythonCmd = $null
$PythonArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
  $PythonCmd = "py"; $PythonArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $PythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
  $PythonCmd = "python3"
}

if (-not $PythonCmd) {
  Write-Host "==> Python no está disponible; abriendo el archivo sin servidor."
  $archivo = Join-Path $MockupDir ($Pagina -replace '\?.*$', '')
  $query = if ($Pagina -match '\?') { $Pagina -replace '^[^?]*', '' } else { "" }
  Start-Process ("file:///" + ($archivo -replace '\\', '/') + $query)
  exit 0
}

# --- Levantar servidor ---
$BaseUrl = "http://localhost:$MockupPort"
$Server = $null

if (Test-Url "$BaseUrl/index.html") {
  Write-Host "==> Ya hay un servidor en $BaseUrl; se reutiliza."
} else {
  Write-Host "==> Sirviendo mockup\ en $BaseUrl ..."
  $Server = Start-Process -FilePath $PythonCmd `
    -ArgumentList ($PythonArgs + @("-m", "http.server", $MockupPort, "--bind", "127.0.0.1", "--directory", "`"$MockupDir`"")) `
    -WindowStyle Hidden -PassThru

  $esperado = 0
  while (-not (Test-Url "$BaseUrl/index.html")) {
    Start-Sleep -Seconds 1
    $esperado++
    if ($esperado -ge 10) {
      Write-Host "El servidor no respondió en 10s. ¿El puerto $MockupPort está ocupado? Probá con `$env:MOCKUP_PORT=otro."
      if ($Server -and -not $Server.HasExited) { Stop-Process -Id $Server.Id -Force }
      exit 1
    }
  }
}

$Url = "$BaseUrl/$Pagina"
Write-Host "==> Abriendo ${Desc}: $Url"
Start-Process $Url

if ($Server) {
  Write-Host "==> Presioná Ctrl+C para detener el servidor."
  try {
    while (-not $Server.HasExited) { Start-Sleep -Seconds 1 }
  } finally {
    if (-not $Server.HasExited) {
      Write-Host ""
      Write-Host "Deteniendo servidor del mockup..."
      Stop-Process -Id $Server.Id -Force
    }
  }
}
