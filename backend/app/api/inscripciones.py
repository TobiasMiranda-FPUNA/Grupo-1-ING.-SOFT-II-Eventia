import logging
# UTC/datetime: para registrar el momento exacto en que se crea la
# inscripción (fecha_inscripcion).
from datetime import UTC, date, datetime
# Annotated: permite declarar una dependencia opcional con valor por
# defecto None (así la función también se puede llamar directo en tests).
from typing import Annotated

# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, Response, status
# func: funciones SQL (COUNT, LOWER) usadas en las consultas.
# select: construcción declarativa de consultas SQL.
from sqlalchemy import func, select
# IntegrityError: excepción que lanza SQLAlchemy cuando una operación viola
# una restricción de la base de datos (aquí, la unicidad evento+participante
# como resguardo extra ante una carrera de escritura concurrente).
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.users import get_optional_user, require_any_system_role
from app.db import get_db
from app.models import Actividad, Evento, Inscripcion, Participante, RolParticipante, Usuario
from app.schemas import (
    InscripcionCreate,
    InscripcionResponse,
    RolParticipantePublicResponse,
)
from app.services.correo import CorreoError, correo_configurado, enviar_tarjeta_inscripcion
from app.services.tarjeta_inscripcion_pdf import (
    ActividadTarjeta,
    DatosTarjeta,
    codigo_inscripcion,
    generar_tarjeta_inscripcion_pdf,
)

logger = logging.getLogger(__name__)

# Router con el prefijo "/api/v1/inscripciones", agrupado bajo el tag
# "Inscripciones". No exige autenticación: la inscripción a un evento es un
# flujo público (el participante no necesariamente tiene una cuenta).
router = APIRouter(prefix="/api/v1/inscripciones", tags=["Inscripciones"])

# Estados posibles del resultado de una inscripción.
CONFIRMED_STATE = "confirmada"
WAITLIST_STATE = "lista_de_espera"
# Único estado de evento que admite nuevas inscripciones.
PUBLISHED_EVENT_STATE = "publicado"

# Personal que gestiona inscripciones: puede descargar y reenviar tarjetas.
staff_required = Depends(
    require_any_system_role("organizador", "administrador", "personal de acreditación")
)


# Busca un participante existente por email (comparación insensible a
# mayúsculas) o crea uno nuevo con los datos recibidos. Evita duplicar el
# registro de una misma persona que se inscribe a más de un evento.
# Si ya existía, completa el documento y la institución que le faltaran (por
# ejemplo, para que salgan en la tarjeta de inscripción); los datos ya
# cargados no se sobrescriben, para que nadie pueda cambiarlos solo con
# conocer el correo de otra persona.
def _get_or_create_participante(db: Session, data: InscripcionCreate) -> Participante:
    email = data.email.strip().lower()
    participante = db.scalar(select(Participante).where(func.lower(Participante.email) == email))
    if participante is not None:
        if not participante.documento and data.documento:
            participante.documento = data.documento
        if not participante.institucion and data.institucion:
            participante.institucion = data.institucion
    else:
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


# Catálogo público de roles activos para alimentar el formulario de
# inscripción sin exigir una cuenta administrativa.
@router.get(
    "/roles-participante",
    response_model=list[RolParticipantePublicResponse],
)
def list_public_participant_roles(
    db: Session = Depends(get_db),
) -> list[RolParticipantePublicResponse]:
    roles = db.scalars(
        select(RolParticipante)
        .where(RolParticipante.activo.is_(True))
        .order_by(RolParticipante.nombre)
    ).all()
    return [
        RolParticipantePublicResponse.model_validate(rol)
        for rol in roles
    ]


# Crea la inscripción de un participante a un evento con lógica
# transaccional: valida que el evento y el rol existan, evita inscripciones
# duplicadas del mismo participante al mismo evento, y asigna el estado
# según el cupo disponible: "confirmada" si hay cupo, "lista_de_espera" si
# no hay cupo pero la política del evento lo permite, o rechaza la
# operación (409) si no hay cupo ni lista de espera habilitada.
# Roles de sistema del personal que inscribe a otras personas desde el
# mismo formulario (sus datos personales no se fuerzan).
STAFF_ROLES = {"organizador", "administrador", "personal de acreditación"}


# Si quien envía el pedido es un participante con sesión iniciada, se
# inscribe a sí mismo: nombres, apellidos y correo se toman de su cuenta y
# se descarta lo que venga en el cuerpo (aunque se haya manipulado el
# formulario). Sin sesión, o si es personal del evento, se usan los datos
# enviados.
def _con_datos_de_cuenta(data: InscripcionCreate, usuario: Usuario | None) -> InscripcionCreate:
    if usuario is None:
        return data
    roles = {rol.nombre.lower() for rol in usuario.roles if rol.activo}
    if "participante" not in roles or roles & STAFF_ROLES:
        return data
    return data.model_copy(
        update={"nombres": usuario.nombres, "apellidos": usuario.apellidos, "email": usuario.email}
    )


@router.post("", response_model=InscripcionResponse, status_code=status.HTTP_201_CREATED)
def create_inscripcion(
    data: InscripcionCreate,
    db: Session = Depends(get_db),
    usuario: Annotated[Usuario | None, Depends(get_optional_user)] = None,
) -> InscripcionResponse:
    data = _con_datos_de_cuenta(data, usuario)
    # with_for_update() bloquea la fila del evento hasta el commit, para que
    # dos inscripciones concurrentes no lean el mismo conteo de cupo antes
    # de que ninguna haya confirmado la suya (en SQLite, usado en los tests,
    # esta cláusula es ignorada de forma segura al no ser soportada).
    # of=Evento limita el bloqueo a la tabla evento: la política se carga con
    # un LEFT OUTER JOIN y PostgreSQL no permite FOR UPDATE sobre el lado
    # nullable de un outer join.
    evento = db.scalar(
        select(Evento).where(Evento.id_evento == data.id_evento).with_for_update(of=Evento)
    )
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado")

    # Solo los eventos publicados aceptan inscripciones (no borradores,
    # cancelados ni finalizados).
    if evento.estado != PUBLISHED_EVENT_STATE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El evento no está abierto a inscripciones",
        )

    # Respeta la fecha límite de inscripción definida en la política.
    if (
        evento.politica is not None
        and evento.politica.fecha_limite is not None
        and date.today() > evento.politica.fecha_limite
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El plazo de inscripción para este evento ya finalizó",
        )

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

    respuesta = InscripcionResponse.model_validate(inscripcion)
    # Solo los confirmados reciben la tarjeta: los de lista de espera todavía
    # no están habilitados a las actividades.
    if inscripcion.estado == CONFIRMED_STATE:
        respuesta.envio_correo = _enviar_tarjeta(db, inscripcion)
    return respuesta


def _datos_tarjeta(db: Session, inscripcion: Inscripcion) -> tuple[Participante, DatosTarjeta]:
    participante = db.get(Participante, inscripcion.id_participante)
    evento = db.get(Evento, inscripcion.id_evento)
    rol = db.get(RolParticipante, inscripcion.id_rol_participante)
    actividades = db.scalars(
        select(Actividad)
        .where(Actividad.id_evento == evento.id_evento)
        .order_by(Actividad.fecha, Actividad.hora_inicio, Actividad.id_actividad)
    ).all()

    return participante, DatosTarjeta(
        id_inscripcion=inscripcion.id_inscripcion,
        participante=f"{participante.nombres} {participante.apellidos}".strip(),
        documento=participante.documento,
        institucion=participante.institucion,
        rol=rol.nombre,
        evento=evento.nombre,
        fecha_inicio_evento=evento.fecha_inicio,
        fecha_fin_evento=evento.fecha_fin,
        lugar_evento=evento.lugar,
        actividades=[
            ActividadTarjeta(
                titulo=a.titulo,
                fecha=a.fecha,
                hora_inicio=a.hora_inicio,
                hora_fin=a.hora_fin,
                lugar=a.lugar,
            )
            for a in actividades
        ],
    )


# Envía la tarjeta en PDF al correo del participante. Nunca lanza: un fallo
# del servidor de correo no debe deshacer la inscripción ya registrada.
def _enviar_tarjeta(db: Session, inscripcion: Inscripcion) -> str:
    if not correo_configurado():
        return "no_configurado"

    participante, datos = _datos_tarjeta(db, inscripcion)
    try:
        enviar_tarjeta_inscripcion(
            participante.email,
            datos,
            generar_tarjeta_inscripcion_pdf(datos),
        )
    except CorreoError:
        logger.exception(
            "No se pudo enviar la tarjeta %s a %s",
            codigo_inscripcion(inscripcion.id_inscripcion),
            participante.email,
        )
        return "error"
    return "enviado"


def _inscripcion_confirmada_or_error(db: Session, id_inscripcion: int) -> Inscripcion:
    inscripcion = db.get(Inscripcion, id_inscripcion)
    if inscripcion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscripción no encontrada")
    if inscripcion.estado != CONFIRMED_STATE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo las inscripciones confirmadas tienen tarjeta de inscripción",
        )
    return inscripcion


# Descarga la tarjeta de inscripción en PDF (para imprimirla en la puerta).
@router.get(
    "/{id_inscripcion}/tarjeta",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def descargar_tarjeta(
    id_inscripcion: int,
    db: Session = Depends(get_db),
    _: Usuario = staff_required,
) -> Response:
    inscripcion = _inscripcion_confirmada_or_error(db, id_inscripcion)
    _, datos = _datos_tarjeta(db, inscripcion)
    codigo = codigo_inscripcion(inscripcion.id_inscripcion)
    return Response(
        content=generar_tarjeta_inscripcion_pdf(datos),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="tarjeta-{codigo}.pdf"'},
    )


# Reenvía por correo la tarjeta de una inscripción confirmada.
@router.post("/{id_inscripcion}/tarjeta/enviar", response_model=InscripcionResponse)
def reenviar_tarjeta(
    id_inscripcion: int,
    db: Session = Depends(get_db),
    _: Usuario = staff_required,
) -> InscripcionResponse:
    inscripcion = _inscripcion_confirmada_or_error(db, id_inscripcion)
    if not correo_configurado():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El envío de correos no está configurado en el servidor (SMTP).",
        )

    envio = _enviar_tarjeta(db, inscripcion)
    if envio == "error":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El servidor de correo no pudo enviar la tarjeta.",
        )

    respuesta = InscripcionResponse.model_validate(inscripcion)
    respuesta.envio_correo = envio
    return respuesta
