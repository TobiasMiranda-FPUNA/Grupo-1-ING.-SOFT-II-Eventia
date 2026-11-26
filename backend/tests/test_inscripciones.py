from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.eventos import create_evento
from app.api.inscripciones import create_inscripcion
from app.db import Base
from app.models import Evento, RolParticipante, TipoEvento
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
            estado="publicado",
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


def test_create_inscripcion_rechaza_evento_no_publicado(db, rol_asistente):
    evento = _crear_evento(db, cupo_maximo=5)
    evento_db = db.get(Evento, evento.id_evento)
    evento_db.estado = "borrador"
    db.commit()

    with pytest.raises(HTTPException) as error:
        create_inscripcion(
            _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "ana.gomez@example.com"),
            db,
        )

    assert error.value.status_code == 409


def test_create_inscripcion_rechaza_fuera_de_fecha_limite(db, rol_asistente):
    evento = _crear_evento(db, cupo_maximo=5)
    evento_db = db.get(Evento, evento.id_evento)
    evento_db.politica.fecha_limite = date.today() - timedelta(days=1)
    db.commit()

    with pytest.raises(HTTPException) as error:
        create_inscripcion(
            _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "ana.gomez@example.com"),
            db,
        )

    assert error.value.status_code == 409
    assert "plazo" in error.value.detail


# ------------------------------------------------------------
# Inscripción con sesión iniciada: los datos personales del
# participante salen de su cuenta, no del cuerpo del pedido.
# ------------------------------------------------------------
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.db import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Inscripcion, Participante, RolSistema, Usuario  # noqa: E402


def _usuario(db, rol_nombre, email="hugo@fpuna.edu.py", documento=None):
    rol = db.query(RolSistema).filter_by(nombre=rol_nombre).first() or RolSistema(nombre=rol_nombre, activo=True)
    usuario = Usuario(
        nombres="Hugo", apellidos="Villagra", email=email, documento=documento,
        password_hash=hash_password("Clave1234"), roles=[rol],
    )
    db.add(usuario)
    db.commit()
    return usuario


def _participante_de(db, id_inscripcion):
    inscripcion = db.get(Inscripcion, id_inscripcion)
    return db.get(Participante, inscripcion.id_participante)


def test_participante_con_sesion_se_inscribe_con_datos_de_su_cuenta(db, rol_asistente):
    evento = _crear_evento(db, cupo_maximo=5)
    usuario = _usuario(db, "participante")
    manipulado = _inscripcion(
        evento.id_evento, rol_asistente.id_rol_participante,
        "otra.persona@example.com", nombres="Nombre", apellidos="Falso",
    )

    response = create_inscripcion(manipulado, db, usuario)

    participante = _participante_de(db, response.id_inscripcion)
    assert participante.email == "hugo@fpuna.edu.py"
    assert (participante.nombres, participante.apellidos) == ("Hugo", "Villagra")
    assert db.query(Participante).filter_by(email="otra.persona@example.com").first() is None


@pytest.mark.parametrize("rol_staff", ["organizador", "administrador", "Personal de acreditación"])
def test_personal_del_evento_puede_inscribir_a_otra_persona(db, rol_asistente, rol_staff):
    evento = _crear_evento(db, cupo_maximo=5)
    usuario = _usuario(db, rol_staff)

    response = create_inscripcion(
        _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "invitada@example.com", nombres="Laura"),
        db,
        usuario,
    )

    participante = _participante_de(db, response.id_inscripcion)
    assert (participante.email, participante.nombres) == ("invitada@example.com", "Laura")


def test_endpoint_http_ignora_correo_manipulado_y_rechaza_token_invalido():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        rol = RolParticipante(nombre="Asistente", activo=True)
        session.add(rol)
        session.commit()
        evento = _crear_evento(session, cupo_maximo=5)
        usuario = _usuario(session, "participante")
        token, _ = create_access_token(usuario.id_usuario, ["participante"])
        cuerpo = {
            "id_evento": evento.id_evento, "id_rol_participante": rol.id_rol_participante,
            "nombres": "Nombre", "apellidos": "Falso", "email": "victima@example.com",
        }

    def override_db():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        ok = client.post("/api/v1/inscripciones", json=cuerpo, headers={"Authorization": f"Bearer {token}"})
        assert ok.status_code == 201
        with Session(engine) as s:
            assert _participante_de(s, ok.json()["id_inscripcion"]).email == "hugo@fpuna.edu.py"
            assert s.query(Participante).filter_by(email="victima@example.com").first() is None

        invalido = client.post("/api/v1/inscripciones", json=cuerpo, headers={"Authorization": "Bearer basura"})
        assert invalido.status_code == 401

        # Sin sesión, la inscripción pública sigue funcionando con los datos enviados.
        anonimo = client.post("/api/v1/inscripciones", json=cuerpo)
        assert anonimo.status_code == 201
    finally:
        app.dependency_overrides.clear()


def test_participante_con_sesion_usa_la_cedula_de_su_cuenta(db, rol_asistente):
    evento = _crear_evento(db, cupo_maximo=5)
    usuario = _usuario(db, "participante", documento="1000006")
    manipulado = _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "hugo@fpuna.edu.py")
    manipulado = manipulado.model_copy(update={"documento": "9999999"})

    response = create_inscripcion(manipulado, db, usuario)

    assert _participante_de(db, response.id_inscripcion).documento == "1000006"


def test_cedula_de_la_cuenta_corrige_la_del_participante_existente(db, rol_asistente):
    db.add(Participante(nombres="Hugo", apellidos="Villagra", email="hugo@fpuna.edu.py", documento="viejo"))
    db.commit()
    evento = _crear_evento(db, cupo_maximo=5)
    usuario = _usuario(db, "participante", documento="1000006")

    response = create_inscripcion(
        _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "hugo@fpuna.edu.py"), db, usuario
    )

    assert _participante_de(db, response.id_inscripcion).documento == "1000006"


def test_cuenta_sin_cedula_conserva_el_documento_del_formulario(db, rol_asistente):
    evento = _crear_evento(db, cupo_maximo=5)
    usuario = _usuario(db, "participante")  # cuenta anterior al campo cédula
    datos = _inscripcion(evento.id_evento, rol_asistente.id_rol_participante, "hugo@fpuna.edu.py")
    datos = datos.model_copy(update={"documento": "4123456"})

    response = create_inscripcion(datos, db, usuario)

    assert _participante_de(db, response.id_inscripcion).documento == "4123456"
