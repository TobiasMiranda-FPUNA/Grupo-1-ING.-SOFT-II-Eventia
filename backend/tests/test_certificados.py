from datetime import date, time

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api import certificados as certificados_api
from app.api.certificados import (
    descargar_certificado,
    descargar_certificado_por_codigo,
    emitir_certificado,
    emitir_y_enviar_certificados_evento,
    reenviar_certificado,
    listar_estado_certificados_evento,
    verificar_certificado,
)
from app.core.config import settings
from app.db import Base
from app.models import (
    Actividad,
    Asistencia,
    CategoriaActividad,
    Evento,
    Inscripcion,
    Participante,
    PoliticaInscripcion,
    RolParticipante,
    TipoEvento,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _escenario(db: Session, minimo: int = 50):
    tipo = TipoEvento(nombre="Congreso")
    categoria = CategoriaActividad(nombre="Conferencia", activo=True)
    rol = RolParticipante(nombre="Asistente", activo=True)
    db.add_all([tipo, categoria, rol])
    db.flush()

    evento = Evento(
        id_tipo_evento=tipo.id_tipo_evento,
        nombre="Evento certificable",
        fecha_inicio=date(2026, 11, 10),
        fecha_fin=date(2026, 11, 11),
        cupo_maximo=10,
        estado="publicado",
    )
    db.add(evento)
    db.flush()
    db.add(
        PoliticaInscripcion(
            id_evento=evento.id_evento,
            min_asistencia_certificado=minimo,
            permite_lista_espera=True,
        )
    )

    actividades = [
        Actividad(
            id_evento=evento.id_evento,
            id_categoria=categoria.id_categoria,
            titulo=f"Actividad {n}",
            fecha=date(2026, 11, 10),
            hora_inicio=time(8 + n, 0),
            hora_fin=time(9 + n, 0),
            modalidad="PRESENCIAL",
            cupo=10,
        )
        for n in (1, 2)
    ]
    participante = Participante(
        nombres="Ana",
        apellidos="Gómez",
        email="ana@example.com",
    )
    db.add_all([*actividades, participante])
    db.flush()

    inscripcion = Inscripcion(
        id_evento=evento.id_evento,
        id_participante=participante.id_participante,
        id_rol_participante=rol.id_rol_participante,
        estado="confirmada",
    )
    db.add(inscripcion)
    db.flush()

    db.add(
        Asistencia(
            id_inscripcion=inscripcion.id_inscripcion,
            id_actividad=actividades[0].id_actividad,
            estado="presente",
        )
    )
    db.commit()
    return evento, inscripcion


def test_certificado_se_emite_al_cumplir_minimo_y_se_verifica(db):
    evento, inscripcion = _escenario(db, minimo=50)

    listado = listar_estado_certificados_evento(evento.id_evento, db, None)
    assert listado[0].porcentaje_asistencia == 50
    assert listado[0].elegible is True
    assert listado[0].certificado_emitido is False

    emitido = emitir_certificado(inscripcion.id_inscripcion, db, None)
    assert emitido.certificado_emitido is True
    assert emitido.codigo_validacion
    assert len(emitido.codigo_validacion) == 32

    verificado = verificar_certificado(emitido.codigo_validacion.lower(), db)
    assert verificado.valido is True
    assert verificado.participante == "Ana Gómez"


def test_certificado_rechaza_si_no_cumple_minimo(db):
    _, inscripcion = _escenario(db, minimo=100)

    with pytest.raises(HTTPException) as error:
        emitir_certificado(inscripcion.id_inscripcion, db, None)

    assert error.value.status_code == 409


def test_descarga_pdf_de_certificado_emitido(db):
    _, inscripcion = _escenario(db, minimo=50)
    emitido = emitir_certificado(inscripcion.id_inscripcion, db, None)

    response = descargar_certificado(inscripcion.id_inscripcion, db, None)
    assert response.media_type == "application/pdf"
    assert response.body.startswith(b"%PDF")
    assert emitido.codigo_validacion in response.headers["content-disposition"]

    # La descarga pública por código devuelve el mismo documento.
    publico = descargar_certificado_por_codigo(emitido.codigo_validacion.lower(), db)
    assert publico.body.startswith(b"%PDF")


def test_descarga_pdf_sin_certificado_emitido_devuelve_404(db):
    _, inscripcion = _escenario(db, minimo=50)

    with pytest.raises(HTTPException) as error:
        descargar_certificado(inscripcion.id_inscripcion, db, None)
    assert error.value.status_code == 404


@pytest.mark.parametrize("operacion", [verificar_certificado, descargar_certificado_por_codigo])
def test_codigo_invalido_devuelve_404(db, operacion):
    with pytest.raises(HTTPException) as error:
        operacion("NOEXISTE", db)
    assert error.value.status_code == 404


@pytest.fixture
def correos(monkeypatch):
    # Simula un servidor SMTP configurado y captura los envíos.
    enviados = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from", "eventia@example.com")
    monkeypatch.setattr(
        certificados_api,
        "enviar_certificado",
        lambda destinatario, datos, pdf: enviados.append((destinatario, datos, pdf)),
    )
    return enviados


def test_emitir_sin_smtp_emite_igual_e_informa_no_configurado(db, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)
    _, inscripcion = _escenario(db, minimo=50)

    emitido = emitir_certificado(inscripcion.id_inscripcion, db, None)

    assert emitido.certificado_emitido is True
    assert emitido.envio_correo == "no_configurado"


def test_emitir_envia_el_pdf_al_correo_del_participante(db, correos):
    _, inscripcion = _escenario(db, minimo=50)

    emitido = emitir_certificado(inscripcion.id_inscripcion, db, None)

    assert emitido.envio_correo == "enviado"
    destinatario, datos, pdf = correos[0]
    assert destinatario == "ana@example.com"
    assert datos.codigo_validacion == emitido.codigo_validacion
    assert pdf.startswith(b"%PDF")


def test_fallo_del_correo_no_deshace_la_emision(db, monkeypatch, correos):
    def falla(*_):
        raise certificados_api.CorreoError("SMTP caído")

    monkeypatch.setattr(certificados_api, "enviar_certificado", falla)
    _, inscripcion = _escenario(db, minimo=50)

    emitido = emitir_certificado(inscripcion.id_inscripcion, db, None)

    assert emitido.certificado_emitido is True
    assert emitido.envio_correo == "error"


def test_reenviar_certificado(db, correos):
    _, inscripcion = _escenario(db, minimo=50)
    emitir_certificado(inscripcion.id_inscripcion, db, None)

    reenviado = reenviar_certificado(inscripcion.id_inscripcion, db, None)

    assert reenviado.envio_correo == "enviado"
    assert len(correos) == 2


def test_reenviar_sin_certificado_devuelve_404(db, correos):
    _, inscripcion = _escenario(db, minimo=50)

    with pytest.raises(HTTPException) as error:
        reenviar_certificado(inscripcion.id_inscripcion, db, None)
    assert error.value.status_code == 404


def test_emitir_y_enviar_evento_finalizado(db, correos):
    evento, inscripcion = _escenario(db, minimo=50)
    evento.fecha_fin = date(2020, 1, 1)
    db.commit()

    resultado = emitir_y_enviar_certificados_evento(evento.id_evento, db, None)

    assert resultado.emitidos == 1
    assert resultado.enviados == 1
    assert resultado.certificados[0].id_inscripcion == inscripcion.id_inscripcion

    # Una segunda ejecución no vuelve a emitir ni a enviar.
    repetido = emitir_y_enviar_certificados_evento(evento.id_evento, db, None)
    assert repetido.emitidos == 0
    assert len(correos) == 1


def test_emitir_y_enviar_rechaza_evento_no_finalizado(db, correos):
    evento, _ = _escenario(db, minimo=50)
    evento.fecha_fin = date(2999, 1, 1)
    db.commit()

    with pytest.raises(HTTPException) as error:
        emitir_y_enviar_certificados_evento(evento.id_evento, db, None)
    assert error.value.status_code == 409


def test_emitir_y_enviar_omite_no_elegibles(db, correos):
    evento, _ = _escenario(db, minimo=100)
    evento.fecha_fin = date(2020, 1, 1)
    db.commit()

    resultado = emitir_y_enviar_certificados_evento(evento.id_evento, db, None)

    assert resultado.emitidos == 0
    assert correos == []
