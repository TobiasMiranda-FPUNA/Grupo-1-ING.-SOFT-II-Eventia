# APIRouter: agrupa endpoints relacionados (aquí, los de autenticación) para
# luego incluirlos en la app principal. Depends: declara dependencias que
# FastAPI resuelve automáticamente antes de ejecutar el endpoint (ej: la
# sesión de BD). HTTPException/status: para devolver errores HTTP con un
# código y mensaje específico.
from fastapi import APIRouter, Depends, HTTPException, status
# select: construye consultas SQL de forma declarativa (estilo SQLAlchemy 2.x).
from sqlalchemy import select
# Session: tipo de la sesión de base de datos usada para consultar/persistir.
from sqlalchemy.orm import Session

# Funciones de seguridad: generar el token JWT y verificar la contraseña.
from app.core.security import create_access_token, verify_password
# Dependencia que entrega una sesión de base de datos por petición.
from app.db import get_db
# Modelo ORM del usuario, para consultarlo en la base de datos.
from app.models import Usuario
# Schemas (Pydantic) de entrada/salida para el login.
from app.schemas import LoginRequest, TokenResponse, UserResponse


# Router con el prefijo "/api/v1/auth", agrupado bajo el tag "Autenticación"
# en la documentación automática de la API.
router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


# Endpoint de login: recibe email/contraseña, valida las credenciales
# contra la base de datos y, si son correctas, devuelve un token de acceso
# junto con los datos básicos del usuario.
@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(Usuario).where(Usuario.email == credentials.email))
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not verify_password(credentials.password, user.password_hash):
        raise invalid_credentials
    if not user.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    roles = [role.nombre for role in user.roles if role.activo]
    token, expires_in = create_access_token(user.id_usuario, roles)
    response_user = UserResponse(
        id_usuario=user.id_usuario,
        nombres=user.nombres,
        apellidos=user.apellidos,
        email=user.email,
        roles=roles,
    )
    return TokenResponse(access_token=token, expires_in=expires_in, user=response_user)
