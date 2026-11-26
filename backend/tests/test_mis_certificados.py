import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.certificados import descargar_mi_certificado, emitir_certificado, listar_mis_certificados
from app.core.security import create_access_token, hash_password
from app.db import Base, get_db
from app.main import app
from app.models import Inscripcion, Participante, RolSistema, Usuario
from tests.test_certificados import _escenario


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _cuenta(db, email, rol="participante"):
    role = db.query(RolSistema).filter_by(nombre=rol).first() or RolSistema(nombre=rol, activo=True)
    usuario = Usuario(nombres="X", apellidos="Y", email=email, password_hash=hash_password("Clave1234"), roles=[role])
    db.add(usuario)
    db.commit()
    return usuario


def _otra_inscripcion(db, evento, inscripcion, email):
    otro = Participante(nombres="Beto", apellidos="Ruiz", email=email)
    db.add(otro)
    db.flush()
    ajena = Inscripcion(
        id_evento=evento.id_evento,
        id_participante=otro.id_participante,
        id_rol_participante=inscripcion.id_rol_participante,
        estado="confirmada",
    )
    db.add(ajena)
    db.commit()
    return ajena


def test_lista_solo_las_inscripciones_propias_con_su_estado(db):
    evento, inscripcion = _escenario(db, minimo=50)
    _otra_inscripcion(db, evento, inscripcion, "beto@example.com")
    ana = _cuenta(db, "ANA@example.com")  # el correo se compara sin mayúsculas

    antes = listar_mis_certificados(db, ana)
    assert len(antes) == 1
    assert antes[0].evento == "Evento certificable"
    assert antes[0].porcentaje_asistencia == 50
    assert antes[0].elegible is True
    assert antes[0].certificado_emitido is False

    emitir_certificado(inscripcion.id_inscripcion, db, None)

    despues = listar_mis_certificados(db, ana)
    assert despues[0].certificado_emitido is True
    assert despues[0].codigo_validacion


def test_participante_sin_inscripciones_ve_lista_vacia(db):
    _escenario(db)
    assert listar_mis_certificados(db, _cuenta(db, "nadie@example.com")) == []


def test_descarga_su_certificado_en_pdf(db):
    _, inscripcion = _escenario(db, minimo=50)
    emitir_certificado(inscripcion.id_inscripcion, db, None)

    respuesta = descargar_mi_certificado(inscripcion.id_inscripcion, db, _cuenta(db, "ana@example.com"))

    assert respuesta.media_type == "application/pdf"
    assert respuesta.body.startswith(b"%PDF")


def test_no_puede_descargar_el_certificado_de_otra_persona(db):
    evento, inscripcion = _escenario(db, minimo=50)
    ajena = _otra_inscripcion(db, evento, inscripcion, "beto@example.com")
    from app.models import Asistencia, Actividad

    for actividad in db.query(Actividad).all():
        db.add(Asistencia(id_inscripcion=ajena.id_inscripcion, id_actividad=actividad.id_actividad, estado="presente"))
    db.commit()
    emitir_certificado(ajena.id_inscripcion, db, None)

    with pytest.raises(HTTPException) as error:
        descargar_mi_certificado(ajena.id_inscripcion, db, _cuenta(db, "ana@example.com"))

    assert error.value.status_code == 404


def test_descarga_sin_certificado_emitido_devuelve_404(db):
    _, inscripcion = _escenario(db, minimo=50)

    with pytest.raises(HTTPException) as error:
        descargar_mi_certificado(inscripcion.id_inscripcion, db, _cuenta(db, "ana@example.com"))

    assert error.value.status_code == 404


def test_endpoints_exigen_rol_participante():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        organizador = _cuenta(session, "org@example.com", rol="organizador")
        participante = _cuenta(session, "ana@example.com")
        token_org, _ = create_access_token(organizador.id_usuario, ["organizador"])
        token_part, _ = create_access_token(participante.id_usuario, ["participante"])

    def override_db():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        assert client.get("/api/v1/certificados/mios").status_code in (401, 403)
        assert client.get("/api/v1/certificados/mios", headers={"Authorization": f"Bearer {token_org}"}).status_code == 403
        ok = client.get("/api/v1/certificados/mios", headers={"Authorization": f"Bearer {token_part}"})
        assert ok.status_code == 200
        assert ok.json() == []
    finally:
        app.dependency_overrides.clear()
