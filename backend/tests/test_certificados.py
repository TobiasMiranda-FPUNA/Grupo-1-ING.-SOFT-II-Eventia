from datetime import date, time

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.certificados import (
    descargar_certificado,
    descargar_certificado_por_codigo,
    emitir_certificado,
    listar_estado_certificados_evento,
    verificar_certificado,
)
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
