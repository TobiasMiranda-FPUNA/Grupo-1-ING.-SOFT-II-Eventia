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
    get_agenda_evento,
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


def _data(**overrides):
    base = dict(
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
    response = create_actividad(evento.id_evento, _data(), db)

    assert response.id_actividad is not None
    assert response.id_evento == evento.id_evento
    assert response.conferencistas == []


def test_actividad_create_rechaza_hora_fin_anterior_o_igual_a_inicio():
    with pytest.raises(ValidationError):
        ActividadCreate(
            nombre="Actividad inválida",
            fecha=date(2026, 3, 1),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 0),
        )


def test_create_actividad_rechaza_evento_inexistente(db):
    with pytest.raises(HTTPException) as error:
        create_actividad(999, _data(), db)

    assert error.value.status_code == 404


def test_create_actividad_rechaza_fecha_fuera_del_rango_del_evento(db, evento):
    # El evento va del 2026-03-01 al 2026-03-02 (ver fixture `evento`).
    data = _data(fecha=date(2026, 3, 3))

    with pytest.raises(HTTPException) as error:
        create_actividad(evento.id_evento, data, db)

    assert error.value.status_code == 422


def test_create_actividad_acepta_fecha_en_el_borde_del_rango_del_evento(db, evento):
    data = _data(fecha=evento.fecha_fin)

    response = create_actividad(evento.id_evento, data, db)

    assert response.fecha == evento.fecha_fin


def test_get_actividad_404_si_no_existe(db):
    with pytest.raises(HTTPException) as error:
        get_actividad(999, db)

    assert error.value.status_code == 404


def test_associate_conferencista_lo_asocia_a_la_actividad(db, evento, conferencista):
    actividad = create_actividad(evento.id_evento, _data(), db)

    response = associate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    assert [c.id_conferencista for c in response.conferencistas] == [conferencista.id_conferencista]
    assert [c.id_conferencista for c in get_actividad(actividad.id_actividad, db).conferencistas] == [
        conferencista.id_conferencista
    ]


def test_associate_conferencista_rechaza_asociacion_duplicada(db, evento, conferencista):
    actividad = create_actividad(evento.id_evento, _data(), db)
    associate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    with pytest.raises(HTTPException) as error:
        associate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    assert error.value.status_code == 409


def test_associate_conferencista_404_si_actividad_no_existe(db, conferencista):
    with pytest.raises(HTTPException) as error:
        associate_conferencista(999, conferencista.id_conferencista, db)

    assert error.value.status_code == 404


def test_associate_conferencista_404_si_conferencista_no_existe(db, evento):
    actividad = create_actividad(evento.id_evento, _data(), db)

    with pytest.raises(HTTPException) as error:
        associate_conferencista(actividad.id_actividad, 999, db)

    assert error.value.status_code == 404


def test_disassociate_conferencista_lo_quita_de_la_actividad(db, evento, conferencista):
    actividad = create_actividad(evento.id_evento, _data(), db)
    associate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    disassociate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    assert get_actividad(actividad.id_actividad, db).conferencistas == []


def test_disassociate_conferencista_404_si_no_estaba_asociado(db, evento, conferencista):
    actividad = create_actividad(evento.id_evento, _data(), db)

    with pytest.raises(HTTPException) as error:
        disassociate_conferencista(actividad.id_actividad, conferencista.id_conferencista, db)

    assert error.value.status_code == 404


def test_disassociate_conferencista_404_si_actividad_no_existe(db, conferencista):
    with pytest.raises(HTTPException) as error:
        disassociate_conferencista(999, conferencista.id_conferencista, db)

    assert error.value.status_code == 404


def test_get_agenda_evento_ordena_por_fecha_y_hora_inicio(db, evento):
    tarde_dia1 = create_actividad(
        evento.id_evento, _data(nombre="Tarde día 1", fecha=date(2026, 3, 1), hora_inicio=time(15, 0), hora_fin=time(16, 0)), db
    )
    manana_dia1 = create_actividad(
        evento.id_evento, _data(nombre="Mañana día 1", fecha=date(2026, 3, 1), hora_inicio=time(9, 0), hora_fin=time(10, 0)), db
    )
    dia2 = create_actividad(
        evento.id_evento, _data(nombre="Día 2", fecha=date(2026, 3, 2), hora_inicio=time(8, 0), hora_fin=time(9, 0)), db
    )

    agenda = get_agenda_evento(evento.id_evento, db)

    assert [a.id_actividad for a in agenda] == [
        manana_dia1.id_actividad,
        tarde_dia1.id_actividad,
        dia2.id_actividad,
    ]


def test_get_agenda_evento_vacia_si_no_tiene_actividades(db, evento):
    assert get_agenda_evento(evento.id_evento, db) == []


def test_get_agenda_evento_404_si_evento_no_existe(db):
    with pytest.raises(HTTPException) as error:
        get_agenda_evento(999, db)

    assert error.value.status_code == 404
