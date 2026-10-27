from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.users import require_any_system_role
from app.db import get_db
from app.models import Actividad, Asistencia, Evento, Inscripcion, Participante, Usuario
from app.schemas import (
    AsistenciaCreate,
    AsistenciaGuardadoResponse,
    AsistenciaParticipanteResponse,
    AsistenciaRegistroMasivo,
    AsistenciaResponse,
)


router = APIRouter(
    prefix="/api/v1/asistencias",
    tags=["Asistencias"],
)

attendance_manager_required = Depends(
    require_any_system_role(
        "organizador",
        "administrador",
        "personal de acreditación",
    )
)


def _get_actividad_or_404(db: Session, id_actividad: int) -> Actividad:
    actividad = db.get(Actividad, id_actividad)
    if actividad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actividad no encontrada",
        )
    return actividad


# Registra la asistencia de una inscripción a una actividad, validando que
# la actividad y la inscripción pertenezcan al evento indicado.
@router.post(
    "",
    response_model=AsistenciaResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_asistencia(
    data: AsistenciaCreate,
    db: Session = Depends(get_db),
    _: Usuario = attendance_manager_required,
) -> AsistenciaResponse:
    if db.get(Evento, data.id_evento) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    actividad = _get_actividad_or_404(db, data.id_actividad)
    if actividad.id_evento != data.id_evento:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La actividad no pertenece al evento seleccionado",
        )

    inscripcion = db.get(Inscripcion, data.id_inscripcion)
    if inscripcion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inscripción no encontrada",
        )
    if inscripcion.id_evento != data.id_evento:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La inscripción no pertenece al evento seleccionado",
        )
    if inscripcion.estado != "confirmada":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Solo se puede registrar asistencia de inscripciones confirmadas",
        )

    existente = db.scalar(
        select(Asistencia).where(
            Asistencia.id_inscripcion == data.id_inscripcion,
            Asistencia.id_actividad == data.id_actividad,
        )
    )
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La asistencia ya fue registrada para esta actividad",
        )

    asistencia = Asistencia(
        id_inscripcion=data.id_inscripcion,
        id_actividad=data.id_actividad,
        estado=data.estado,
    )
    db.add(asistencia)
    db.commit()
    db.refresh(asistencia)

    return AsistenciaResponse.model_validate(asistencia)


@router.get(
    "/eventos/{id_evento}/actividades/{id_actividad}",
    response_model=list[AsistenciaParticipanteResponse],
)
def listar_participantes_actividad(
    id_evento: int,
    id_actividad: int,
    db: Session = Depends(get_db),
    _: Usuario = attendance_manager_required,
) -> list[AsistenciaParticipanteResponse]:
    actividad = _get_actividad_or_404(db, id_actividad)
    if actividad.id_evento != id_evento:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La actividad no pertenece al evento seleccionado",
        )

    rows = db.execute(
        select(Inscripcion, Participante)
        .join(
            Participante,
            Participante.id_participante == Inscripcion.id_participante,
        )
        .where(
            Inscripcion.id_evento == id_evento,
            Inscripcion.estado == "confirmada",
        )
        .order_by(Participante.apellidos, Participante.nombres)
    ).all()

    asistencias = {
        asistencia.id_inscripcion: asistencia.estado
        for asistencia in db.scalars(
            select(Asistencia).where(Asistencia.id_actividad == id_actividad)
        ).all()
    }

    return [
        AsistenciaParticipanteResponse(
            id_inscripcion=inscripcion.id_inscripcion,
            id_participante=participante.id_participante,
            participante=f"{participante.nombres} {participante.apellidos}".strip(),
            email=participante.email,
            estado_inscripcion=inscripcion.estado,
            estado_asistencia=asistencias.get(inscripcion.id_inscripcion),
        )
        for inscripcion, participante in rows
    ]


@router.post(
    "/actividades/{id_actividad}/registrar",
    response_model=AsistenciaGuardadoResponse,
)
def registrar_asistencia_masiva(
    id_actividad: int,
    data: AsistenciaRegistroMasivo,
    db: Session = Depends(get_db),
    _: Usuario = attendance_manager_required,
) -> AsistenciaGuardadoResponse:
    actividad = _get_actividad_or_404(db, id_actividad)

    ids = [item.id_inscripcion for item in data.registros]
    if len(ids) != len(set(ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La solicitud contiene inscripciones duplicadas",
        )

    inscripciones = {
        inscripcion.id_inscripcion: inscripcion
        for inscripcion in db.scalars(
            select(Inscripcion).where(Inscripcion.id_inscripcion.in_(ids))
        ).all()
    }

    for item in data.registros:
        inscripcion = inscripciones.get(item.id_inscripcion)
        if inscripcion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inscripción {item.id_inscripcion} no encontrada",
            )
        if inscripcion.id_evento != actividad.id_evento:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Todas las inscripciones deben pertenecer al evento de la actividad",
            )
        if inscripcion.estado != "confirmada":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Solo se puede registrar asistencia de inscripciones confirmadas",
            )

        asistencia = db.scalar(
            select(Asistencia).where(
                Asistencia.id_inscripcion == item.id_inscripcion,
                Asistencia.id_actividad == id_actividad,
            )
        )

        if asistencia is None:
            db.add(
                Asistencia(
                    id_inscripcion=item.id_inscripcion,
                    id_actividad=id_actividad,
                    estado=item.estado,
                )
            )
        else:
            asistencia.estado = item.estado

    db.commit()

    return AsistenciaGuardadoResponse(
        id_actividad=id_actividad,
        registros_guardados=len(data.registros),
    )
