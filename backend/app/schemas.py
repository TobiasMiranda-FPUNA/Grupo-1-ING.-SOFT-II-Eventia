# BaseModel: clase base de Pydantic de la que heredan todos los schemas,
# permite validar y serializar datos automáticamente.
# ConfigDict: permite configurar el comportamiento del modelo (por ejemplo,
# habilitar la lectura de datos desde atributos de un objeto ORM).
# EmailStr: tipo de dato que valida que el string tenga formato de email.
# Field: permite agregar validaciones y metadatos extra a un campo
# (longitud mínima/máxima, valor por defecto, etc.).
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Datos que se esperan recibir al hacer login: email y contraseña.
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


# Datos de un usuario que se devuelven como respuesta de la API (sin
# información sensible como la contraseña). from_attributes=True permite
# construir este schema directamente desde un objeto del modelo Usuario.
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombres: str
    apellidos: str
    email: EmailStr
    roles: list[str]


# Respuesta del login exitoso: el token de acceso, su tipo, cuándo expira
# y los datos del usuario autenticado.
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# Datos necesarios para crear un nuevo rol del sistema.
class RoleCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)


# Datos opcionales para actualizar un rol existente (todos los campos son
# opcionales para permitir actualizaciones parciales).
class RoleUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)
    activo: bool | None = None


# Datos de un rol que se devuelven como respuesta de la API, extiende
# RoleCreate agregando el id y el estado (activo/inactivo) del rol.
class RoleResponse(RoleCreate):
    id: int
    activo: bool
