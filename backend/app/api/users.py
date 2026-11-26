# jwt (PyJWT): se usa aquí para capturar la excepción InvalidTokenError al
# validar el token recibido.
import jwt
# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, status
# HTTPAuthorizationCredentials: representa las credenciales extraídas del
# header Authorization. HTTPBearer: esquema de seguridad que exige un token
# tipo "Bearer <token>" y se lo inyecta al endpoint mediante Depends.
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

# Función para decodificar/validar el token JWT recibido, y para hashear
# la contraseña de los usuarios creados por el administrador.
from app.core.security import decode_access_token, hash_password
from app.db import get_db
from app.models import RolSistema, Usuario
from app.schemas import UserResponse, UsuarioAdminResponse, UsuarioCreate


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


# Variante para endpoints públicos que se comportan distinto si hay sesión
# (ej: la inscripción). Sin header Authorization devuelve None; con un
# token inválido o vencido responde 401, igual que get_current_user.
optional_bearer_scheme = HTTPBearer(auto_error=False)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario | None:
    if credentials is None:
        return None
    return get_current_user(credentials, db)


# Fábrica de dependencias: dado el nombre de un rol, devuelve una
# dependencia de FastAPI que exige que el usuario autenticado tenga ese rol
# activo (usada en app/api/roles.py como "admin_required"). Si no lo tiene,
# responde 403 Forbidden.
def require_system_role(role_name: str):
    role_name_lower = role_name.lower()

    def role_dependency(user: Usuario = Depends(get_current_user)) -> Usuario:
        active_roles = {role.nombre.lower() for role in user.roles if role.activo}
        if role_name_lower not in active_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene permisos para esta operación",
            )
        return user

    return role_dependency


# Variante para operaciones que pueden ser realizadas por más de un rol.
# Se utiliza, por ejemplo, en asistencia (organizador/acreditación/admin)
# y en emisión de certificados (organizador/admin).
def require_any_system_role(*role_names: str):
    role_names_lower = {role_name.lower() for role_name in role_names}

    def role_dependency(user: Usuario = Depends(get_current_user)) -> Usuario:
        active_roles = {role.nombre.lower() for role in user.roles if role.activo}
        if active_roles.isdisjoint(role_names_lower):
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

# ============================================================
# GESTIÓN DE USUARIOS (solo administrador)
# ============================================================

# Dependencia reutilizada por los endpoints de gestión de usuarios.
admin_required = Depends(require_system_role("administrador"))


def _to_admin_response(user: Usuario) -> UsuarioAdminResponse:
    return UsuarioAdminResponse(
        id_usuario=user.id_usuario,
        nombres=user.nombres,
        apellidos=user.apellidos,
        email=user.email,
        activo=user.activo,
        roles=[role.nombre for role in user.roles],
    )


# Lista todas las cuentas del sistema, ordenadas por apellido y nombre.
@router.get("", response_model=list[UsuarioAdminResponse])
def list_users(
    db: Session = Depends(get_db),
    _: Usuario = admin_required,
) -> list[UsuarioAdminResponse]:
    users = db.scalars(select(Usuario).order_by(Usuario.apellidos, Usuario.nombres)).all()
    return [_to_admin_response(user) for user in users]


# Crea una cuenta con correo, contraseña (guardada con Argon2) y un rol
# de sistema activo. El correo no puede repetirse (sin distinguir
# mayúsculas de minúsculas).
@router.post("", response_model=UsuarioAdminResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    _: Usuario = admin_required,
) -> UsuarioAdminResponse:
    duplicado = db.scalar(
        select(Usuario.id_usuario).where(func.lower(Usuario.email) == payload.email.lower())
    )
    if duplicado is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese correo")

    role = db.get(RolSistema, payload.id_rol_sistema)
    if role is None or not role.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El rol seleccionado no existe o está inactivo")

    user = Usuario(
        nombres=payload.nombres,
        apellidos=payload.apellidos,
        email=payload.email,
        password_hash=hash_password(payload.password),
        activo=True,
        roles=[role],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_admin_response(user)


# Elimina una cuenta. El administrador no puede eliminarse a sí mismo:
# así el sistema nunca se queda sin quien lo administre.
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = admin_required,
) -> None:
    user = db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if user.id_usuario == current_user.id_usuario:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No podés eliminar tu propio usuario")
    # Al borrar el usuario, SQLAlchemy elimina también sus filas de
    # usuario_rol. En PostgreSQL, participante.id_usuario queda en NULL
    # (ON DELETE SET NULL), así que sus inscripciones se conservan.
    db.delete(user)
    db.commit()
