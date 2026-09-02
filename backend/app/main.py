# fastapi es la libreria para gestinar APIs web de manera rápida y sencilla
from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.roles import router as roles_router
from app.api.users import router as users_router
import app.models  # noqa: F401


# Se crea la instancia principal de la aplicación FastAPI, que es el punto
# de entrada de toda la API (título y versión se muestran en la doc /docs).
app = FastAPI(title="Eventia API", version="1.0.0")

# Se registran los routers de cada módulo (auth, roles, users) en la app,
# incorporando así sus endpoints a la API principal.
app.include_router(auth_router)
app.include_router(roles_router)
app.include_router(users_router)


# Endpoint de health check: permite verificar que la API está corriendo
# (usado por Docker/orquestadores, CI/CD o para debug manual, sin
# requerir autenticación ni acceder a la base de datos).
@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
