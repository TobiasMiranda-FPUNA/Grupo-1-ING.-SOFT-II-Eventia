# Grupo-1-ING.-SOFT-II-Eventia

Proyecto de gestión de eventos académicos y profesionales.

## Backend

La API REST está implementada con Python, FastAPI y PostgreSQL dentro de la carpeta `backend/`.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

La documentación interactiva queda disponible en `/docs`. El endpoint de autenticación es `POST /api/v1/auth/login`.
# SCRIPTS SQL DE LA BASE DE DATOS DEL SISTEMA
La base de datos es en PostgresSQL
