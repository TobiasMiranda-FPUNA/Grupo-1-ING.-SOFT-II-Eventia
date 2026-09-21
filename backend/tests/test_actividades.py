from datetime import date, time

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.actividades import (
    associate_conferencista,
    create_actividad,
    disassociate_conferencista,
    get_actividad,
)
from app.api.conferencistas import create_conferencista
from app.db import Base
from app.models import Evento, TipoEvento
from app.schemas import ActividadCreate, ConferencistaCreate


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def evento(db):
    tipo = TipoEvento(nombre="Congreso")
    db.add(tipo)
    db.flush()

    evento = Evento(
        id_tipo_evento=tipo.id_tipo_evento,
        nombre="Jornada de Software",
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 3, 2),
        cupo_maximo=50,
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


@pytest.fixture
def conferencista(db):
    return create_conferencista(
        ConferencistaCreate(nombres="Ada", apellidos="Lovelace", email="ada@example.test"), db
    )


def _data(evento, **overrides):
    base = dict(
        id_evento=evento.id_evento,
        nombre="Charla de apertura",
        descripcion="Introducción al evento",
        fecha=date(2026, 3, 1),
        hora_inicio=time(9, 0),
        hora_fin=time(10, 0),
        lugar="Auditorio principal",
    )
    base.update(overrides)
    return ActividadCreate(**base)


def test_create_actividad_persiste_sin_conferencistas(db, evento):
    response = create_actividad(_data(evento), db)

    assert response.id_actividad is not None
    assert response.id_evento == evento.id_evento
    assert response.conferencistas == []


def test_actividad_create_rechaza_hora_fin_anterior_o_igual_a_inicio(evento):
    with pytest.raises(ValidationError):
        ActividadCreate(
            id_evento=evento.id_evento,
            nombre="Actividad inválida",
            fecha=date(2026, 3, 1),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 0),
        )


def test_create_actividad_rechaza_evento_inexistente(db):
    data = ActividadCreate(
        id_evento=999,
        nombre="Actividad huérfana",
        fecha=date(2026, 3, 1),
        hora_inicio=time(9, 0),
        hora_fin=time(10, 0),
    )

    with pytest.raises(HTTPException) as error:
        create_actividad(data, db)

    assert error.value.status_code == 404


def test_get_actividad_404_si_no_existe(db):
    with pytest.raises(HTTPException) as error:
        get_actividad(999, db)

    assert error.value.status_code == 404


def test_associate_conferencista_lo_asocia_a_la_actividad(db, evento, conferencista):
    actividad = create_actividad(_data(evento), db)

    response = associate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    assert [c.id_conferencista for c in response.conferencistas] == [conferencista.id_conferencista]
    assert [c.id_conferencista for c in get_actividad(actividad.id_actividad, db).conferencistas] == [
        conferencista.id_conferencista
    ]


def test_associate_conferencista_rechaza_asociacion_duplicada(db, evento, conferencista):
    actividad = create_actividad(_data(evento), db)
    associate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    with pytest.raises(HTTPException) as error:
        associate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    assert error.value.status_code == 409


def test_associate_conferencista_404_si_actividad_no_existe(db, conferencista):
    with pytest.raises(HTTPException) as error:
        associate_conferencista(999, conferencista.id_conferencista, db)

    assert error.value.status_code == 404


def test_associate_conferencista_404_si_conferencista_no_existe(db, evento):
    actividad = create_actividad(_data(evento), db)

    with pytest.raises(HTTPException) as error:
        associate_conferencista(actividad.id_actividad, 999, db)

    assert error.value.status_code == 404


def test_disassociate_conferencista_lo_quita_de_la_actividad(db, evento, conferencista):
    actividad = create_actividad(_data(evento), db)
    associate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    disassociate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    assert get_actividad(actividad.id_actividad, db).conferencistas == []


def test_disassociate_conferencista_404_si_no_estaba_asociado(db, evento, conferencista):
    actividad = create_actividad(_data(evento), db)

    with pytest.raises(HTTPException) as error:
        disassociate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    assert error.value.status_code == 404


def test_disassociate_conferencista_404_si_actividad_no_existe(db, conferencista):
    with pytest.raises(HTTPException) as error:
        disassociate_conferencista(999, conferencista.id_conferencista, db)

    assert error.value.status_code == 404
