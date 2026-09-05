from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.roles import delete_participant_role
from app.models import Evento, Inscripcion, Participante, RolParticipante, TipoEvento
from app.db import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _crear_evento(db: Session) -> Evento:
    tipo = TipoEvento(nombre="Congreso")
    db.add(tipo)
    db.flush()
    evento = Evento(
        id_tipo_evento=tipo.id_tipo_evento,
        nombre="Evento de prueba",
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 1, 2),
        cupo_maximo=10,
    )
    db.add(evento)
    db.flush()
    return evento


def _crear_participante(db: Session, email: str) -> Participante:
    participante = Participante(nombres="Juan", apellidos="Perez", email=email)
    db.add(participante)
    db.flush()
    return participante


def test_cannot_delete_role_with_active_registration(db):
    role = RolParticipante(nombre="Estudiante", activo=True)
    db.add(role)
    db.flush()
    evento = _crear_evento(db)
    participante = _crear_participante(db, "estudiante@example.com")
    db.add(
        Inscripcion(
            id_evento=evento.id_evento,
            id_participante=participante.id_participante,
            id_rol_participante=role.id_rol_participante,
            estado=" confirmada ",
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as error:
        delete_participant_role(role.id_rol_participante, db)

    assert error.value.status_code == 409
    assert "inscripciones activas" in error.value.detail
    assert db.get(RolParticipante, role.id_rol_participante) is not None


def test_can_delete_role_without_active_registration(db):
    role = RolParticipante(nombre="Expositor", activo=True)
    db.add(role)
    db.flush()
    evento = _crear_evento(db)
    participante = _crear_participante(db, "expositor@example.com")
    db.add(
        Inscripcion(
            id_evento=evento.id_evento,
            id_participante=participante.id_participante,
            id_rol_participante=role.id_rol_participante,
            estado="cancelada",
        )
    )
    db.commit()

    delete_participant_role(role.id_rol_participante, db)

    assert db.get(RolParticipante, role.id_rol_participante) is None
