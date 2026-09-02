# UTC/datetime/timedelta: utilidades estándar de Python para manejar fechas
# y calcular la expiración de los tokens en tiempo universal.
from datetime import UTC, datetime, timedelta

# jwt (PyJWT): librería para crear y verificar tokens JWT (JSON Web Token),
# usados aquí como token de sesión/autenticación de la API.
import jwt
# PasswordHasher: implementa el algoritmo Argon2 para hashear y verificar
# contraseñas de forma segura (nunca se guarda la contraseña en texto plano).
from argon2 import PasswordHasher
# Excepciones que argon2 lanza cuando un hash es inválido o la contraseña
# ingresada no coincide con el hash almacenado.
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Configuración de la app (clave secreta, algoritmo y expiración del JWT).
from app.core.config import settings


# Instancia reutilizable del hasher de Argon2, usada para hashear y
# verificar contraseñas en toda la aplicación.
password_hasher = PasswordHasher()


# Genera el hash seguro de una contraseña en texto plano, para guardarlo
# en la base de datos en lugar de la contraseña original.
def hash_password(password: str) -> str:
    return password_hasher.hash(password)


# Verifica si una contraseña en texto plano coincide con un hash guardado.
# Devuelve False (en vez de lanzar una excepción) si el hash es inválido o
# la contraseña no coincide, simplificando su uso en el login.
def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


# Crea un token JWT de acceso para un usuario autenticado, incluyendo su id
# (sub), sus roles, la fecha de emisión (iat) y la fecha de expiración (exp).
# Devuelve el token junto con los segundos que faltan para que expire.
def create_access_token(user_id: int, roles: list[str]) -> tuple[str, int]:
    expires_in = settings.jwt_expire_minutes * 60
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), expires_in


# Decodifica y valida un token JWT recibido, usando la misma clave secreta
# y algoritmo con los que fue creado. Lanza una excepción si el token es
# inválido, fue alterado o ya expiró.
def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
