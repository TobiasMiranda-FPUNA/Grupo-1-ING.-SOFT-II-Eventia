#!/usr/bin/env python3
# ============================================================
# test_report.py
# Proyecto: Eventia
#
# Ejecuta los tests del backend (pytest) y del frontend (Vitest
# vía "ng test"), guarda cada ejecución en un historial y genera
# un reporte HTML que se abre en el navegador:
#   - resumen de la ejecución (pasaron, fallaron, omitidos, tiempo),
#   - gráfico y tabla con TODAS las ejecuciones guardadas,
#   - detalle de cada test agrupado por archivo, con el error
#     completo de los que fallan,
#   - comparación con la ejecución anterior (nuevos fallos y
#     tests arreglados).
#
# Solo usa la librería estándar de Python (no hay que instalar nada).
# Funciona en macOS, Linux y Windows.
#
# Uso (desde la raíz del repositorio):
#   python3 scripts/test_report.py                   # backend + frontend
#   python3 scripts/test_report.py --solo backend
#   python3 scripts/test_report.py --solo frontend
#   python3 scripts/test_report.py --sin-ejecutar    # solo reabre el reporte
#   python3 scripts/test_report.py --no-abrir        # no abre el navegador
#   (en Windows: py scripts\test_report.py ...)
#
# Archivos generados (carpeta ignorada por git):
#   test-reports/index.html       reporte
#   test-reports/historial.json   todas las ejecuciones
#
# Requisitos previos:
#   - backend/.venv con las dependencias (lo crean scripts/up.sh,
#     dev_up.sh, swagger_up.sh o api_clients_up.sh).
#   - frontend/node_modules (npm install).
#   Los tests del backend usan SQLite en memoria: no hace falta
#   tener Postgres corriendo.
#
# Código de salida: 0 si todo pasó; 1 si algún test falló o
# alguna suite no se pudo ejecutar (sirve para CI).
# ============================================================

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
SALIDA_DIR = REPO_ROOT / "test-reports"
HISTORIAL = SALIDA_DIR / "historial.json"
REPORTE = SALIDA_DIR / "index.html"

# Cantidad máxima de ejecuciones que se conservan en el historial.
MAX_EJECUCIONES = 200
# Líneas finales de la salida que se guardan cuando una suite no corre.
LINEAS_SALIDA = 80

WINDOWS = os.name == "nt"
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


# ------------------------------------------------------------
# Lectura de resultados (formato JUnit XML, que generan tanto
# pytest como Vitest).
# ------------------------------------------------------------
def agrupar_backend(classname: str, name: str) -> tuple[str, str]:
    # "tests.test_asistencias" -> "tests/test_asistencias.py"
    return classname.replace(".", "/") + ".py", name


def agrupar_frontend(classname: str, name: str) -> tuple[str, str]:
    # Vitest encadena los describe con " > ": "App > should create".
    return classname, name.replace(" > ", " › ")


def leer_junit(path: Path, agrupar) -> list[dict]:
    tests = []
    for caso in ET.parse(path).getroot().iter("testcase"):
        grupo, nombre = agrupar(caso.get("classname", ""), caso.get("name", ""))
        estado, mensaje, detalle = "ok", "", ""

        for etiqueta in ("failure", "error"):
            nodo = caso.find(etiqueta)
            if nodo is not None:
                estado = "fallo"
                mensaje = nodo.get("message") or etiqueta
                detalle = (nodo.text or "").strip()
                break
        else:
            omitido = caso.find("skipped")
            if omitido is not None:
                estado = "omitido"
                mensaje = omitido.get("message", "")

        tests.append({
            "grupo": grupo,
            "nombre": nombre,
            "estado": estado,
            "duracion": float(caso.get("time") or 0),
            "mensaje": ANSI.sub("", mensaje)[:1000],
            "detalle": ANSI.sub("", detalle)[:6000],
        })
    return tests


# ------------------------------------------------------------
# Ejecución de cada suite.
# ------------------------------------------------------------
def ejecutar_suite(nombre, herramienta, comando, cwd, xml, agrupar, env=None) -> dict:
    print(f"==> {nombre} ({herramienta}) ...", flush=True)
    suite = {"nombre": nombre, "herramienta": herramienta, "tests": [], "salida": ""}
    inicio = time.monotonic()
    try:
        proceso = subprocess.run(
            comando,
            cwd=cwd,
            env={**os.environ, **(env or {})},
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        codigo = proceso.returncode
        salida = ANSI.sub("", proceso.stdout + proceso.stderr)
    except OSError as error:
        codigo, salida = -1, f"No se pudo ejecutar {comando[0]}: {error}"
    suite["duracion"] = round(time.monotonic() - inicio, 2)

    if xml.exists() and xml.stat().st_size > 0:
        try:
            suite["tests"] = leer_junit(xml, agrupar)
        except ET.ParseError as error:
            salida += f"\n\nNo se pudo leer el resultado ({xml.name}): {error}"

    hay_fallos = any(t["estado"] == "fallo" for t in suite["tests"])
    if not suite["tests"] or (codigo != 0 and not hay_fallos):
        # La suite no llegó a ejecutarse (error de compilación, dependencias
        # faltantes, etc.): se guarda el final de la salida para verlo.
        suite["estado"] = "error"
        lineas = [l for l in salida.strip().splitlines() if not l.startswith("npm notice")]
        suite["salida"] = "\n".join(lineas[-LINEAS_SALIDA:])
    else:
        suite["estado"] = "fallo" if hay_fallos else "ok"

    cuenta = {e: sum(1 for t in suite["tests"] if t["estado"] == e) for e in ("ok", "fallo", "omitido")}
    if suite["estado"] == "error":
        print(f"    ERROR: la suite no se pudo ejecutar ({suite['duracion']} s). Ver detalle en el reporte.")
    else:
        print(
            f"    {cuenta['ok']} pasaron · {cuenta['fallo']} fallaron · "
            f"{cuenta['omitido']} omitidos · {suite['duracion']} s"
        )
    return suite


def python_backend() -> Path | None:
    venv = BACKEND_DIR / ".venv" / ("Scripts/python.exe" if WINDOWS else "bin/python")
    return venv if venv.exists() else None


def suite_backend(tmp: Path) -> dict:
    python = python_backend()
    if python is None:
        return suite_no_disponible(
            "Backend", "pytest",
            "No se encontró backend/.venv. Crealo con cualquiera de los scripts de "
            "arranque (por ejemplo scripts/api_clients_up.sh) o con:\n"
            "  python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt",
        )
    xml = tmp / "backend.xml"
    return ejecutar_suite(
        "Backend", "pytest",
        [str(python), "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"],
        BACKEND_DIR, xml, agrupar_backend,
        # Los tests usan SQLite en memoria (ver README, sección Pruebas).
        env={"DATABASE_URL": "sqlite:///:memory:"},
    )


def suite_frontend(tmp: Path) -> dict:
    npx = shutil.which("npx")
    if npx is None:
        return suite_no_disponible("Frontend", "vitest", "No se encontró npx. Instalá Node.js.")
    if not (FRONTEND_DIR / "node_modules").exists():
        return suite_no_disponible(
            "Frontend", "vitest",
            "No se encontró frontend/node_modules. Ejecutá 'npm install' dentro de frontend/.",
        )
    xml = tmp / "frontend.xml"
    return ejecutar_suite(
        "Frontend", "vitest",
        [npx, "ng", "test", "--watch=false", "--reporters=junit", f"--output-file={xml}"],
        FRONTEND_DIR, xml, agrupar_frontend,
        # Sin el aviso de "nueva versión de npm", que tapa los errores reales.
        env={"NPM_CONFIG_UPDATE_NOTIFIER": "false"},
    )


def suite_no_disponible(nombre: str, herramienta: str, motivo: str) -> dict:
    print(f"==> {nombre} ({herramienta}): {motivo.splitlines()[0]}")
    return {
        "nombre": nombre, "herramienta": herramienta, "estado": "error",
        "duracion": 0, "tests": [], "salida": motivo,
    }


def info_git() -> dict:
    def git(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""

    return {
        "rama": git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": git("rev-parse", "--short", "HEAD"),
        "cambios_sin_commit": bool(git("status", "--porcelain")),
    }


# ------------------------------------------------------------
# Historial.
# ------------------------------------------------------------
def leer_historial() -> list[dict]:
    if not HISTORIAL.exists():
        return []
    try:
        return json.loads(HISTORIAL.read_text(encoding="utf-8"))["ejecuciones"]
    except (ValueError, KeyError) as error:
        respaldo = HISTORIAL.with_suffix(f".roto-{int(time.time())}.json")
        HISTORIAL.rename(respaldo)
        print(f"Aviso: el historial estaba dañado ({error}); se movió a {respaldo.name}.")
        return []


def guardar_historial(ejecuciones: list[dict]) -> None:
    SALIDA_DIR.mkdir(exist_ok=True)
    temporal = HISTORIAL.with_suffix(".tmp")
    temporal.write_text(
        json.dumps({"ejecuciones": ejecuciones[-MAX_EJECUCIONES:]}, ensure_ascii=False),
        encoding="utf-8",
    )
    temporal.replace(HISTORIAL)


# ------------------------------------------------------------
# Reporte HTML (autocontenido: datos, estilos y script en el
# mismo archivo, sin dependencias externas).
# ------------------------------------------------------------
def generar_reporte(ejecuciones: list[dict]) -> None:
    datos = json.dumps({"ejecuciones": ejecuciones}, ensure_ascii=False).replace("</", "<\\/")
    SALIDA_DIR.mkdir(exist_ok=True)
    REPORTE.write_text(PLANTILLA.replace("__DATOS__", datos), encoding="utf-8")


PLANTILLA = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Eventia · Tests</title>
<style>
:root {
  --bg: #f5f7fb; --card: #ffffff; --border: #e5e7eb; --text: #172033; --muted: #667085;
  --soft: #f2f4f7; --accent: #2563eb;
  --ok: #12b76a; --ok-bg: #ecfdf3; --ok-text: #067647;
  --fail: #f04438; --fail-bg: #fef3f2; --fail-text: #b42318;
  --skip: #98a2b3; --warn-bg: #fffaeb; --warn-text: #b54708;
  --code-bg: #0f172a; --code-text: #e2e8f0;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0b1120; --card: #111827; --border: #1f2937; --text: #e5e7eb; --muted: #9ca3af;
    --soft: #1f2937; --accent: #60a5fa;
    --ok-bg: #052e1c; --ok-text: #6ce9a6; --fail-bg: #3b0d0c; --fail-text: #fda29b;
    --warn-bg: #3a2405; --warn-text: #fec84b; --code-bg: #020617;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 15px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }
main { max-width: 1180px; margin: 0 auto; padding: 28px 20px 60px; }
header { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
.eyebrow { font-size: .75rem; font-weight: 800; letter-spacing: .11em; color: var(--accent); }
h1 { margin: 4px 0; font-size: 1.8rem; }
h2 { font-size: 1.05rem; margin: 0 0 12px; }
.muted { color: var(--muted); }
select, input[type=search] { font: inherit; color: var(--text); background: var(--card); border: 1px solid var(--border); border-radius: 9px; padding: 9px 11px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 18px; margin-bottom: 16px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px; }
.metric { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 14px 16px; }
.metric b { display: block; font-size: 1.9rem; line-height: 1.1; font-variant-numeric: tabular-nums; }
.metric span { font-size: .85rem; color: var(--muted); }
.metric.ok b { color: var(--ok-text); } .metric.fallo b { color: var(--fail-text); }
.banner { border-radius: 12px; padding: 12px 16px; font-weight: 700; margin-bottom: 16px; }
.banner.ok { background: var(--ok-bg); color: var(--ok-text); }
.banner.fallo, .banner.error { background: var(--fail-bg); color: var(--fail-text); }
.badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: .75rem; font-weight: 800; white-space: nowrap; }
.badge.ok { background: var(--ok-bg); color: var(--ok-text); }
.badge.fallo, .badge.error, .badge.nuevo { background: var(--fail-bg); color: var(--fail-text); }
.badge.omitido { background: var(--soft); color: var(--muted); }
.badge.arreglado { background: var(--ok-bg); color: var(--ok-text); }
.chart { width: 100%; height: 150px; display: block; }
.chart rect.bar { cursor: pointer; }
.chart .sel { fill: none; stroke: var(--accent); stroke-width: 2; }
.leyenda { display: flex; gap: 14px; font-size: .8rem; color: var(--muted); margin-top: 6px; flex-wrap: wrap; }
.leyenda i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
.tabla-wrap { max-height: 320px; overflow: auto; border: 1px solid var(--border); border-radius: 10px; }
table { width: 100%; border-collapse: collapse; font-size: .88rem; }
th, td { padding: 8px 12px; border-bottom: 1px solid var(--border); text-align: left; white-space: nowrap; }
th { position: sticky; top: 0; background: var(--soft); font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
tbody tr { cursor: pointer; } tbody tr:hover { background: var(--soft); }
tbody tr.sel { background: color-mix(in srgb, var(--accent) 14%, transparent); }
.toolbar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
.toolbar input { flex: 1; min-width: 200px; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.chips button { font: inherit; font-weight: 700; font-size: .85rem; border: 1px solid var(--border); background: var(--card); color: var(--text); border-radius: 999px; padding: 6px 12px; cursor: pointer; }
.chips button.on { background: var(--accent); border-color: var(--accent); color: #fff; }
.suite-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.suite-head h2 { margin: 0; }
.barra { height: 8px; background: var(--soft); border-radius: 999px; overflow: hidden; display: flex; margin-bottom: 12px; }
.barra .ok { background: var(--ok); } .barra .fallo { background: var(--fail); } .barra .omitido { background: var(--skip); }
details { border: 1px solid var(--border); border-radius: 10px; margin-bottom: 8px; overflow: hidden; }
summary { list-style: none; cursor: pointer; padding: 10px 14px; display: flex; justify-content: space-between; gap: 12px; align-items: center; background: var(--soft); }
summary::-webkit-details-marker { display: none; }
summary .archivo { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .85rem; overflow: hidden; text-overflow: ellipsis; }
summary .archivo::before { content: "▸ "; color: var(--muted); }
details[open] summary .archivo::before { content: "▾ "; }
.test { display: grid; grid-template-columns: 22px 1fr auto; gap: 8px; padding: 8px 14px; border-top: 1px solid var(--border); align-items: start; }
.test .icono { font-weight: 900; text-align: center; }
.test.ok .icono { color: var(--ok); } .test.fallo .icono { color: var(--fail); } .test.omitido .icono { color: var(--skip); }
.test .nombre { overflow-wrap: anywhere; }
.test .t { color: var(--muted); font-size: .8rem; font-variant-numeric: tabular-nums; }
.test.fallo { background: var(--fail-bg); }
pre { margin: 8px 0 0; padding: 12px; background: var(--code-bg); color: var(--code-text); border-radius: 8px; overflow: auto; max-height: 360px; font-size: .78rem; line-height: 1.5; white-space: pre-wrap; grid-column: 2 / -1; }
.salida { white-space: pre-wrap; }
.vacio { text-align: center; color: var(--muted); padding: 24px; }
@media (max-width: 640px) {
  main { padding: 18px 12px 50px; } h1 { font-size: 1.4rem; }
  th:nth-child(2), td:nth-child(2) { display: none; }
}
</style>
</head>
<body>
<main id="app"></main>
<script id="datos" type="application/json">__DATOS__</script>
<script>
const EJECUCIONES = JSON.parse(document.getElementById('datos').textContent).ejecuciones;
const estado = { indice: EJECUCIONES.length - 1, filtro: 'todos', busqueda: '' };
const app = document.getElementById('app');

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const seg = s => s < 1 ? `${Math.round(s * 1000)} ms` : `${s.toFixed(s < 10 ? 2 : 1)} s`;
const fecha = iso => new Date(iso).toLocaleString('es', { dateStyle: 'short', timeStyle: 'medium' });
const clave = (suite, t) => `${suite}|${t.grupo}|${t.nombre}`;

function totales(ej) {
  const r = { total: 0, ok: 0, fallo: 0, omitido: 0, duracion: 0, error: false };
  for (const s of ej.suites) {
    r.duracion += s.duracion;
    if (s.estado === 'error') r.error = true;
    for (const t of s.tests) { r.total++; r[t.estado]++; }
  }
  return r;
}
const estadoDe = ej => { const t = totales(ej); return t.error ? 'error' : t.fallo ? 'fallo' : 'ok'; };
const ETIQUETA = { ok: 'OK', fallo: 'Con fallos', error: 'Error', omitido: 'Omitido' };

// Compara con la ejecución anterior que haya corrido la misma suite.
function cambios(indice) {
  const nuevos = new Set(), arreglados = new Set();
  const ej = EJECUCIONES[indice];
  for (const s of ej.suites) {
    let previa;
    for (let i = indice - 1; i >= 0 && !previa; i--) {
      previa = EJECUCIONES[i].suites.find(p => p.nombre === s.nombre && p.estado !== 'error');
    }
    if (!previa) continue;
    const antes = new Map(previa.tests.map(t => [clave(s.nombre, t), t.estado]));
    for (const t of s.tests) {
      const k = clave(s.nombre, t), anterior = antes.get(k);
      if (t.estado === 'fallo' && anterior !== 'fallo') nuevos.add(k);
      if (t.estado === 'ok' && anterior === 'fallo') arreglados.add(k);
    }
  }
  return { nuevos, arreglados };
}

function grafico() {
  const visibles = EJECUCIONES.map((ej, i) => [ej, i]).slice(-60);
  const max = Math.max(1, ...visibles.map(([ej]) => totales(ej).total));
  const ancho = 22, hueco = 6, alto = 130;
  const barras = visibles.map(([ej, i], n) => {
    const t = totales(ej), x = n * (ancho + hueco);
    const h = v => (v / max) * alto;
    let y = alto, partes = '';
    for (const [k, color] of [['ok', 'var(--ok)'], ['fallo', 'var(--fail)'], ['omitido', 'var(--skip)']]) {
      if (!t[k]) continue;
      y -= h(t[k]);
      partes += `<rect x="${x}" y="${y}" width="${ancho}" height="${h(t[k])}" fill="${color}"/>`;
    }
    if (t.error) partes += `<rect x="${x}" y="${alto - 6}" width="${ancho}" height="6" fill="var(--fail)" opacity=".5"/>`;
    const sel = i === estado.indice ? `<rect class="sel" x="${x - 2}" y="0" width="${ancho + 4}" height="${alto + 2}" rx="3"/>` : '';
    const tip = `${fecha(ej.fecha)} — ${t.ok} ok, ${t.fallo} fallos, ${t.omitido} omitidos${t.error ? ', suite con error' : ''}`;
    return `<g data-i="${i}">${sel}${partes}<rect class="bar" data-i="${i}" x="${x}" y="0" width="${ancho}" height="${alto}" fill="transparent"><title>${esc(tip)}</title></rect></g>`;
  }).join('');
  const w = Math.max(visibles.length * (ancho + hueco), 1);
  return `<svg class="chart" viewBox="0 0 ${w} ${alto + 4}" preserveAspectRatio="xMinYMax meet" role="img" aria-label="Resultados por ejecución">${barras}</svg>`;
}

function tablaEjecuciones() {
  const filas = EJECUCIONES.map((ej, i) => [ej, i]).reverse().map(([ej, i]) => {
    const t = totales(ej), e = estadoDe(ej), g = ej.git || {};
    const suites = ej.suites.map(s => s.nombre).join(' + ');
    return `<tr data-i="${i}" class="${i === estado.indice ? 'sel' : ''}">
      <td>${esc(fecha(ej.fecha))}</td>
      <td>${esc(g.rama || '')} <span class="muted">${esc(g.commit || '')}${g.cambios_sin_commit ? '*' : ''}</span></td>
      <td>${esc(suites)}</td>
      <td class="num">${t.total}</td><td class="num">${t.ok}</td><td class="num">${t.fallo}</td>
      <td class="num">${seg(t.duracion)}</td>
      <td><span class="badge ${e}">${ETIQUETA[e]}</span></td></tr>`;
  }).join('');
  return `<div class="tabla-wrap"><table>
    <thead><tr><th>Fecha</th><th>Rama / commit</th><th>Suites</th><th>Tests</th><th>OK</th><th>Fallos</th><th>Duración</th><th>Estado</th></tr></thead>
    <tbody>${filas}</tbody></table></div>`;
}

function detalleSuite(s, cmb) {
  const q = estado.busqueda.trim().toLowerCase();
  const visible = t =>
    (estado.filtro === 'todos' || t.estado === estado.filtro) &&
    (!q || `${t.grupo} ${t.nombre}`.toLowerCase().includes(q));
  const c = { ok: 0, fallo: 0, omitido: 0 };
  s.tests.forEach(t => c[t.estado]++);
  const total = s.tests.length || 1;

  let cuerpo;
  if (s.estado === 'error') {
    cuerpo = `<div class="banner error">La suite no se pudo ejecutar. Final de la salida:</div><pre class="salida">${esc(s.salida)}</pre>`;
  } else {
    const grupos = new Map();
    for (const t of s.tests.filter(visible)) {
      if (!grupos.has(t.grupo)) grupos.set(t.grupo, []);
      grupos.get(t.grupo).push(t);
    }
    cuerpo = [...grupos].map(([grupo, tests]) => {
      const fallos = tests.filter(t => t.estado === 'fallo').length;
      const filas = tests.map(t => {
        const k = clave(s.nombre, t);
        const marca = cmb.nuevos.has(k) ? ' <span class="badge nuevo">nuevo fallo</span>'
          : cmb.arreglados.has(k) ? ' <span class="badge arreglado">arreglado</span>' : '';
        const error = t.estado === 'fallo' ? `<pre>${esc(t.mensaje)}${t.detalle ? '\n\n' + esc(t.detalle) : ''}</pre>`
          : t.estado === 'omitido' && t.mensaje ? `<pre>${esc(t.mensaje)}</pre>` : '';
        const icono = { ok: '✓', fallo: '✗', omitido: '○' }[t.estado];
        return `<div class="test ${t.estado}"><span class="icono">${icono}</span><span class="nombre">${esc(t.nombre)}${marca}</span><span class="t">${seg(t.duracion)}</span>${error}</div>`;
      }).join('');
      const abierto = fallos || q || estado.filtro !== 'todos' ? 'open' : '';
      const resumen = fallos ? `<span class="badge fallo">${fallos} ✗</span>` : `<span class="badge ok">${tests.length} ✓</span>`;
      return `<details ${abierto}><summary><span class="archivo">${esc(grupo)}</span>${resumen}</summary>${filas}</details>`;
    }).join('') || '<div class="vacio">Ningún test coincide con el filtro.</div>';
  }

  return `<section class="card">
    <div class="suite-head">
      <h2>${esc(s.nombre)} <span class="muted">· ${esc(s.herramienta)}</span></h2>
      <span><span class="badge ${s.estado}">${ETIQUETA[s.estado]}</span>
        <span class="muted">${c.ok}/${s.tests.length} ok · ${seg(s.duracion)}</span></span>
    </div>
    <div class="barra"><div class="ok" style="width:${c.ok / total * 100}%"></div><div class="fallo" style="width:${c.fallo / total * 100}%"></div><div class="omitido" style="width:${c.omitido / total * 100}%"></div></div>
    ${cuerpo}
  </section>`;
}

function render() {
  if (!EJECUCIONES.length) {
    app.innerHTML = '<div class="card vacio">Todavía no hay ejecuciones. Corré <code>python3 scripts/test_report.py</code>.</div>';
    return;
  }
  const ej = EJECUCIONES[estado.indice], t = totales(ej), e = estadoDe(ej), cmb = cambios(estado.indice);
  const banner = {
    ok: `✓ Todos los tests pasaron (${t.ok}).`,
    fallo: `✗ ${t.fallo} test(s) fallaron.`,
    error: '✗ Al menos una suite no se pudo ejecutar.',
  }[e];
  const comparacion = [
    cmb.nuevos.size ? `<span class="badge nuevo">${cmb.nuevos.size} nuevo(s) fallo(s)</span>` : '',
    cmb.arreglados.size ? `<span class="badge arreglado">${cmb.arreglados.size} arreglado(s)</span>` : '',
  ].join(' ');
  const g = ej.git || {};
  const posicion = estado.indice === EJECUCIONES.length - 1 ? 'última ejecución' : `ejecución ${estado.indice + 1} de ${EJECUCIONES.length}`;

  app.innerHTML = `
    <header>
      <div>
        <span class="eyebrow">EVENTIA · TESTS</span>
        <h1>Ejecuciones de tests</h1>
        <div class="muted">${esc(fecha(ej.fecha))} · ${posicion} · ${esc(g.rama || '')} ${esc(g.commit || '')}${g.cambios_sin_commit ? ' (con cambios sin commit)' : ''}</div>
      </div>
      <select id="sel-ejecucion" aria-label="Elegir ejecución">
        ${EJECUCIONES.map((x, i) => [x, i]).reverse().map(([x, i]) =>
          `<option value="${i}" ${i === estado.indice ? 'selected' : ''}>${esc(fecha(x.fecha))} — ${ETIQUETA[estadoDe(x)]}</option>`).join('')}
      </select>
    </header>

    <div class="banner ${e}">${banner} ${comparacion}</div>

    <div class="cards">
      <div class="metric"><b>${t.total}</b><span>tests</span></div>
      <div class="metric ok"><b>${t.ok}</b><span>pasaron</span></div>
      <div class="metric fallo"><b>${t.fallo}</b><span>fallaron</span></div>
      <div class="metric"><b>${t.omitido}</b><span>omitidos</span></div>
      <div class="metric"><b>${seg(t.duracion)}</b><span>duración total</span></div>
    </div>

    <section class="card">
      <h2>Todas las ejecuciones <span class="muted">(${EJECUCIONES.length})</span></h2>
      ${grafico()}
      <div class="leyenda"><span><i style="background:var(--ok)"></i>pasaron</span><span><i style="background:var(--fail)"></i>fallaron</span><span><i style="background:var(--skip)"></i>omitidos</span><span>Hacé clic en una barra o fila para verla.</span></div>
      <div style="margin-top:14px">${tablaEjecuciones()}</div>
    </section>

    <div class="toolbar">
      <input id="buscar" type="search" placeholder="Buscar test o archivo…" value="${esc(estado.busqueda)}" aria-label="Buscar test">
      <div class="chips" role="group" aria-label="Filtrar">
        ${['todos', 'fallo', 'omitido', 'ok'].map(f =>
          `<button data-f="${f}" class="${estado.filtro === f ? 'on' : ''}">${{ todos: 'Todos', fallo: 'Fallidos', omitido: 'Omitidos', ok: 'Pasaron' }[f]}</button>`).join('')}
      </div>
    </div>

    ${ej.suites.map(s => detalleSuite(s, cmb)).join('')}
  `;
}

function seleccionar(i) { estado.indice = Number(i); render(); }

app.addEventListener('click', ev => {
  const fila = ev.target.closest('[data-i]');
  if (fila) return seleccionar(fila.dataset.i);
  const chip = ev.target.closest('[data-f]');
  if (chip) { estado.filtro = chip.dataset.f; render(); }
});
app.addEventListener('change', ev => { if (ev.target.id === 'sel-ejecucion') seleccionar(ev.target.value); });
app.addEventListener('input', ev => {
  if (ev.target.id !== 'buscar') return;
  estado.busqueda = ev.target.value;
  const pos = ev.target.selectionStart;
  render();
  const input = document.getElementById('buscar');
  input.focus(); input.setSelectionRange(pos, pos);
});

render();
</script>
</body>
</html>
"""


# ------------------------------------------------------------
# Programa principal.
# ------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta los tests de Eventia y muestra todas las ejecuciones en un reporte HTML."
    )
    parser.add_argument("--solo", choices=["backend", "frontend"], help="ejecutar una sola suite")
    parser.add_argument("--sin-ejecutar", action="store_true", help="no ejecutar tests; solo regenerar y abrir el reporte")
    parser.add_argument("--no-abrir", action="store_true", help="no abrir el navegador al terminar")
    args = parser.parse_args()

    ejecuciones = leer_historial()
    codigo = 0

    if not args.sin_ejecutar:
        suites = []
        with tempfile.TemporaryDirectory(prefix="eventia-tests-") as tmp:
            if args.solo in (None, "backend"):
                suites.append(suite_backend(Path(tmp)))
            if args.solo in (None, "frontend"):
                suites.append(suite_frontend(Path(tmp)))

        ejecuciones.append({
            "fecha": datetime.now().astimezone().isoformat(timespec="seconds"),
            "git": info_git(),
            "suites": suites,
        })
        guardar_historial(ejecuciones)
        if any(s["estado"] != "ok" for s in suites):
            codigo = 1

    generar_reporte(ejecuciones[-MAX_EJECUCIONES:])
    print(f"\nReporte: {REPORTE}")
    print(f"Ejecuciones guardadas: {min(len(ejecuciones), MAX_EJECUCIONES)}")
    if not args.no_abrir:
        webbrowser.open(REPORTE.as_uri())
    return codigo


if __name__ == "__main__":
    sys.exit(main())
