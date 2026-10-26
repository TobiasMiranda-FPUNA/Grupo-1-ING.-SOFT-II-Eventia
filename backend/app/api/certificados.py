from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Certificado, Evento, Inscripcion, Participante
from app.schemas import CertificadoVerificacionResponse


router = APIRouter(
    prefix="/api/v1/certificados",
    tags=["Certificados"],
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
