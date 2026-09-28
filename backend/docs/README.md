# Documentación de la API de Eventia (Swagger)

Documentación interactiva de todos los endpoints del backend. Desde Swagger
se puede ver cada endpoint, sus parámetros y esquemas, y **ejecutarlos**
con el botón *Try it out*.

## Archivos

| Archivo | Descripción |
|---|---|
| `index.html` | Swagger UI. Carga `openapi.json` de esta carpeta. |
| `openapi.json` | Esquema OpenAPI 3 exportado desde la app FastAPI. |
| `generate_openapi.py` | Regenera `openapi.json` a partir del código. |

## Forma rápida (un solo comando)

Desde la raíz del repositorio (con Postgres corriendo):

```bash
./scripts/swagger_up.sh          # macOS / Linux
.\scripts\swagger_up.ps1         # Windows (PowerShell)
```

El script crea `backend/.venv` y `backend/.env` si faltan, regenera
`openapi.json`, levanta el backend (si no estaba corriendo) y abre
http://localhost:8000/api-docs/ en el navegador. Ctrl+C detiene el backend.
Para usar otro puerto: `BACKEND_PORT=8001 ./scripts/swagger_up.sh`.

## Cómo usarla (paso a paso)

1. Levantar la base de datos y el backend (desde la carpeta `backend`):

   ```bash
   source .venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. Abrir en el navegador una de estas opciones:

   | URL | Qué es |
   |---|---|
   | http://localhost:8000/api-docs/ | Swagger de esta carpeta (`docs/index.html`) |
   | http://localhost:8000/docs | Swagger generado en vivo por FastAPI |
   | http://localhost:8000/redoc | Documentación en formato ReDoc (solo lectura) |

   Ambos Swagger muestran lo mismo; `/docs` siempre refleja el código
   actual, mientras que `/api-docs/` muestra el `openapi.json` versionado en
   el repositorio.

3. Autenticarse para los endpoints protegidos (candado 🔒):
   1. Abrir `POST /api/v1/auth/login` → *Try it out* → cargar email y
      contraseña → *Execute*.
   2. Copiar el valor de `access_token` de la respuesta.
   3. Presionar **Authorize** (arriba a la derecha), pegar el token **sin**
      el prefijo `Bearer` y confirmar.

   El token dura 60 minutos (`JWT_EXPIRE_MINUTES`). Si un endpoint responde
   `401`, volver a hacer login; si responde `403`, el usuario no tiene el
   rol necesario.

## Mantener actualizado `openapi.json`

Cada vez que se agregue o modifique un endpoint o un schema, regenerar el
archivo desde la carpeta `backend` (no hace falta la base de datos):

```bash
python docs/generate_openapi.py
```

## Endpoints disponibles

Rol requerido: **—** = público, **token** = cualquier usuario autenticado,
**admin** = rol `administrador`, **org** = rol `organizador`.

### Autenticación y usuarios

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/api/v1/auth/login` | — | Login; devuelve `access_token` y datos del usuario |
| GET | `/api/v1/users/me` | token | Perfil del usuario autenticado y sus roles |

### Parametrización de roles

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/api/v1/roles/sistema` | admin | Lista roles del sistema |
| POST | `/api/v1/roles/sistema` | admin | Crea un rol del sistema |
| PUT / PATCH | `/api/v1/roles/sistema/{role_id}` | admin | Modifica un rol del sistema |
| DELETE | `/api/v1/roles/sistema/{role_id}` | admin | Elimina un rol del sistema |
| GET | `/api/v1/roles/participantes` | admin | Lista roles de participante |
| POST | `/api/v1/roles/participantes` | admin | Crea un rol de participante |
| PUT / PATCH | `/api/v1/roles/participantes/{role_id}` | admin | Modifica un rol de participante |
| DELETE | `/api/v1/roles/participantes/{role_id}` | admin | Elimina un rol de participante |

### Eventos

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/api/v1/eventos` | — | Lista eventos. Filtros: `id_tipo_evento`, `estado`, `q`, `fecha_desde`, `fecha_hasta` |
| GET | `/api/v1/eventos/tipos` | — | Lista los tipos de evento |
| GET | `/api/v1/eventos/{evento_id}` | — | Detalle de un evento |
| POST | `/api/v1/eventos` | org | Crea un evento |
| PUT | `/api/v1/eventos/{evento_id}` | org | Modifica un evento |

### Actividades

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/api/v1/eventos/{evento_id}/actividades` | org | Crea una actividad dentro de un evento |
| GET | `/api/v1/eventos/{evento_id}/agenda` | — | Agenda (actividades) de un evento |
| GET | `/api/v1/actividades/{actividad_id}` | — | Detalle de una actividad |
| POST | `/api/v1/actividades/{actividad_id}/conferencistas/{conferencista_id}` | org | Asigna un conferencista a la actividad |
| DELETE | `/api/v1/actividades/{actividad_id}/conferencistas/{conferencista_id}` | org | Quita un conferencista de la actividad |

### Conferencistas

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/api/v1/conferencistas` | — | Lista conferencistas. Filtros: `q`, `activo` |
| GET | `/api/v1/conferencistas/{conferencista_id}` | — | Detalle de un conferencista |
| POST | `/api/v1/conferencistas` | org | Crea un conferencista |
| PUT / PATCH | `/api/v1/conferencistas/{conferencista_id}` | org | Modifica un conferencista |
| DELETE | `/api/v1/conferencistas/{conferencista_id}` | org | Elimina un conferencista |

### Categorías de actividad

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/api/v1/categorias-actividad` | — | Lista categorías. Filtro: `activo` |
| GET | `/api/v1/categorias-actividad/{categoria_id}` | — | Detalle de una categoría |

### Inscripciones

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/api/v1/inscripciones` | — | Inscribe a un participante en un evento |

### Sistema

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/health` | — | Verifica que la API esté corriendo |
