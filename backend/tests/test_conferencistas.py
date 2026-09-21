import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.conferencistas import (
    create_conferencista,
    delete_conferencista,
    get_conferencista,
    list_conferencistas,
    update_conferencista,
)
from app.db import Base
from app.schemas import ConferencistaCreate, ConferencistaUpdate


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _data(**overrides):
    base = dict(
        nombres="Ada",
        apellidos="Lovelace",
        email="ada@example.test",
        institucion="Universidad Nacional",
        especialidad="Ciencias de la computación",
        biografia="Pionera de la programación.",
    )
    base.update(overrides)
    return ConferencistaCreate(**base)


def test_create_conferencista_persiste_con_activo_por_defecto(db):
    response = create_conferencista(_data(), db)

    assert response.id_conferencista is not None
    assert response.activo is True
    assert response.email == "ada@example.test"


def test_create_conferencista_rechaza_email_duplicado(db):
    create_conferencista(_data(), db)

    with pytest.raises(HTTPException) as error:
        create_conferencista(_data(nombres="Otra", email="ADA@example.test"), db)

    assert error.value.status_code == 409


def test_list_conferencistas_filtra_por_texto(db):
    create_conferencista(_data(), db)
    create_conferencista(_data(nombres="Alan", apellidos="Turing", email="alan@example.test"), db)

    resultado = list_conferencistas(db, q="turing", activo=None)

    assert [c.apellidos for c in resultado] == ["Turing"]


def test_get_conferencista_404_si_no_existe(db):
    with pytest.raises(HTTPException) as error:
        get_conferencista(999, db)

    assert error.value.status_code == 404


def test_update_conferencista_actualiza_campos_parciales(db):
    creado = create_conferencista(_data(), db)

    actualizado = update_conferencista(
        creado.id_conferencista,
        ConferencistaUpdate(institucion="Otra institución", activo=False),
        db,
    )

    assert actualizado.institucion == "Otra institución"
    assert actualizado.activo is False
    assert actualizado.nombres == "Ada"


def test_update_conferencista_rechaza_email_duplicado(db):
    create_conferencista(_data(), db)
    otro = create_conferencista(_data(nombres="Alan", apellidos="Turing", email="alan@example.test"), db)

    with pytest.raises(HTTPException) as error:
        update_conferencista(otro.id_conferencista, ConferencistaUpdate(email="ADA@example.test"), db)

    assert error.value.status_code == 409


def test_update_conferencista_404_si_no_existe(db):
    with pytest.raises(HTTPException) as error:
        update_conferencista(999, ConferencistaUpdate(nombres="No existe"), db)

    assert error.value.status_code == 404


def test_delete_conferencista_lo_elimina(db):
    creado = create_conferencista(_data(), db)

    delete_conferencista(creado.id_conferencista, db)

    with pytest.raises(HTTPException) as error:
        get_conferencista(creado.id_conferencista, db)
    assert error.value.status_code == 404


def test_delete_conferencista_404_si_no_existe(db):
    with pytest.raises(HTTPException) as error:
        delete_conferencista(999, db)

    assert error.value.status_code == 404
