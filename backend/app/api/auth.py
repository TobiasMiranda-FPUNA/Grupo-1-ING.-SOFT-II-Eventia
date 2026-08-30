from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db import get_db
from app.models import Usuario
from app.schemas import LoginRequest, TokenResponse, UserResponse


router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


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
