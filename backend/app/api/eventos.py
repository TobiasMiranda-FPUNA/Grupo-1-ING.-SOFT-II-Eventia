# date: usado para tipar los filtros de fecha del listado de eventos.
from datetime import date

# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, status
# select: construcción declarativa de consultas SQL.
from sqlalchemy import select
from sqlalchemy.orm import Session

# Dependencia que exige que el usuario autenticado tenga un rol específico.
from app.api.users import require_system_role
from app.db import get_db
from app.models import Evento, PoliticaInscripcion, TipoEvento, Usuario
from app.schemas import EventoCreate, EventoResponse, EventoUpdate

# Router con el prefijo "/api/v1/eventos", agrupado bajo el tag "Eventos".
router = APIRouter(prefix="/api/v1/eventos", tags=["Eventos"])
# Dependencia reutilizada en los endpoints de escritura: exige que el
# usuario autenticado tenga el rol de sistema "organizador" (listar eventos
# queda público, sin esta dependencia).
organizer_required = Depends(require_system_role("organizador"))


# Valida que la fecha de fin no sea anterior a la fecha de inicio. Se separa
# en una función porque se usa tanto al crear como al actualizar un evento
# (en la actualización, sobre la combinación de fechas ya guardadas y las
# nuevas que llegaron en la petición).
def _validate_fechas(fecha_inicio: date, fecha_fin: date) -> None:
    if fecha_fin < fecha_inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha de fin no puede ser anterior a la fecha de inicio",
        )


# Busca un tipo de evento por id y lanza 404 si no existe, para no crear/
# actualizar un evento apuntando a un tipo de evento inexistente.
def _get_tipo_evento_or_404(db: Session, id_tipo_evento: int) -> TipoEvento:
    tipo = db.get(TipoEvento, id_tipo_evento)
    if tipo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de evento no encontrado")
    return tipo


# Crea un nuevo evento junto con su política de inscripción (o la que venga
# por defecto), validando que el tipo de evento exista, que las fechas sean
# coherentes (fin >= inicio) y que el cupo sea positivo (ya validado por el
# schema EventoCreate con Field(gt=0)).
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
        estado=data.estado,
    )
    db.add(evento)
    db.flush()

    politica = PoliticaInscripcion(id_evento=evento.id_evento, **data.politica.model_dump())
    db.add(politica)
    db.commit()
    db.refresh(evento)
    return EventoResponse.model_validate(evento)


# Lista eventos con filtros opcionales: por tipo de evento, por estado
# (borrador/publicado), por texto en el nombre y por rango de fechas
# (eventos cuyo rango [fecha_inicio, fecha_fin] se solapa con el filtrado).
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
        query = query.where(Evento.estado == estado)
    if q:
        query = query.where(Evento.nombre.ilike(f"%{q}%"))
    if fecha_desde is not None:
        query = query.where(Evento.fecha_fin >= fecha_desde)
    if fecha_hasta is not None:
        query = query.where(Evento.fecha_inicio <= fecha_hasta)

    eventos = db.scalars(query.order_by(Evento.fecha_inicio)).all()
    return [EventoResponse.model_validate(evento) for evento in eventos]


# Actualiza un evento existente de forma parcial: solo se modifican los
# campos presentes en la petición. Si se cambia alguna fecha, se revalida la
# coherencia fin >= inicio contra el resultado final (no solo el campo que
# cambió). La política de inscripción se crea si aún no existía o se
# actualiza campo por campo si ya existía.
@router.put("/{evento_id}", response_model=EventoResponse)
def update_evento(
    evento_id: int,
    data: EventoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> EventoResponse:
    evento = db.get(Evento, evento_id)
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado")

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
        evento.estado = data.estado
    if data.fecha_inicio is not None:
        evento.fecha_inicio = data.fecha_inicio
    if data.fecha_fin is not None:
        evento.fecha_fin = data.fecha_fin
    _validate_fechas(evento.fecha_inicio, evento.fecha_fin)

    if data.politica is not None:
        if evento.politica is None:
            evento.politica = PoliticaInscripcion(id_evento=evento.id_evento, **data.politica.model_dump())
        else:
            for field, value in data.politica.model_dump().items():
                setattr(evento.politica, field, value)

    db.commit()
    db.refresh(evento)
    return EventoResponse.model_validate(evento)
