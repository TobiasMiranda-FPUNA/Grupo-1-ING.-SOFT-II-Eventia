
# date: usado para validar que la fecha de la actividad quede dentro del
# rango de fechas del evento al que pertenece.
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

# insert: inserta una asociación sin reemplazar las existentes.
# select: construcción declarativa de consultas SQL.
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

# Dependencia que exige que el usuario autenticado tenga un rol específico.
from app.api.users import require_system_role
from app.db import get_db
from app.models import (
    Actividad,
    CategoriaActividad,
    Conferencista,
    Evento,
    Usuario,
    actividad_conferencista,
)
from app.schemas import ActividadCreate, ActividadResponse


router = APIRouter(
    prefix="/api/v1/actividades",
    tags=["Actividades"],
)

evento_actividades_router = APIRouter(
    prefix="/api/v1/eventos",
    tags=["Actividades"],
)

organizer_required = Depends(require_system_role("organizador"))


# Busca un evento por id y lanza 404 si no existe.
def _get_evento_or_404(db: Session, id_evento: int) -> Evento:
    evento = db.get(Evento, id_evento)

    if evento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    return evento


# Busca una categoría activa por id.
def _get_categoria_activa_or_404(
    db: Session,
    id_categoria: int,
) -> CategoriaActividad:
    categoria = db.get(CategoriaActividad, id_categoria)

    if categoria is None or not categoria.activo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría de actividad no encontrada",
        )

    return categoria


# Busca una actividad por id.
def _get_actividad_or_404(
    db: Session,
    actividad_id: int,
) -> Actividad:
    actividad = db.get(Actividad, actividad_id)

    if actividad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actividad no encontrada",
        )

    return actividad


# Busca un conferencista por id.
def _get_conferencista_or_404(
    db: Session,
    conferencista_id: int,
) -> Conferencista:
    conferencista = db.get(Conferencista, conferencista_id)

    if conferencista is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conferencista no encontrado",
        )

    return conferencista


# Valida que la fecha de la actividad esté dentro del rango del evento.
def _validate_fecha_dentro_evento(
    evento: Evento,
    fecha: date,
) -> None:
    if not (evento.fecha_inicio <= fecha <= evento.fecha_fin):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "La fecha de la actividad debe estar dentro "
                "del rango de fechas del evento"
            ),
        )


# Crea una actividad dentro de un evento.
@evento_actividades_router.post(
    "/{evento_id}/actividades",
    response_model=ActividadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_actividad(
    evento_id: int,
    data: ActividadCreate,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> ActividadResponse:

    evento = _get_evento_or_404(db, evento_id)
    categoria = _get_categoria_activa_or_404(db, data.id_categoria)

    _validate_fecha_dentro_evento(evento, data.fecha)

    actividad = Actividad(
        id_evento=evento.id_evento,
        id_categoria=categoria.id_categoria,
        titulo=data.titulo.strip(),
        descripcion=data.descripcion,
        fecha=data.fecha,
        hora_inicio=data.hora_inicio,
        hora_fin=data.hora_fin,
        lugar=data.lugar,
        modalidad=data.modalidad,
        cupo=data.cupo,
    )

    db.add(actividad)
    db.commit()
    db.refresh(actividad)

    return ActividadResponse.model_validate(actividad)


# Obtiene una actividad por id.
@router.get(
    "/{actividad_id}",
    response_model=ActividadResponse,
)
def get_actividad(
    actividad_id: int,
    db: Session = Depends(get_db),
) -> ActividadResponse:

    actividad = _get_actividad_or_404(db, actividad_id)

    return ActividadResponse.model_validate(actividad)


# Lista las actividades de un evento.
@evento_actividades_router.get(
    "/{evento_id}/agenda",
    response_model=list[ActividadResponse],
)
def get_agenda_evento(
    evento_id: int,
    db: Session = Depends(get_db),
) -> list[ActividadResponse]:

    _get_evento_or_404(db, evento_id)

    query = (
        select(Actividad)
        .where(Actividad.id_evento == evento_id)
        .order_by(
            Actividad.fecha,
            Actividad.hora_inicio,
        )
    )

    actividades = db.scalars(query).all()

    return [
        ActividadResponse.model_validate(actividad)
        for actividad in actividades
    ]


# Asocia un conferencista a una actividad.
# Permite que varios conferencistas compartan la misma actividad.
@router.post(
    "/{actividad_id}/conferencistas/{conferencista_id}",
    response_model=ActividadResponse,
    status_code=status.HTTP_201_CREATED,
)
def associate_conferencista(
    actividad_id: int,
    conferencista_id: int,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> ActividadResponse:

    actividad = _get_actividad_or_404(db, actividad_id)

    _get_conferencista_or_404(db, conferencista_id)

    # Comprobar si la asociación ya existe.
    asociacion_existente = db.execute(
        select(actividad_conferencista).where(
            actividad_conferencista.c.id_actividad == actividad_id,
            actividad_conferencista.c.id_conferencista == conferencista_id,
        )
    ).first()

    if asociacion_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El conferencista ya está asociado a esta actividad",
        )

    # Insertar solamente la nueva asociación.
    # Las asociaciones de otros conferencistas se conservan.
    db.execute(
        insert(actividad_conferencista).values(
            id_actividad=actividad_id,
            id_conferencista=conferencista_id,
        )
    )

    db.commit()

    # Recargar la relación para devolver los conferencistas actualizados.
    db.expire(actividad, ["conferencistas"])
    db.refresh(actividad)

    return ActividadResponse.model_validate(actividad)


# Desasocia un conferencista de una actividad.
@router.delete(
    "/{actividad_id}/conferencistas/{conferencista_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def disassociate_conferencista(
    actividad_id: int,
    conferencista_id: int,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> None:

    actividad = _get_actividad_or_404(db, actividad_id)

    conferencista = _get_conferencista_or_404(
        db,
        conferencista_id,
    )

    if conferencista not in actividad.conferencistas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El conferencista no está asociado a esta actividad",
        )

    actividad.conferencistas.remove(conferencista)

    db.commit()
