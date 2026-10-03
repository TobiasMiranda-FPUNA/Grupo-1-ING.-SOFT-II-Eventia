# date/datetime/time: tipos usados en los campos de fecha de eventos y
# actividades, y en la fecha de registro de una inscripción.
from datetime import date, datetime, time

# Literal: restringe un campo a un conjunto fijo de valores permitidos.
# Annotated: permite adjuntar validadores personalizados.
from typing import Annotated, Literal

from email_validator import EmailNotValidError, validate_email

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)


def _validate_email(value: str) -> str:
    # Permite utilizar dominios reservados para pruebas,
    # como admin@eventia.test.
    try:
        return validate_email(
            value,
            check_deliverability=False,
            test_environment=True,
        ).normalized
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc


Email = Annotated[str, BeforeValidator(_validate_email)]


# ============================================================
# MODALIDADES DE ACTIVIDAD
# ============================================================

ModalidadActividad = Literal[
    "PRESENCIAL",
    "VIRTUAL",
    "HIBRIDA"
]


# ============================================================
# AUTENTICACIÓN
# ============================================================

class LoginRequest(BaseModel):
    email: Email
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombres: str
    apellidos: str
    email: Email
    roles: list[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ============================================================
# ROLES DEL SISTEMA
# ============================================================

class RoleCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = Field(
        default=None,
        max_length=255
    )


class RoleUpdate(BaseModel):
    nombre: str | None = Field(
        default=None,
        min_length=1,
        max_length=80
    )

    descripcion: str | None = Field(
        default=None,
        max_length=255
    )

    activo: bool | None = None


class RoleResponse(RoleCreate):
    id: int
    activo: bool


# ============================================================
# POLÍTICA DE INSCRIPCIÓN
# ============================================================

class PoliticaInscripcionData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha_limite: date | None = None

    requiere_aprobacion: bool = False

    permite_lista_espera: bool = False

    min_asistencia_certificado: int = Field(
        default=75,
        ge=0,
        le=100
    )


# ============================================================
# TIPOS DE EVENTO
# ============================================================

class TipoEventoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_tipo_evento: int
    nombre: str
    descripcion: str | None
    activo: bool


# ============================================================
# EVENTOS
# ============================================================

class EventoBase(BaseModel):
    id_tipo_evento: int

    nombre: str = Field(
        min_length=1,
        max_length=150
    )

    descripcion: str | None = Field(
        default=None,
        max_length=500
    )

    fecha_inicio: date
    fecha_fin: date

    lugar: str | None = Field(
        default=None,
        max_length=200
    )

    cupo_maximo: int = Field(gt=0)

    estado: Literal["borrador", "publicado"] = "borrador"

    @model_validator(mode="after")
    def check_fechas(self) -> "EventoBase":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError(
                "La fecha de fin no puede ser anterior a la fecha de inicio"
            )

        return self


class EventoCreate(EventoBase):
    politica: PoliticaInscripcionData = Field(
        default_factory=PoliticaInscripcionData
    )


class EventoUpdate(BaseModel):
    id_tipo_evento: int | None = None

    nombre: str | None = Field(
        default=None,
        min_length=1,
        max_length=150
    )

    descripcion: str | None = Field(
        default=None,
        max_length=500
    )

    fecha_inicio: date | None = None
    fecha_fin: date | None = None

    lugar: str | None = Field(
        default=None,
        max_length=200
    )

    cupo_maximo: int | None = Field(
        default=None,
        gt=0
    )

    estado: Literal["borrador", "publicado"] | None = None

    politica: PoliticaInscripcionData | None = None


class EventoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_evento: int
    id_tipo_evento: int
    nombre: str
    descripcion: str | None
    fecha_inicio: date
    fecha_fin: date
    lugar: str | None
    cupo_maximo: int
    estado: str

    politica: PoliticaInscripcionData | None = None


# ============================================================
# CONFERENCISTAS / EXPOSITORES
# ============================================================

# Campos comunes para crear y devolver conferencistas.

class ConferencistaBase(BaseModel):
    nombres: str = Field(
        min_length=1,
        max_length=100
    )

    apellidos: str = Field(
        min_length=1,
        max_length=100
    )

    email: Email = Field(max_length=150)

    institucion: str | None = Field(
        default=None,
        max_length=150
    )

    # Especialidad profesional del expositor.
    especialidad: str | None = Field(
        default=None,
        max_length=150
    )

    biografia: str | None = None


# Datos necesarios para crear un conferencista.

class ConferencistaCreate(ConferencistaBase):
    pass


# Datos opcionales para actualizar un conferencista.

class ConferencistaUpdate(BaseModel):
    nombres: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    apellidos: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    email: Email | None = Field(
        default=None,
        max_length=150
    )

    institucion: str | None = Field(
        default=None,
        max_length=150
    )

    especialidad: str | None = Field(
        default=None,
        max_length=150
    )

    biografia: str | None = None

    activo: bool | None = None


# Datos devueltos por la API.

class ConferencistaResponse(ConferencistaBase):
    model_config = ConfigDict(from_attributes=True)

    id_conferencista: int
    activo: bool


# ============================================================
# CATEGORÍAS DE ACTIVIDAD
# ============================================================

class CategoriaActividadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_categoria: int
    nombre: str
    descripcion: str | None
    activo: bool


# ============================================================
# ACTIVIDADES
# ============================================================

class ActividadCreate(BaseModel):
    id_categoria: int

    titulo: str = Field(
        min_length=1,
        max_length=150
    )

    descripcion: str | None = None

    fecha: date
    hora_inicio: time
    hora_fin: time

    lugar: str | None = Field(
        default=None,
        max_length=200
    )

    modalidad: ModalidadActividad = "PRESENCIAL"

    cupo: int = Field(ge=0)

    @model_validator(mode="after")
    def check_horario(self) -> "ActividadCreate":
        if self.hora_fin <= self.hora_inicio:
            raise ValueError(
                "La hora de fin debe ser posterior a la hora de inicio"
            )

        return self


class ActividadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_actividad: int
    id_evento: int
    id_categoria: int
    titulo: str
    descripcion: str | None
    fecha: date
    hora_inicio: time
    hora_fin: time
    lugar: str | None
    modalidad: str
    cupo: int

    conferencistas: list[ConferencistaResponse] = []


# ============================================================
# INSCRIPCIONES
# ============================================================

class InscripcionCreate(BaseModel):
    id_evento: int
    id_rol_participante: int

    documento: str | None = Field(
        default=None,
        max_length=50
    )

    nombres: str = Field(
        min_length=1,
        max_length=100
    )

    apellidos: str = Field(
        min_length=1,
        max_length=100
    )

    email: Email

    institucion: str | None = Field(
        default=None,
        max_length=150
    )


class InscripcionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_inscripcion: int
    id_evento: int
    id_participante: int
    id_rol_participante: int
    fecha_inscripcion: datetime
    estado: str