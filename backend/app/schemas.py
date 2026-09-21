# date/datetime/time: tipos usados en los campos de fecha de eventos y
# actividades, y en la fecha de registro de una inscripción.
from datetime import date, datetime, time
# Literal: restringe un campo a un conjunto fijo de valores permitidos
# (ej: el estado de un evento solo puede ser "borrador" o "publicado").
# Annotated: permite adjuntarle un validador propio a un tipo (usado en
# Email más abajo).
from typing import Annotated, Literal

# validate_email/EmailNotValidError: misma librería que usa EmailStr de
# Pydantic por debajo, pero llamada directamente para poder pasarle
# test_environment=True (ver comentario en Email más abajo).
from email_validator import EmailNotValidError, validate_email
# BaseModel: clase base de Pydantic de la que heredan todos los schemas,
# permite validar y serializar datos automáticamente.
# ConfigDict: permite configurar el comportamiento del modelo (por ejemplo,
# habilitar la lectura de datos desde atributos de un objeto ORM).
# BeforeValidator: permite adjuntar una función de validación/normalización
# propia a un tipo (usada por Email más abajo).
# Field: permite agregar validaciones y metadatos extra a un campo
# (longitud mínima/máxima, valor por defecto, etc.). model_validator: valida
# el modelo completo una vez parseados los campos individuales (útil para
# reglas que involucran más de un campo, como fecha_fin >= fecha_inicio).
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _validate_email(value: str) -> str:
    # test_environment=True evita que se rechacen dominios reservados para
    # pruebas (test, example, invalid, localhost - ver RFC 2606), que es
    # justamente lo que usan las cuentas de ejemplo cargadas en
    # sql/cargar_datos_ejemplo.sql (ej: admin@eventia.test). Sin este flag,
    # EmailStr de Pydantic las rechaza con "special-use or reserved name".
    try:
        return validate_email(value, check_deliverability=False, test_environment=True).normalized
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc


Email = Annotated[str, BeforeValidator(_validate_email)]


# Datos que se esperan recibir al hacer login: email y contraseña.
class LoginRequest(BaseModel):
    email: Email
    password: str = Field(min_length=1)


# Datos de un usuario que se devuelven como respuesta de la API (sin
# información sensible como la contraseña). from_attributes=True permite
# construir este schema directamente desde un objeto del modelo Usuario.
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombres: str
    apellidos: str
    email: Email
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


# Política de inscripción de un evento: si permite lista de espera cuando se
# agota el cupo, si requiere aprobación manual, la fecha límite para
# inscribirse y el porcentaje mínimo de asistencia exigido para certificado.
# Se usa tanto para recibirla (anidada en EventoCreate/EventoUpdate) como
# para devolverla (anidada en EventoResponse).
class PoliticaInscripcionData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha_limite: date | None = None
    requiere_aprobacion: bool = False
    permite_lista_espera: bool = False
    min_asistencia_certificado: int = Field(default=75, ge=0, le=100)


# Campos comunes a la creación de un evento. La validación de fechas se hace
# a nivel de modelo porque involucra dos campos (fecha_inicio y fecha_fin).
class EventoBase(BaseModel):
    id_tipo_evento: int
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)
    fecha_inicio: date
    fecha_fin: date
    lugar: str | None = Field(default=None, max_length=200)
    cupo_maximo: int = Field(gt=0)
    estado: Literal["borrador", "publicado"] = "borrador"

    @model_validator(mode="after")
    def check_fechas(self) -> "EventoBase":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")
        return self


# Datos necesarios para crear un evento. La política de inscripción es
# opcional: si no se envía, se crea con los valores por defecto (sin lista
# de espera, sin aprobación manual, 75% de asistencia mínima).
class EventoCreate(EventoBase):
    politica: PoliticaInscripcionData = Field(default_factory=PoliticaInscripcionData)


# Datos opcionales para actualizar un evento existente (todos los campos son
# opcionales para permitir actualizaciones parciales). La validación de que
# fecha_fin no sea anterior a fecha_inicio se hace en el endpoint, ya que
# depende de combinar estos valores con los que ya tiene el evento guardado.
class EventoUpdate(BaseModel):
    id_tipo_evento: int | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    lugar: str | None = Field(default=None, max_length=200)
    cupo_maximo: int | None = Field(default=None, gt=0)
    estado: Literal["borrador", "publicado"] | None = None
    politica: PoliticaInscripcionData | None = None


# Datos de un evento que se devuelven como respuesta de la API, incluyendo
# su política de inscripción anidada.
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


# Campos comunes a la creación/actualización de un conferencista (expositor
# invitado a exponer en actividades del evento).
class ConferencistaBase(BaseModel):
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    email: Email
    institucion: str | None = Field(default=None, max_length=150)
    especialidad: str | None = Field(default=None, max_length=150)
    biografia: str | None = Field(default=None, max_length=1000)


# Datos necesarios para crear un conferencista.
class ConferencistaCreate(ConferencistaBase):
    pass


# Datos opcionales para actualizar un conferencista existente (todos los
# campos son opcionales para permitir actualizaciones parciales).
class ConferencistaUpdate(BaseModel):
    nombres: str | None = Field(default=None, min_length=1, max_length=100)
    apellidos: str | None = Field(default=None, min_length=1, max_length=100)
    email: Email | None = None
    institucion: str | None = Field(default=None, max_length=150)
    especialidad: str | None = Field(default=None, max_length=150)
    biografia: str | None = Field(default=None, max_length=1000)
    activo: bool | None = None


# Datos de un conferencista que se devuelven como respuesta de la API.
class ConferencistaResponse(ConferencistaBase):
    model_config = ConfigDict(from_attributes=True)

    id_conferencista: int
    activo: bool


# Campos necesarios para crear una actividad de la agenda de un evento
# (charla, taller, panel). Modelo mínimo: solo lo necesario para poder
# asociarle conferencistas (HU06); no incluye categoría ni cupo propio.
class ActividadCreate(BaseModel):
    id_evento: int
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)
    fecha: date
    hora_inicio: time
    hora_fin: time
    lugar: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def check_horario(self) -> "ActividadCreate":
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        return self


# Datos de una actividad que se devuelven como respuesta de la API,
# incluyendo los conferencistas actualmente asociados a ella.
class ActividadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_actividad: int
    id_evento: int
    nombre: str
    descripcion: str | None
    fecha: date
    hora_inicio: time
    hora_fin: time
    lugar: str | None
    conferencistas: list[ConferencistaResponse] = []


# Datos que se esperan recibir al inscribir un participante a un evento.
# Como la inscripción es pública (no requiere una cuenta de usuario), se
# reciben los datos de contacto del participante junto con el evento y el
# rol que ocupará; si ya existe un participante con ese email se reutiliza.
class InscripcionCreate(BaseModel):
    id_evento: int
    id_rol_participante: int
    documento: str | None = Field(default=None, max_length=50)
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    email: Email
    institucion: str | None = Field(default=None, max_length=150)


# Datos de una inscripción que se devuelven como respuesta de la API,
# incluyendo el estado resultante ("confirmada" o "lista_de_espera").
class InscripcionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_inscripcion: int
    id_evento: int
    id_participante: int
    id_rol_participante: int
    fecha_inscripcion: datetime
    estado: str
