from datetime import date, time

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.asistencias import (
    listar_participantes_actividad,
    registrar_asistencia,
    registrar_asistencia_masiva,
)
from app.db import Base
from app.models import (
    Actividad,
    Asistencia,
    CategoriaActividad,
    Evento,
    Inscripcion,
    Participante,
    RolParticipante,
    TipoEvento,
)
from app.schemas import AsistenciaCreate, AsistenciaRegistroItem, AsistenciaRegistroMasivo


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _datos(db: Session):
    tipo = TipoEvento(nombre="Congreso")
    categoria = CategoriaActividad(nombre="Conferencia", activo=True)
    rol = RolParticipante(nombre="Asistente", activo=True)
    db.add_all([tipo, categoria, rol])
    db.flush()

    evento = Evento(
        id_tipo_evento=tipo.id_tipo_evento,
        nombre="Evento",
        fecha_inicio=date(2026, 11, 10),
        fecha_fin=date(2026, 11, 11),
        cupo_maximo=10,
        estado="publicado",
    )
    db.add(evento)
    db.flush()

    actividad = Actividad(
        id_evento=evento.id_evento,
        id_categoria=categoria.id_categoria,
        titulo="Apertura",
        fecha=date(2026, 11, 10),
        hora_inicio=time(9, 0),
        hora_fin=time(10, 0),
        modalidad="PRESENCIAL",
        cupo=10,
    )
    participante = Participante(
        nombres="Ana",
        apellidos="Gómez",
        email="ana@example.com",
    )
    db.add_all([actividad, participante])
    db.flush()

    inscripcion = Inscripcion(
        id_evento=evento.id_evento,
        id_participante=participante.id_participante,
        id_rol_participante=rol.id_rol_participante,
        estado="confirmada",
    )
    db.add(inscripcion)
    db.commit()
    return evento, actividad, inscripcion


def test_listar_y_guardar_asistencia(db):
    evento, actividad, inscripcion = _datos(db)

    roster = listar_participantes_actividad(
        evento.id_evento,
        actividad.id_actividad,
        db,
        None,
    )
    assert len(roster) == 1
    assert roster[0].estado_asistencia is None

    response = registrar_asistencia_masiva(
        actividad.id_actividad,
        AsistenciaRegistroMasivo(
            registros=[
                AsistenciaRegistroItem(
                    id_inscripcion=inscripcion.id_inscripcion,
                    estado="presente",
                )
            ]
        ),
        db,
        None,
    )
    assert response.registros_guardados == 1

    asistencia = db.scalar(select(Asistencia))
    assert asistencia is not None
    assert asistencia.estado == "presente"

    # Guardar nuevamente actualiza el registro y no crea un duplicado.
    registrar_asistencia_masiva(
        actividad.id_actividad,
        AsistenciaRegistroMasivo(
            registros=[
                AsistenciaRegistroItem(
                    id_inscripcion=inscripcion.id_inscripcion,
                    estado="ausente",
                )
            ]
        ),
        db,
        None,
    )
    assert len(db.scalars(select(Asistencia)).all()) == 1
    assert db.scalar(select(Asistencia)).estado == "ausente"


def _otro_evento(db: Session, evento: Evento) -> Evento:
    otro = Evento(
        id_tipo_evento=evento.id_tipo_evento,
        nombre="Otro evento",
        fecha_inicio=date(2026, 12, 1),
        fecha_fin=date(2026, 12, 2),
        cupo_maximo=10,
        estado="publicado",
    )
    db.add(otro)
    db.commit()
    return otro


def test_registrar_asistencia_individual(db):
    evento, actividad, inscripcion = _datos(db)

    response = registrar_asistencia(
        AsistenciaCreate(
            id_evento=evento.id_evento,
            id_actividad=actividad.id_actividad,
            id_inscripcion=inscripcion.id_inscripcion,
        ),
        db,
        None,
    )
    assert response.estado == "presente"
    assert response.id_inscripcion == inscripcion.id_inscripcion
    assert response.id_actividad == actividad.id_actividad
    assert len(db.scalars(select(Asistencia)).all()) == 1


def test_registrar_asistencia_duplicada_devuelve_409(db):
    evento, actividad, inscripcion = _datos(db)
    data = AsistenciaCreate(
        id_evento=evento.id_evento,
        id_actividad=actividad.id_actividad,
        id_inscripcion=inscripcion.id_inscripcion,
    )
    registrar_asistencia(data, db, None)

    with pytest.raises(HTTPException) as exc:
        registrar_asistencia(data, db, None)
    assert exc.value.status_code == 409


def test_registrar_asistencia_actividad_de_otro_evento(db):
    evento, actividad, inscripcion = _datos(db)
    otro = _otro_evento(db, evento)

    with pytest.raises(HTTPException) as exc:
        registrar_asistencia(
            AsistenciaCreate(
                id_evento=otro.id_evento,
                id_actividad=actividad.id_actividad,
                id_inscripcion=inscripcion.id_inscripcion,
            ),
            db,
            None,
        )
    assert exc.value.status_code == 422
    assert "actividad no pertenece" in exc.value.detail


def test_registrar_asistencia_inscripcion_de_otro_evento(db):
    evento, actividad, inscripcion = _datos(db)
    otro = _otro_evento(db, evento)
    inscripcion.id_evento = otro.id_evento
    db.commit()

    with pytest.raises(HTTPException) as exc:
        registrar_asistencia(
            AsistenciaCreate(
                id_evento=evento.id_evento,
                id_actividad=actividad.id_actividad,
                id_inscripcion=inscripcion.id_inscripcion,
            ),
            db,
            None,
        )
    assert exc.value.status_code == 422
    assert "inscripción no pertenece" in exc.value.detail
    assert db.scalar(select(Asistencia)) is None


def test_registrar_asistencia_inscripcion_no_confirmada(db):
    evento, actividad, inscripcion = _datos(db)
    inscripcion.estado = "cancelada"
    db.commit()

    with pytest.raises(HTTPException) as exc:
        registrar_asistencia(
            AsistenciaCreate(
                id_evento=evento.id_evento,
                id_actividad=actividad.id_actividad,
                id_inscripcion=inscripcion.id_inscripcion,
            ),
            db,
            None,
        )
    assert exc.value.status_code == 422


@pytest.mark.parametrize("campo", ["id_evento", "id_actividad", "id_inscripcion"])
def test_registrar_asistencia_recurso_inexistente(db, campo):
    evento, actividad, inscripcion = _datos(db)
    ids = {
        "id_evento": evento.id_evento,
        "id_actividad": actividad.id_actividad,
        "id_inscripcion": inscripcion.id_inscripcion,
    }
    ids[campo] = 9999

    with pytest.raises(HTTPException) as exc:
        registrar_asistencia(AsistenciaCreate(**ids), db, None)
    assert exc.value.status_code == 404
