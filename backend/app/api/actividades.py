# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Dependencia que exige que el usuario autenticado tenga un rol específico.
from app.api.users import require_system_role
from app.db import get_db
from app.models import Actividad, Conferencista, Evento, Usuario
from app.schemas import ActividadCreate, ActividadResponse

# Router con el prefijo "/api/v1/actividades", agrupado bajo el tag
# "Actividades" (agenda de un evento: charlas, talleres, paneles). Modelo
# mínimo: solo cubre lo necesario para asociar/desasociar conferencistas a
# una actividad (HU06); el CRUD completo de actividades queda fuera de este
# alcance.
router = APIRouter(prefix="/api/v1/actividades", tags=["Actividades"])
# Dependencia reutilizada en los endpoints de escritura: exige que el
# usuario autenticado tenga el rol de sistema "organizador" (leer/listar
# queda público, igual que en app/api/eventos.py y app/api/conferencistas.py).
organizer_required = Depends(require_system_role("organizador"))


# Busca un evento por id y lanza 404 si no existe, para no crear una
# actividad apuntando a un evento inexistente.
def _get_evento_or_404(db: Session, id_evento: int) -> Evento:
    evento = db.get(Evento, id_evento)
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado")
    return evento


# Busca una actividad por id y lanza 404 si no existe.
def _get_actividad_or_404(db: Session, actividad_id: int) -> Actividad:
    actividad = db.get(Actividad, actividad_id)
    if actividad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actividad no encontrada")
    return actividad


# Busca un conferencista por id y lanza 404 si no existe.
def _get_conferencista_or_404(db: Session, conferencista_id: int) -> Conferencista:
    conferencista = db.get(Conferencista, conferencista_id)
    if conferencista is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conferencista no encontrado")
    return conferencista


# Crea una nueva actividad dentro de un evento, validando que el evento
# exista (la coherencia de horario ya la valida ActividadCreate a nivel de
# schema).
@router.post("", response_model=ActividadResponse, status_code=status.HTTP_201_CREATED)
def create_actividad(
    data: ActividadCreate,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> ActividadResponse:
    _get_evento_or_404(db, data.id_evento)

    actividad = Actividad(
        id_evento=data.id_evento,
        nombre=data.nombre.strip(),
        descripcion=data.descripcion,
        fecha=data.fecha,
        hora_inicio=data.hora_inicio,
        hora_fin=data.hora_fin,
        lugar=data.lugar,
    )
    db.add(actividad)
    db.commit()
    db.refresh(actividad)
    return ActividadResponse.model_validate(actividad)


# Obtiene una actividad puntual por id, incluyendo los conferencistas
# actualmente asociados. Público, igual que el resto de los "get" de
# recursos de agenda.
@router.get("/{actividad_id}", response_model=ActividadResponse)
def get_actividad(actividad_id: int, db: Session = Depends(get_db)) -> ActividadResponse:
    actividad = _get_actividad_or_404(db, actividad_id)
    return ActividadResponse.model_validate(actividad)


# Asocia un conferencista a una actividad. Valida que ambos existan y que el
# conferencista no esté ya asociado (409 Conflict si ya lo está, para evitar
# asociaciones duplicadas silenciosas).
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
    conferencista = _get_conferencista_or_404(db, conferencista_id)

    if conferencista in actividad.conferencistas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El conferencista ya está asociado a esta actividad",
        )

    actividad.conferencistas.append(conferencista)
    db.commit()
    db.refresh(actividad)
    return ActividadResponse.model_validate(actividad)


# Desasocia un conferencista de una actividad. Valida que ambos existan y
# que la asociación exista (404 si el conferencista no estaba asociado a
# esta actividad).
@router.delete("/{actividad_id}/conferencistas/{conferencista_id}", status_code=status.HTTP_204_NO_CONTENT)
def disassociate_conferencista(
    actividad_id: int,
    conferencista_id: int,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> None:
    actividad = _get_actividad_or_404(db, actividad_id)
    conferencista = _get_conferencista_or_404(db, conferencista_id)

    if conferencista not in actividad.conferencistas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El conferencista no está asociado a esta actividad",
        )

    actividad.conferencistas.remove(conferencista)
    db.commit()
