
# FastAPI es la librería para gestionar APIs web de manera rápida y sencilla.
from fastapi import FastAPI

# CORSMiddleware habilita que el navegador acepte respuestas de esta API
# cuando la petición viene de otro origen, por ejemplo Angular.
from fastapi.middleware.cors import CORSMiddleware

# StaticFiles sirve archivos estáticos.
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.actividades import evento_actividades_router
from app.api.actividades import router as actividades_router
from app.api.auth import router as auth_router
from app.api.categorias_actividad import router as categorias_actividad_router
from app.api.conferencistas import router as conferencistas_router
from app.api.eventos import router as eventos_router
from app.api.inscripciones import router as inscripciones_router
from app.api.roles import router as roles_router
from app.api.users import router as users_router

import app.models  # noqa: F401


# Carpeta backend/docs.
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

# Descripción general de la API.
API_DESCRIPTION = """
API REST del sistema **Eventia** para la gestión de eventos académicos:
eventos, actividades (agenda), conferencistas, inscripciones y
parametrización de roles.

### Cómo autenticarse
1. Ejecutar `POST /api/v1/auth/login` con email y contraseña.
2. Copiar el `access_token` de la respuesta.
3. Presionar **Authorize** e ingresar el token (sin el prefijo `Bearer`).

### Permisos por rol
* **administrador**: parametrización de roles (`/api/v1/roles/...`).
* **organizador**: alta/edición de eventos, actividades y conferencistas.
* Los endpoints de consulta (GET públicos), el login y las inscripciones no
  requieren token.
"""

# Descripción de cada grupo de endpoints.
OPENAPI_TAGS = [
    {
        "name": "Autenticación",
        "description": "Login con email y contraseña; devuelve el token JWT."
    },
    {
        "name": "Usuarios",
        "description": "Datos del usuario autenticado."
    },
    {
        "name": "Parametrización",
        "description": "ABM de roles del sistema y roles de participante. Requiere rol **administrador**."
    },
    {
        "name": "Eventos",
        "description": "Alta, edición y consulta de eventos. Crear/editar requiere rol **organizador**."
    },
    {
        "name": "Actividades",
        "description": "Actividades de un evento (agenda) y asignación de conferencistas. Crear/asignar requiere rol **organizador**."
    },
    {
        "name": "Conferencistas",
        "description": "ABM de conferencistas. Crear/editar/eliminar requiere rol **organizador**."
    },
    {
        "name": "Categorías de actividad",
        "description": "Consulta de las categorías de actividad."
    },
    {
        "name": "Inscripciones",
        "description": "Inscripción pública de participantes a un evento."
    },
    {
        "name": "Sistema",
        "description": "Health check de la API."
    },
]

# Se crea la instancia principal de FastAPI.
app = FastAPI(
    title="Eventia API",
    version="1.0.0",
    description=API_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters={"persistAuthorization": True},
)

# Habilita las peticiones desde el frontend Angular en desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:57109",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de los routers de cada módulo.
app.include_router(auth_router)
app.include_router(roles_router)
app.include_router(users_router)
app.include_router(eventos_router)
app.include_router(inscripciones_router)
app.include_router(conferencistas_router)
app.include_router(categorias_actividad_router)
app.include_router(actividades_router)
app.include_router(evento_actividades_router)

# Publica la documentación estática desde backend/docs.
app.mount(
    "/api-docs",
    StaticFiles(directory=DOCS_DIR, html=True),
    name="api-docs",
)


# Endpoint de health check.
@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
