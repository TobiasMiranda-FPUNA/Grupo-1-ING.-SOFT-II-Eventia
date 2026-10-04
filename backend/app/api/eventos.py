
# date: usado para tipar los filtros de fecha del listado de eventos.
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.users import require_system_role
from app.db import get_db
from app.models import Evento, PoliticaInscripcion, TipoEvento, Usuario
from app.schemas import EventoCreate, EventoResponse, EventoUpdate, TipoEventoResponse


router = APIRouter(prefix="/api/v1/eventos", tags=["Eventos"])

organizer_required = Depends(require_system_role("organizador"))


# Estados permitidos por la restricción de PostgreSQL.
ESTADOS_EVENTO = {"BORRADOR", "PUBLICADO", "FINALIZADO", "CANCELADO"}


# Normaliza el estado recibido desde Angular.
# Por ejemplo: "borrador" -> "BORRADOR".
def _normalizar_estado(estado: str) -> str:
    estado_normalizado = estado.strip().upper()

    if estado_normalizado not in ESTADOS_EVENTO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Estado no válido: {estado}. "
                f"Estados permitidos: {', '.join(sorted(ESTADOS_EVENTO))}"
            ),
        )

    return estado_normalizado


# Valida que la fecha de fin no sea anterior a la fecha de inicio.
def _validate_fechas(fecha_inicio: date, fecha_fin: date) -> None:
    if fecha_fin < fecha_inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha de fin no puede ser anterior a la fecha de inicio",
        )


# Busca un tipo de evento por ID.
def _get_tipo_evento_or_404(db: Session, id_tipo_evento: int) -> TipoEvento:
    tipo = db.get(TipoEvento, id_tipo_evento)

    if tipo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de evento no encontrado",
        )

    return tipo


# Crea un evento junto con su política de inscripción.
@router.post("", response_model=EventoResponse, status_code=status.HTTP_201_CREATED)
def create_evento(
    data: EventoCreate,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> EventoResponse:

    _get_tipo_evento_or_404(db, data.id_tipo_evento)

    _validate_fechas(data.fecha_inicio, data.fecha_fin)

    evento = Evento(
        id_tipo_evento=data.id_tipo_evento,
        nombre=data.nombre.strip(),
        descripcion=data.descripcion,
        fecha_inicio=data.fecha_inicio,
        fecha_fin=data.fecha_fin,
        lugar=data.lugar,
        cupo_maximo=data.cupo_maximo,
        estado=_normalizar_estado(data.estado),
    )

    db.add(evento)
    db.flush()

    politica = PoliticaInscripcion(
        id_evento=evento.id_evento,
        **data.politica.model_dump(),
    )

    db.add(politica)
    db.commit()
    db.refresh(evento)

    return EventoResponse.model_validate(evento)


# Devuelve los tipos de evento activos.
@router.get("/tipos", response_model=list[TipoEventoResponse])
def list_tipos_evento(
    db: Session = Depends(get_db),
) -> list[TipoEventoResponse]:

    tipos = db.scalars(
        select(TipoEvento)
        .where(TipoEvento.activo.is_(True))
        .order_by(TipoEvento.nombre)
    ).all()

    return [
        TipoEventoResponse.model_validate(tipo)
        for tipo in tipos
    ]


# Devuelve un evento puntual.
@router.get("/{evento_id}", response_model=EventoResponse)
def get_evento(
    evento_id: int,
    db: Session = Depends(get_db),
) -> EventoResponse:

    evento = db.get(Evento, evento_id)

    if evento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    return EventoResponse.model_validate(evento)


# Lista eventos con filtros opcionales.
@router.get("", response_model=list[EventoResponse])
def list_eventos(
    db: Session = Depends(get_db),
    id_tipo_evento: int | None = None,
    estado: str | None = None,
    q: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> list[EventoResponse]:

    query = select(Evento)

    if id_tipo_evento is not None:
        query = query.where(Evento.id_tipo_evento == id_tipo_evento)

    if estado is not None:
        query = query.where(
            Evento.estado == _normalizar_estado(estado)
        )

    if q:
        query = query.where(Evento.nombre.ilike(f"%{q}%"))

    if fecha_desde is not None:
        query = query.where(Evento.fecha_fin >= fecha_desde)

    if fecha_hasta is not None:
        query = query.where(Evento.fecha_inicio <= fecha_hasta)

    eventos = db.scalars(
        query.order_by(Evento.fecha_inicio)
    ).all()

    return [
        EventoResponse.model_validate(evento)
        for evento in eventos
    ]


# Actualiza un evento existente.
@router.put("/{evento_id}", response_model=EventoResponse)
def update_evento(
    evento_id: int,
    data: EventoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> EventoResponse:

    evento = db.get(Evento, evento_id)

    if evento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if data.id_tipo_evento is not None:
        _get_tipo_evento_or_404(db, data.id_tipo_evento)
        evento.id_tipo_evento = data.id_tipo_evento

    if data.nombre is not None:
        evento.nombre = data.nombre.strip()

    if data.descripcion is not None:
        evento.descripcion = data.descripcion

    if data.lugar is not None:
        evento.lugar = data.lugar

    if data.cupo_maximo is not None:
        evento.cupo_maximo = data.cupo_maximo

    if data.estado is not None:
        evento.estado = _normalizar_estado(data.estado)

    if data.fecha_inicio is not None:
        evento.fecha_inicio = data.fecha_inicio

    if data.fecha_fin is not None:
        evento.fecha_fin = data.fecha_fin

    _validate_fechas(
        evento.fecha_inicio,
        evento.fecha_fin,
    )

    if data.politica is not None:
        if evento.politica is None:
            evento.politica = PoliticaInscripcion(
                id_evento=evento.id_evento,
                **data.politica.model_dump(),
            )
        else:
            for field, value in data.politica.model_dump().items():
                setattr(evento.politica, field, value)

    db.commit()
    db.refresh(evento)

    return EventoResponse.model_validate(evento)
