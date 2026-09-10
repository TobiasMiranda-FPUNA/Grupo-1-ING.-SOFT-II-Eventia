# UTC/datetime: para registrar el momento exacto en que se crea la
# inscripción (fecha_inscripcion).
from datetime import UTC, datetime

# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, status
# func: funciones SQL (COUNT, LOWER) usadas en las consultas.
# select: construcción declarativa de consultas SQL.
from sqlalchemy import func, select
# IntegrityError: excepción que lanza SQLAlchemy cuando una operación viola
# una restricción de la base de datos (aquí, la unicidad evento+participante
# como resguardo extra ante una carrera de escritura concurrente).
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Evento, Inscripcion, Participante, RolParticipante
from app.schemas import InscripcionCreate, InscripcionResponse

# Router con el prefijo "/api/v1/inscripciones", agrupado bajo el tag
# "Inscripciones". No exige autenticación: la inscripción a un evento es un
# flujo público (el participante no necesariamente tiene una cuenta).
router = APIRouter(prefix="/api/v1/inscripciones", tags=["Inscripciones"])

# Estados posibles del resultado de una inscripción.
CONFIRMED_STATE = "confirmada"
WAITLIST_STATE = "lista_de_espera"


# Busca un participante existente por email (comparación insensible a
# mayúsculas) o crea uno nuevo con los datos recibidos. Evita duplicar el
# registro de una misma persona que se inscribe a más de un evento.
def _get_or_create_participante(db: Session, data: InscripcionCreate) -> Participante:
    email = data.email.strip().lower()
    participante = db.scalar(select(Participante).where(func.lower(Participante.email) == email))
    if participante is None:
        participante = Participante(
            documento=data.documento,
            nombres=data.nombres.strip(),
            apellidos=data.apellidos.strip(),
            email=email,
            institucion=data.institucion,
        )
        db.add(participante)
        db.flush()
    return participante


# Construye el error 409 Conflict que se devuelve cuando el participante ya
# tiene una inscripción registrada para el mismo evento.
def _duplicate_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="El participante ya está inscripto en este evento",
    )


# Crea la inscripción de un participante a un evento con lógica
# transaccional: valida que el evento y el rol existan, evita inscripciones
# duplicadas del mismo participante al mismo evento, y asigna el estado
# según el cupo disponible: "confirmada" si hay cupo, "lista_de_espera" si
# no hay cupo pero la política del evento lo permite, o rechaza la
# operación (409) si no hay cupo ni lista de espera habilitada.
@router.post("", response_model=InscripcionResponse, status_code=status.HTTP_201_CREATED)
def create_inscripcion(data: InscripcionCreate, db: Session = Depends(get_db)) -> InscripcionResponse:
    # with_for_update() bloquea la fila del evento hasta el commit, para que
    # dos inscripciones concurrentes no lean el mismo conteo de cupo antes
    # de que ninguna haya confirmado la suya (en SQLite, usado en los tests,
    # esta cláusula es ignorada de forma segura al no ser soportada).
    evento = db.scalar(select(Evento).where(Evento.id_evento == data.id_evento).with_for_update())
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado")

    rol = db.get(RolParticipante, data.id_rol_participante)
    if rol is None or not rol.activo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol de participante no encontrado")

    participante = _get_or_create_participante(db, data)

    existing = db.scalar(
        select(Inscripcion).where(
            Inscripcion.id_evento == evento.id_evento,
            Inscripcion.id_participante == participante.id_participante,
        )
    )
    if existing is not None:
        raise _duplicate_error()

    confirmados = db.scalar(
        select(func.count())
        .select_from(Inscripcion)
        .where(Inscripcion.id_evento == evento.id_evento, Inscripcion.estado == CONFIRMED_STATE)
    )

    if confirmados < evento.cupo_maximo:
        estado = CONFIRMED_STATE
    elif evento.politica is not None and evento.politica.permite_lista_espera:
        estado = WAITLIST_STATE
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay cupos disponibles para este evento",
        )

    inscripcion = Inscripcion(
        id_evento=evento.id_evento,
        id_participante=participante.id_participante,
        id_rol_participante=rol.id_rol_participante,
        estado=estado,
        fecha_inscripcion=datetime.now(UTC),
    )
    db.add(inscripcion)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _duplicate_error() from None
    db.refresh(inscripcion)
    return InscripcionResponse.model_validate(inscripcion)
