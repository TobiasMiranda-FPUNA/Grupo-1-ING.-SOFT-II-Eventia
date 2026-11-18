from datetime import date, time

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api import inscripciones as inscripciones_api
from app.api.eventos import create_evento
from app.api.inscripciones import create_inscripcion, descargar_tarjeta, reenviar_tarjeta
from app.core.config import settings
from app.db import Base
from app.models import Actividad, CategoriaActividad, RolParticipante, TipoEvento
from app.schemas import EventoCreate, InscripcionCreate, PoliticaInscripcionData
from app.services.correo import _armar_mensaje_tarjeta
from app.services.tarjeta_inscripcion_pdf import (
    ActividadTarjeta,
    DatosTarjeta,
    codigo_inscripcion,
    generar_tarjeta_inscripcion_pdf,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def correos(monkeypatch):
    # Simula un servidor SMTP configurado y captura los envíos.
    enviados = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from", "eventia@example.com")
    monkeypatch.setattr(
        inscripciones_api,
        "enviar_tarjeta_inscripcion",
        lambda destinatario, datos, pdf: enviados.append((destinatario, datos, pdf)),
    )
    return enviados


def _evento(db, cupo_maximo=5, permite_lista_espera=False):
    tipo = TipoEvento(nombre="Congreso")
    categoria = CategoriaActividad(nombre="Conferencia", activo=True)
    db.add_all([tipo, categoria])
    db.flush()
    evento = create_evento(
        EventoCreate(
            id_tipo_evento=tipo.id_tipo_evento,
            nombre="Congreso de prueba",
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 6, 2),
            lugar="Auditorio",
            cupo_maximo=cupo_maximo,
            estado="publicado",
            politica=PoliticaInscripcionData(permite_lista_espera=permite_lista_espera),
        ),
        db,
    )
    db.add(
        Actividad(
            id_evento=evento.id_evento,
            id_categoria=categoria.id_categoria,
            titulo="Charla de apertura",
            fecha=date(2026, 6, 1),
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            lugar="Sala A",
            modalidad="PRESENCIAL",
            cupo=50,
        )
    )
    rol = RolParticipante(nombre="Asistente", activo=True)
    db.add(rol)
    db.commit()
    return evento, rol


def _inscribir(db, evento, rol, email="hugo@example.com"):
    return create_inscripcion(
        InscripcionCreate(
            id_evento=evento.id_evento,
            id_rol_participante=rol.id_rol_participante,
            nombres="Hugo",
            apellidos="Villagra",
            email=email,
        ),
        db,
    )


def test_inscripcion_confirmada_envia_la_tarjeta(db, correos):
    evento, rol = _evento(db)

    respuesta = _inscribir(db, evento, rol)

    assert respuesta.envio_correo == "enviado"
    destinatario, datos, pdf = correos[0]
    assert destinatario == "hugo@example.com"
    assert datos.participante == "Hugo Villagra"
    assert datos.rol == "Asistente"
    assert [a.titulo for a in datos.actividades] == ["Charla de apertura"]
    assert pdf.startswith(b"%PDF")


def test_lista_de_espera_no_recibe_tarjeta(db, correos):
    evento, rol = _evento(db, cupo_maximo=1, permite_lista_espera=True)
    _inscribir(db, evento, rol, "primero@example.com")

    en_espera = _inscribir(db, evento, rol, "segundo@example.com")

    assert en_espera.estado == "lista_de_espera"
    assert en_espera.envio_correo is None
    assert len(correos) == 1


def test_sin_smtp_la_inscripcion_se_registra_igual(db):
    evento, rol = _evento(db)

    respuesta = _inscribir(db, evento, rol)

    assert respuesta.estado == "confirmada"
    assert respuesta.envio_correo == "no_configurado"


def test_fallo_del_correo_no_deshace_la_inscripcion(db, monkeypatch, correos):
    def falla(*_):
        raise inscripciones_api.CorreoError("SMTP caído")

    monkeypatch.setattr(inscripciones_api, "enviar_tarjeta_inscripcion", falla)
    evento, rol = _evento(db)

    respuesta = _inscribir(db, evento, rol)

    assert respuesta.estado == "confirmada"
    assert respuesta.envio_correo == "error"


def test_descargar_y_reenviar_tarjeta(db, correos):
    evento, rol = _evento(db)
    inscripcion = _inscribir(db, evento, rol)

    pdf = descargar_tarjeta(inscripcion.id_inscripcion, db, None)
    assert pdf.media_type == "application/pdf"
    assert pdf.body.startswith(b"%PDF")
    assert codigo_inscripcion(inscripcion.id_inscripcion) in pdf.headers["content-disposition"]

    reenviada = reenviar_tarjeta(inscripcion.id_inscripcion, db, None)
    assert reenviada.envio_correo == "enviado"
    assert len(correos) == 2


def test_tarjeta_de_lista_de_espera_devuelve_409(db, correos):
    evento, rol = _evento(db, cupo_maximo=1, permite_lista_espera=True)
    _inscribir(db, evento, rol, "primero@example.com")
    en_espera = _inscribir(db, evento, rol, "segundo@example.com")

    with pytest.raises(HTTPException) as error:
        descargar_tarjeta(en_espera.id_inscripcion, db, None)
    assert error.value.status_code == 409


def test_tarjeta_inexistente_devuelve_404(db):
    with pytest.raises(HTTPException) as error:
        descargar_tarjeta(999, db, None)
    assert error.value.status_code == 404


def test_codigo_y_mensaje_de_la_tarjeta():
    datos = DatosTarjeta(
        id_inscripcion=42,
        participante="Hugo Villagra",
        documento=None,
        institucion="FPUNA",
        rol="Asistente",
        evento="Congreso",
        fecha_inicio_evento=date(2026, 6, 1),
        fecha_fin_evento=date(2026, 6, 2),
        lugar_evento=None,
        actividades=[ActividadTarjeta("Charla", date(2026, 6, 1), time(9), time(10), None)],
    )
    assert codigo_inscripcion(42) == "INS-000042"

    pdf = generar_tarjeta_inscripcion_pdf(datos)
    mensaje = _armar_mensaje_tarjeta("hugo@example.com", datos, pdf)

    assert "INS-000042" in mensaje.get_body(preferencelist=("plain",)).get_content()
    adjuntos = list(mensaje.iter_attachments())
    assert adjuntos[0].get_filename() == "tarjeta-INS-000042.pdf"
    assert adjuntos[0].get_content().startswith(b"%PDF")
