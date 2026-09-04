# jwt (PyJWT): se usa aquí para capturar la excepción InvalidTokenError al
# validar el token recibido.
import jwt
# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, status
# HTTPAuthorizationCredentials: representa las credenciales extraídas del
# header Authorization. HTTPBearer: esquema de seguridad que exige un token
# tipo "Bearer <token>" y se lo inyecta al endpoint mediante Depends.
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

# Función para decodificar/validar el token JWT recibido.
from app.core.security import decode_access_token
from app.db import get_db
from app.models import Usuario
from app.schemas import UserResponse


# Router con el prefijo "/api/v1/users", agrupado bajo el tag "Usuarios".
router = APIRouter(prefix="/api/v1/users", tags=["Usuarios"])
# Esquema de autenticación Bearer, reutilizado como dependencia para exigir
# el header "Authorization: Bearer <token>" en los endpoints protegidos.
bearer_scheme = HTTPBearer()


# Dependencia que obtiene el usuario autenticado a partir del token Bearer
# recibido: decodifica el JWT, busca al usuario en la base de datos y
# valida que exista y esté activo. Se usa en todo endpoint que requiera
# autenticación (ej: get_profile más abajo, o require_system_role).
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (ValueError, KeyError, TypeError, jwt.InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o vencido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.scalar(select(Usuario).where(Usuario.id_usuario == user_id))
    if user is None or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autorizado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Fábrica de dependencias: dado el nombre de un rol, devuelve una
# dependencia de FastAPI que exige que el usuario autenticado tenga ese rol
# activo (usada en app/api/roles.py como "admin_required"). Si no lo tiene,
# responde 403 Forbidden.
def require_system_role(role_name: str):
    def role_dependency(user: Usuario = Depends(get_current_user)) -> Usuario:
        if role_name not in {role.nombre for role in user.roles if role.activo}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene permisos para esta operación",
            )
        return user

    return role_dependency


# Endpoint que devuelve el perfil del usuario autenticado (a partir del
# token enviado), incluyendo sus roles activos.
@router.get("/me", response_model=UserResponse)
def get_profile(user: Usuario = Depends(get_current_user)) -> UserResponse:
    roles = [role.nombre for role in user.roles if role.activo]
    return UserResponse(
        id_usuario=user.id_usuario,
        nombres=user.nombres,
        apellidos=user.apellidos,
        email=user.email,
        roles=roles,
    )