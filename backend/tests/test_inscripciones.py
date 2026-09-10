from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.eventos import create_evento
from app.api.inscripciones import create_inscripcion
from app.db import Base
from app.models import RolParticipante, TipoEvento
from app.schemas import EventoCreate, InscripcionCreate, PoliticaInscripcionData


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def rol_asistente(db):
    rol = RolParticipante(nombre="Asistente", activo=True)
    db.add(rol)
    db.commit()
    db.refresh(rol)
    return rol


def _crear_evento(db, cupo_maximo=1, permite_lista_espera=False, nombre="Evento de prueba"):
    tipo = db.query(TipoEvento).filter_by(nombre="Congreso").first()
    if tipo is None:
        tipo = TipoEvento(nombre="Congreso")
        db.add(tipo)
        db.flush()
    return create_evento(
        EventoCreate(
            id_tipo_evento=tipo.id_tipo_evento,
            nombre=nombre,
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 6, 2),
            cupo_maximo=cupo_maximo,
            politica=PoliticaInscripcionData(permite_lista_espera=permite_lista_espera),
        ),
        db,
    )


def _inscripcion(id_evento, id_rol_participante, email, nombres="Ana", apellidos="Gomez"):
    return InscripcionCreate(
        id_evento=id_evento,
        id_rol_participante=id_rol_participante,
        nombres=nombres,
        apellidos=apellidos,
        email=email,
    )


def test_create_inscripcion_confirma_cuando_hay_cupo_disponible(db, rol_asistente):
    evento = _crear_evento(db, cupo_maximo=5)

    response = create_inscripcion(
        _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "ana.gomez@example.com"),
        db,
    )

    assert response.estado == "confirmada"
    assert response.id_evento == evento.id_evento


def test_create_inscripcion_rechaza_duplicado_del_mismo_participante(db, rol_asistente):
    evento = _crear_evento(db, cupo_maximo=5)
    payload = _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "ana.gomez@example.com")
    create_inscripcion(payload, db)

    with pytest.raises(HTTPException) as error:
        create_inscripcion(payload, db)

    assert error.value.status_code == 409


def test_create_inscripcion_va_a_lista_de_espera_cuando_se_agota_el_cupo(db, rol_asistente):
    evento = _crear_evento(db, cupo_maximo=1, permite_lista_espera=True)
    create_inscripcion(
        _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "ana.gomez@example.com"),
        db,
    )

    response = create_inscripcion(
        _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "luis.diaz@example.com", "Luis", "Diaz"),
        db,
    )

    assert response.estado == "lista_de_espera"


def test_create_inscripcion_rechaza_sin_cupo_ni_lista_de_espera(db, rol_asistente):
    evento = _crear_evento(db, cupo_maximo=1, permite_lista_espera=False)
    create_inscripcion(
        _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "ana.gomez@example.com"),
        db,
    )

    with pytest.raises(HTTPException) as error:
        create_inscripcion(
            _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "luis.diaz@example.com", "Luis", "Diaz"),
            db,
        )

    assert error.value.status_code == 409


def test_create_inscripcion_404_si_evento_no_existe(db, rol_asistente):
    with pytest.raises(HTTPException) as error:
        create_inscripcion(
            _inscripcion(999, rol_asistente.id_rol_participante, "ana.gomez@example.com"),
            db,
        )

    assert error.value.status_code == 404


def test_create_inscripcion_404_si_rol_no_existe(db):
    evento = _crear_evento(db)

    with pytest.raises(HTTPException) as error:
        create_inscripcion(_inscripcion(evento.id_evento, 999, "ana.gomez@example.com"), db)

    assert error.value.status_code == 404


def test_create_inscripcion_reutiliza_participante_existente_por_email(db, rol_asistente):
    primer_evento = _crear_evento(db, cupo_maximo=5, nombre="Evento A")
    segundo_evento = _crear_evento(db, cupo_maximo=5, nombre="Evento B")

    primera = create_inscripcion(
        _inscripcion(primer_evento.id_evento, rol_asistente.id_rol_participante, "ana.gomez@example.com"),
        db,
    )
    segunda = create_inscripcion(
        _inscripcion(segundo_evento.id_evento, rol_asistente.id_rol_participante, "ANA.GOMEZ@example.com"),
        db,
    )

    assert primera.id_participante == segunda.id_participante
