import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.users import require_any_system_role
from app.db import get_db
from app.models import (
    Certificado,
    Evento,
    Inscripcion,
    Participante,
    Usuario,
)
from app.schemas import (
    CertificadoGestionResponse,
    CertificadoVerificacionResponse,
    EnvioCertificadosEventoResponse,
    MiCertificadoResponse,
)
from app.services.asistencia import (
    ResumenAsistencia,
    calcular_porcentaje_asistencia,
    calcular_porcentajes_evento,
)
from app.services.certificado_pdf import DatosCertificado, generar_certificado_pdf
from app.services.correo import CorreoError, correo_configurado, enviar_certificado


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/certificados",
    tags=["Certificados"],
)

certificate_manager_required = Depends(
    require_any_system_role("organizador", "administrador")
)

participant_required = Depends(require_any_system_role("participante"))


def _calcular_estado_certificado(
    db: Session,
    inscripcion: Inscripcion,
    participante: Participante,
    evento: Evento,
    resumen: ResumenAsistencia | None = None,
) -> CertificadoGestionResponse:
    if resumen is None:
        resumen = calcular_porcentaje_asistencia(db, inscripcion)

    total_actividades = resumen.total_actividades
    porcentaje = resumen.porcentaje
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
        asistencias_presentes=resumen.presentes,
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

    resumenes = calcular_porcentajes_evento(db, id_evento)

    return [
        _calcular_estado_certificado(
            db,
            inscripcion,
            participante,
            evento,
            resumenes[inscripcion.id_inscripcion],
        )
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

    certificado = _crear_certificado(db, inscripcion)
    envio = _enviar_por_correo(db, (certificado, inscripcion, participante, evento))

    respuesta = _calcular_estado_certificado(
        db,
        inscripcion,
        participante,
        evento,
    )
    respuesta.envio_correo = envio
    return respuesta


def _crear_certificado(db: Session, inscripcion: Inscripcion) -> Certificado:
    certificado = Certificado(
        id_inscripcion=inscripcion.id_inscripcion,
        tipo="participacion",
    )
    db.add(certificado)
    db.commit()
    db.refresh(certificado)
    return certificado


def _get_certificado_emitido(db: Session, *condiciones):
    return db.execute(
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
        .where(*condiciones)
    ).first()


def _get_certificado_por_codigo_or_404(db: Session, codigo: str):
    row = _get_certificado_emitido(
        db,
        func.upper(Certificado.codigo_validacion) == codigo.strip().upper(),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado o código de validación inválido",
        )
    return row


def _datos_certificado(db: Session, row) -> DatosCertificado:
    certificado, inscripcion, participante, evento = row
    resumen = calcular_porcentaje_asistencia(db, inscripcion)
    return DatosCertificado(
        codigo_validacion=certificado.codigo_validacion,
        tipo=certificado.tipo,
        fecha_emision=certificado.fecha_emision,
        participante=f"{participante.nombres} {participante.apellidos}".strip(),
        evento=evento.nombre,
        fecha_inicio_evento=evento.fecha_inicio,
        fecha_fin_evento=evento.fecha_fin,
        porcentaje_asistencia=resumen.porcentaje,
    )


# Envía el certificado en PDF al correo del participante. Nunca lanza: un
# fallo del servidor de correo no debe deshacer la emisión del certificado.
def _enviar_por_correo(db: Session, row) -> str:
    if not correo_configurado():
        return "no_configurado"

    participante = row[2]
    datos = _datos_certificado(db, row)
    try:
        enviar_certificado(participante.email, datos, generar_certificado_pdf(datos))
    except CorreoError:
        logger.exception(
            "No se pudo enviar el certificado %s a %s",
            datos.codigo_validacion,
            participante.email,
        )
        return "error"
    return "enviado"


def _respuesta_pdf(db: Session, row) -> Response:
    certificado = row[0]
    contenido = generar_certificado_pdf(_datos_certificado(db, row))

    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="certificado-{certificado.codigo_validacion}.pdf"'
            ),
        },
    )


# Descarga el PDF de un certificado ya emitido (gestión interna).
@router.get(
    "/inscripcion/{id_inscripcion}/documento",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def descargar_certificado(
    id_inscripcion: int,
    db: Session = Depends(get_db),
    _: Usuario = certificate_manager_required,
) -> Response:
    row = _get_certificado_emitido(
        db,
        Certificado.id_inscripcion == id_inscripcion,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La inscripción no tiene un certificado emitido",
        )
    return _respuesta_pdf(db, row)


# Reenvía por correo un certificado ya emitido.
@router.post(
    "/inscripcion/{id_inscripcion}/enviar",
    response_model=CertificadoGestionResponse,
)
def reenviar_certificado(
    id_inscripcion: int,
    db: Session = Depends(get_db),
    _: Usuario = certificate_manager_required,
) -> CertificadoGestionResponse:
    row = _get_certificado_emitido(
        db,
        Certificado.id_inscripcion == id_inscripcion,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La inscripción no tiene un certificado emitido",
        )
    if not correo_configurado():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El envío de correos no está configurado en el servidor (SMTP).",
        )

    envio = _enviar_por_correo(db, row)
    if envio == "error":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El servidor de correo no pudo enviar el certificado.",
        )

    _, inscripcion, participante, evento = row
    respuesta = _calcular_estado_certificado(db, inscripcion, participante, evento)
    respuesta.envio_correo = envio
    return respuesta


# Emite y envía por correo el certificado de todos los participantes que
# culminaron el evento: el evento ya finalizó y cumplieron la asistencia
# mínima. Los que ya tenían certificado no se vuelven a procesar.
@router.post(
    "/evento/{id_evento}/emitir-y-enviar",
    response_model=EnvioCertificadosEventoResponse,
)
def emitir_y_enviar_certificados_evento(
    id_evento: int,
    db: Session = Depends(get_db),
    _: Usuario = certificate_manager_required,
) -> EnvioCertificadosEventoResponse:
    evento = db.get(Evento, id_evento)
    if evento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )
    if evento.fecha_fin >= date.today():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El evento todavía no finalizó; los certificados se envían al culminar.",
        )

    pendientes = [
        estado
        for estado in listar_estado_certificados_evento(id_evento, db, _)
        if estado.elegible and not estado.certificado_emitido
    ]

    procesados: list[CertificadoGestionResponse] = []
    for estado in pendientes:
        inscripcion = db.get(Inscripcion, estado.id_inscripcion)
        participante = db.get(Participante, estado.id_participante)
        certificado = _crear_certificado(db, inscripcion)
        envio = _enviar_por_correo(db, (certificado, inscripcion, participante, evento))

        respuesta = _calcular_estado_certificado(db, inscripcion, participante, evento)
        respuesta.envio_correo = envio
        procesados.append(respuesta)

    return EnvioCertificadosEventoResponse(
        emitidos=len(procesados),
        enviados=sum(p.envio_correo == "enviado" for p in procesados),
        con_error=sum(p.envio_correo == "error" for p in procesados),
        sin_configurar=sum(p.envio_correo == "no_configurado" for p in procesados),
        certificados=procesados,
    )


# Descarga pública del PDF a partir del código de validación, para que el
# participante (que no tiene cuenta en el sistema) obtenga su certificado.
@router.get(
    "/verificar/{codigo}/documento",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def descargar_certificado_por_codigo(
    codigo: str,
    db: Session = Depends(get_db),
) -> Response:
    return _respuesta_pdf(db, _get_certificado_por_codigo_or_404(db, codigo))


# Verificación pública de autenticidad mediante el código de validación.
@router.get(
    "/verificar/{codigo}",
    response_model=CertificadoVerificacionResponse,
)
def verificar_certificado(
    codigo: str,
    db: Session = Depends(get_db),
) -> CertificadoVerificacionResponse:
    certificado, inscripcion, participante, evento = (
        _get_certificado_por_codigo_or_404(db, codigo)
    )

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


# ============================================================
# MIS CERTIFICADOS (participante con sesión)
# ============================================================

# El participante se identifica por el correo de su cuenta, el mismo con
# el que se inscribe (ver _con_datos_de_cuenta en inscripciones.py).
def _del_participante(usuario: Usuario):
    return func.lower(Participante.email) == usuario.email.strip().lower()


# Lista todas las inscripciones del participante en sesión con el estado
# de su certificado: asistencia frente al mínimo, si ya fue emitido y su
# código. Solo devuelve inscripciones propias.
@router.get("/mios", response_model=list[MiCertificadoResponse])
def listar_mis_certificados(
    db: Session = Depends(get_db),
    usuario: Usuario = participant_required,
) -> list[MiCertificadoResponse]:
    rows = db.execute(
        select(Inscripcion, Participante, Evento)
        .join(Participante, Participante.id_participante == Inscripcion.id_participante)
        .join(Evento, Evento.id_evento == Inscripcion.id_evento)
        .where(_del_participante(usuario))
        .order_by(Evento.fecha_inicio.desc(), Evento.nombre)
    ).all()

    return [
        MiCertificadoResponse(
            **_calcular_estado_certificado(db, inscripcion, participante, evento).model_dump(),
            id_evento=evento.id_evento,
            evento=evento.nombre,
            fecha_inicio_evento=evento.fecha_inicio,
            fecha_fin_evento=evento.fecha_fin,
        )
        for inscripcion, participante, evento in rows
    ]


# Descarga el PDF de un certificado propio. Si la inscripción es de otra
# persona responde 404, igual que si no existiera, para no revelar nada.
@router.get(
    "/mios/{id_inscripcion}/documento",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def descargar_mi_certificado(
    id_inscripcion: int,
    db: Session = Depends(get_db),
    usuario: Usuario = participant_required,
) -> Response:
    row = _get_certificado_emitido(
        db,
        Certificado.id_inscripcion == id_inscripcion,
        _del_participante(usuario),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tenés un certificado emitido para esta inscripción",
        )
    return _respuesta_pdf(db, row)
