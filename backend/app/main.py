# fastapi es la libreria para gestinar APIs web de manera rápida y sencilla
from fastapi import FastAPI
# CORSMiddleware: habilita que el navegador acepte respuestas de este API
# cuando la petición viene de otro origen (ej: el frontend Angular corriendo
# en http://localhost:4200), algo que el navegador bloquea por defecto.
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.eventos import router as eventos_router
from app.api.inscripciones import router as inscripciones_router
from app.api.roles import router as roles_router
from app.api.users import router as users_router
import app.models  # noqa: F401


# Se crea la instancia principal de la aplicación FastAPI, que es el punto
# de entrada de toda la API (título y versión se muestran en la doc /docs).
app = FastAPI(title="Eventia API", version="1.0.0")

# Habilita las peticiones desde el frontend Angular en desarrollo
# (ng serve corre por defecto en el puerto 4200).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Se registran los routers de cada módulo (auth, roles, users, eventos,
# inscripciones) en la app, incorporando así sus endpoints a la API principal.
app.include_router(auth_router)
app.include_router(roles_router)
app.include_router(users_router)
app.include_router(eventos_router)
app.include_router(inscripciones_router)


# Endpoint de health check: permite verificar que la API está corriendo
# (usado por Docker/orquestadores, CI/CD o para debug manual, sin
# requerir autenticación ni acceder a la base de datos).
@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
