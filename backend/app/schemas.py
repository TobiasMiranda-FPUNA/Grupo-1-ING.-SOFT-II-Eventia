from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombres: str
    apellidos: str
    email: EmailStr
    roles: list[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RoleCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)


class RoleUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)
    activo: bool | None = None


class RoleResponse(RoleCreate):
    id: int
    activo: bool
