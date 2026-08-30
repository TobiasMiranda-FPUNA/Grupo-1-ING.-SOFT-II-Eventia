from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.roles import router as roles_router
from app.api.users import router as users_router
import app.models  # noqa: F401


app = FastAPI(title="Eventia API", version="1.0.0")
app.include_router(auth_router)
app.include_router(roles_router)
app.include_router(users_router)


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
