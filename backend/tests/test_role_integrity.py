import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.roles import delete_participant_role
from app.models import Inscripcion, RolParticipante
from app.db import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_cannot_delete_role_with_active_registration(db):
    role = RolParticipante(nombre="Estudiante", activo=True)
    db.add(role)
    db.flush()
    db.add(Inscripcion(id_rol_participante=role.id_rol_participante, estado=" confirmada "))
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
    db.add(Inscripcion(id_rol_participante=role.id_rol_participante, estado="cancelada"))
    db.commit()

    delete_participant_role(role.id_rol_participante, db)

    assert db.get(RolParticipante, role.id_rol_participante) is None