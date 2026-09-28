# Mockup interactivo de Eventia

Réplica estática (HTML + CSS + JavaScript puro) de las pantallas del frontend
Angular (`frontend/src/app/pages/`). Funciona sin backend ni base de datos:
los datos se simulan en `js/mock-data.js` y se guardan en el `localStorage`
del navegador.

## Cómo abrirlo

Desde la raíz del repositorio:

```bash
./scripts/mockup_up.sh              # muestra un menú para elegir la pantalla
./scripts/mockup_up.sh eventos      # abre directamente una pantalla
./scripts/mockup_up.sh --list       # lista las pantallas disponibles
```

En Windows (PowerShell):

```powershell
.\scripts\mockup_up.ps1
.\scripts\mockup_up.ps1 eventos
```

El script levanta un servidor HTTP local (`python3 -m http.server`, puerto
`4300` por defecto, configurable con `MOCKUP_PORT`) y abre el navegador.
Con Ctrl+C se detiene. Si no hay Python, abre el archivo directamente.

## Pantallas

| Opción         | Archivo                   | Ruta en Angular         |
|----------------|---------------------------|-------------------------|
| `todas`        | `index.html`              | —                       |
| `login`        | `login.html`              | `/login`                |
| `roles`        | `roles.html`              | `/roles`                |
| `eventos`      | `eventos.html`            | `/eventos`              |
| `evento-nuevo` | `evento-form.html`        | `/eventos/nuevo`        |
| `evento-editar`| `evento-form.html?id=1`   | `/eventos/:id/editar`   |

## Datos de prueba

- Login válido: `admin@eventia.test` u `organizador@eventia.test` con
  cualquier contraseña de 6 o más caracteres. Otro correo muestra la alerta
  de credencial inválida.
- El rol "Estudiante" está marcado como en uso, para probar el bloqueo al
  eliminarlo.
- "Reiniciar datos" (barra inferior) vuelve a los datos de ejemplo.

## Estructura

```
mockup/
├── index.html            selector de pantallas
├── login.html  roles.html  eventos.html  evento-form.html
├── css/                  estilos de cada pantalla (traducidos de los .scss)
│   └── mockup-bar.css    barra inferior propia del mockup
└── js/
    ├── mock-data.js      API simulada y datos de ejemplo
    ├── mockup-bar.js     navegación entre pantallas
    └── <pantalla>.js     lógica de cada pantalla (réplica de su .ts)
```

Si se modifica una pantalla del frontend, hay que actualizar a mano su
`.html`, `css/` y `js/` correspondientes acá.
