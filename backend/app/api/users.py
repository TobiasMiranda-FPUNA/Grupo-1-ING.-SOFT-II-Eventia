import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import get_db
from app.models import Usuario
from app.schemas import UserResponse


router = APIRouter(prefix="/api/v1/users", tags=["Usuarios"])
bearer_scheme = HTTPBearer()


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


def require_system_role(role_name: str):
    def role_dependency(user: Usuario = Depends(get_current_user)) -> Usuario:
        if role_name not in {role.nombre for role in user.roles if role.activo}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene permisos para esta operación",
            )
        return user

    return role_dependency


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