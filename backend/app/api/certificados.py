from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.users import require_any_system_role
from app.db import get_db
from app.models import (
    Actividad,
    Asistencia,
    Certificado,
    Evento,
    Inscripcion,
    Participante,
    Usuario,
)
from app.schemas import (
    CertificadoGestionResponse,
    CertificadoVerificacionResponse,
)


router = APIRouter(
    prefix="/api/v1/certificados",
    tags=["Certificados"],
)

certificate_manager_required = Depends(
    require_any_system_role("organizador", "administrador")
)


def _calcular_estado_certificado(
    db: Session,
    inscripcion: Inscripcion,
    participante: Participante,
    evento: Evento,
) -> CertificadoGestionResponse:
    total_actividades = db.scalar(
        select(func.count())
        .select_from(Actividad)
        .where(Actividad.id_evento == evento.id_evento)
    ) or 0

    presentes = db.scalar(
        select(func.count())
        .select_from(Asistencia)
        .join(Actividad, Actividad.id_actividad == Asistencia.id_actividad)
        .where(
            Asistencia.id_inscripcion == inscripcion.id_inscripcion,
            Asistencia.estado == "presente",
            Actividad.id_evento == evento.id_evento,
        )
    ) or 0

    porcentaje = round((presentes * 100 / total_actividades), 2) if total_actividades else 0.0
    minimo = (
        evento.politica.min_asistencia_certificado
        if evento.politica is not None
        else 75
    )
    elegible = (
        inscripcion.estado == "confirmada"
        and total_actividades > 0
        and porcentaje >= minimo
    )

    certificado = db.scalar(
        select(Certificado).where(
            Certificado.id_inscripcion == inscripcion.id_inscripcion
        )
    )

    return CertificadoGestionResponse(
        id_inscripcion=inscripcion.id_inscripcion,
        id_participante=participante.id_participante,
        participante=f"{participante.nombres} {participante.apellidos}".strip(),
        email=participante.email,
        estado_inscripcion=inscripcion.estado,
        actividades_evento=total_actividades,
        asistencias_presentes=presentes,
        porcentaje_asistencia=porcentaje,
        minimo_requerido=minimo,
        elegible=elegible,
        certificado_emitido=certificado is not None,
        codigo_validacion=certificado.codigo_validacion if certificado else None,
        fecha_emision=certificado.fecha_emision if certificado else None,
    )


@router.get(
    "/evento/{id_evento}/participantes",
    response_model=list[CertificadoGestionResponse],
)
def listar_estado_certificados_evento(
    id_evento: int,
    db: Session = Depends(get_db),
    _: Usuario = certificate_manager_required,
) -> list[CertificadoGestionResponse]:
    evento = db.get(Evento, id_evento)
    if evento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    rows = db.execute(
        select(Inscripcion, Participante)
        .join(
            Participante,
            Participante.id_participante == Inscripcion.id_participante,
        )
        .where(Inscripcion.id_evento == id_evento)
        .order_by(Participante.apellidos, Participante.nombres)
    ).all()

    return [
        _calcular_estado_certificado(db, inscripcion, participante, evento)
        for inscripcion, participante in rows
    ]


@router.post(
    "/emitir/{id_inscripcion}",
    response_model=CertificadoGestionResponse,
)
def emitir_certificado(
    id_inscripcion: int,
    db: Session = Depends(get_db),
    _: Usuario = certificate_manager_required,
) -> CertificadoGestionResponse:
    row = db.execute(
        select(Inscripcion, Participante, Evento)
        .join(
            Participante,
            Participante.id_participante == Inscripcion.id_participante,
        )
        .join(
            Evento,
            Evento.id_evento == Inscripcion.id_evento,
        )
        .where(Inscripcion.id_inscripcion == id_inscripcion)
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inscripción no encontrada",
        )

    inscripcion, participante, evento = row
    estado_actual = _calcular_estado_certificado(
        db,
        inscripcion,
        participante,
        evento,
    )

    if estado_actual.certificado_emitido:
        return estado_actual

    if not estado_actual.elegible:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El participante todavía no cumple el porcentaje mínimo "
                f"de asistencia ({estado_actual.minimo_requerido}%)."
            ),
        )

    certificado = Certificado(
        id_inscripcion=inscripcion.id_inscripcion,
        tipo="participacion",
    )
    db.add(certificado)
    db.commit()
    db.refresh(certificado)

    return _calcular_estado_certificado(
        db,
        inscripcion,
        participante,
        evento,
    )


@router.get(
    "/verificar/{codigo}",
    response_model=CertificadoVerificacionResponse,
)
def verificar_certificado(
    codigo: str,
    db: Session = Depends(get_db),
) -> CertificadoVerificacionResponse:
    codigo_normalizado = codigo.strip().upper()

    row = db.execute(
        select(Certificado, Inscripcion, Participante, Evento)
        .join(
            Inscripcion,
            Inscripcion.id_inscripcion == Certificado.id_inscripcion,
        )
        .join(
            Participante,
            Participante.id_participante == Inscripcion.id_participante,
        )
        .join(
            Evento,
            Evento.id_evento == Inscripcion.id_evento,
        )
        .where(
            func.upper(Certificado.codigo_validacion) == codigo_normalizado
        )
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado o código de validación inválido",
        )

    certificado, inscripcion, participante, evento = row

    return CertificadoVerificacionResponse(
        codigo_validacion=certificado.codigo_validacion,
        tipo=certificado.tipo,
        fecha_emision=certificado.fecha_emision,
        id_inscripcion=inscripcion.id_inscripcion,
        participante=f"{participante.nombres} {participante.apellidos}".strip(),
        evento=evento.nombre,
        fecha_inicio_evento=evento.fecha_inicio,
        fecha_fin_evento=evento.fecha_fin,
    )
