from datetime import date

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.eventos import create_evento, list_eventos, update_evento
from app.db import Base
from app.models import TipoEvento
from app.schemas import EventoCreate, EventoUpdate, PoliticaInscripcionData


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def tipo_evento(db):
    tipo = TipoEvento(nombre="Congreso")
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo


def test_create_evento_persiste_con_estado_borrador_por_defecto(db, tipo_evento):
    data = EventoCreate(
        id_tipo_evento=tipo_evento.id_tipo_evento,
        nombre="Jornada de Software",
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 3, 2),
        cupo_maximo=50,
    )

    response = create_evento(data, db)

    assert response.id_evento is not None
    assert response.estado == "borrador"
    assert response.politica.permite_lista_espera is False
    assert response.politica.min_asistencia_certificado == 75


def test_evento_create_rechaza_fecha_fin_anterior_a_inicio():
    with pytest.raises(ValidationError):
        EventoCreate(
            id_tipo_evento=1,
            nombre="Evento invalido",
            fecha_inicio=date(2026, 3, 2),
            fecha_fin=date(2026, 3, 1),
            cupo_maximo=10,
        )


def test_create_evento_rechaza_tipo_evento_inexistente(db):
    data = EventoCreate(
        id_tipo_evento=999,
        nombre="Evento sin tipo",
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 3, 2),
        cupo_maximo=10,
    )

    with pytest.raises(HTTPException) as error:
        create_evento(data, db)

    assert error.value.status_code == 404


def test_list_eventos_filtra_por_estado(db, tipo_evento):
    create_evento(
        EventoCreate(
            id_tipo_evento=tipo_evento.id_tipo_evento,
            nombre="Borrador",
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 3, 2),
            cupo_maximo=10,
        ),
        db,
    )
    create_evento(
        EventoCreate(
            id_tipo_evento=tipo_evento.id_tipo_evento,
            nombre="Publicado",
            fecha_inicio=date(2026, 4, 1),
            fecha_fin=date(2026, 4, 2),
            cupo_maximo=10,
            estado="publicado",
        ),
        db,
    )

    resultado = list_eventos(db, estado="publicado")

    assert [evento.nombre for evento in resultado] == ["Publicado"]


def test_update_evento_rechaza_resultado_con_fecha_fin_anterior_a_inicio(db, tipo_evento):
    evento = create_evento(
        EventoCreate(
            id_tipo_evento=tipo_evento.id_tipo_evento,
            nombre="Evento",
            fecha_inicio=date(2026, 5, 1),
            fecha_fin=date(2026, 5, 5),
            cupo_maximo=10,
        ),
        db,
    )

    with pytest.raises(HTTPException) as error:
        update_evento(evento.id_evento, EventoUpdate(fecha_fin=date(2026, 4, 30)), db)

    assert error.value.status_code == 422


def test_update_evento_actualiza_politica_de_inscripcion(db, tipo_evento):
    evento = create_evento(
        EventoCreate(
            id_tipo_evento=tipo_evento.id_tipo_evento,
            nombre="Evento",
            fecha_inicio=date(2026, 5, 1),
            fecha_fin=date(2026, 5, 5),
            cupo_maximo=10,
        ),
        db,
    )

    actualizado = update_evento(
        evento.id_evento,
        EventoUpdate(politica=PoliticaInscripcionData(permite_lista_espera=True)),
        db,
    )

    assert actualizado.politica.permite_lista_espera is True


def test_update_evento_404_si_no_existe(db):
    with pytest.raises(HTTPException) as error:
        update_evento(999, EventoUpdate(nombre="No existe"), db)

    assert error.value.status_code == 404
