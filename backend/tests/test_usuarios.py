import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import login
from app.api.users import create_user, delete_user, list_users
from app.core.security import create_access_token, hash_password
from app.db import Base, get_db
from app.main import app
from app.models import RolSistema, Usuario, usuario_rol
from app.schemas import LoginRequest, UsuarioCreate


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def roles(db):
    admin = RolSistema(codigo="ADMINISTRADOR", nombre="administrador", activo=True)
    participante = RolSistema(codigo="PARTICIPANTE", nombre="participante", activo=True)
    inactivo = RolSistema(codigo="VIEJO", nombre="viejo", activo=False)
    db.add_all([admin, participante, inactivo])
    db.commit()
    return {"admin": admin, "participante": participante, "inactivo": inactivo}


@pytest.fixture
def admin_user(db, roles):
    user = Usuario(
        nombres="Ana",
        apellidos="Duarte",
        email="admin@eventia.test",
        password_hash=hash_password("Admin123!"),
        roles=[roles["admin"]],
    )
    db.add(user)
    db.commit()
    return user


def _payload(rol: RolSistema, **cambios) -> UsuarioCreate:
    datos = {
        "nombres": "María",
        "apellidos": "López",
        "email": "maria@eventia.test",
        "password": "Clave1234",
        "id_rol_sistema": rol.id_rol,
    }
    datos.update(cambios)
    return UsuarioCreate(**datos)


def test_crear_usuario_participante_puede_iniciar_sesion(db, roles, admin_user):
    creado = create_user(_payload(roles["participante"]), db, admin_user)

    assert creado.email == "maria@eventia.test"
    assert creado.roles == ["participante"]
    assert creado.activo is True
    guardado = db.get(Usuario, creado.id_usuario)
    assert guardado.password_hash != "Clave1234"

    sesion = login(LoginRequest(email="maria@eventia.test", password="Clave1234"), db)
    assert sesion.user.roles == ["participante"]


def test_crear_usuario_rechaza_correo_duplicado_sin_importar_mayusculas(db, roles, admin_user):
    with pytest.raises(HTTPException) as error:
        create_user(_payload(roles["participante"], email="ADMIN@eventia.test"), db, admin_user)

    assert error.value.status_code == 409


@pytest.mark.parametrize("rol_key", ["inactivo", None])
def test_crear_usuario_rechaza_rol_inexistente_o_inactivo(db, roles, admin_user, rol_key):
    payload = _payload(roles["participante"], id_rol_sistema=roles[rol_key].id_rol if rol_key else 999)

    with pytest.raises(HTTPException) as error:
        create_user(payload, db, admin_user)

    assert error.value.status_code == 400


@pytest.mark.parametrize(
    "cambios",
    [{"password": "corta"}, {"email": "no-es-un-correo"}, {"nombres": "   "}, {"id_rol_sistema": 0}],
)
def test_esquema_valida_datos_obligatorios(roles, cambios):
    with pytest.raises(ValidationError):
        _payload(roles["participante"], **cambios)


def test_listar_usuarios_ordenados_por_apellido(db, roles, admin_user):
    create_user(_payload(roles["participante"], apellidos="Acosta", email="b@eventia.test"), db, admin_user)

    listado = list_users(db, admin_user)

    assert [u.apellidos for u in listado] == ["Acosta", "Duarte"]
    assert listado[1].roles == ["administrador"]


def test_eliminar_usuario_borra_cuenta_y_roles(db, roles, admin_user):
    creado = create_user(_payload(roles["participante"]), db, admin_user)

    delete_user(creado.id_usuario, db, admin_user)

    assert db.get(Usuario, creado.id_usuario) is None
    filas = db.execute(select(usuario_rol).where(usuario_rol.c.id_usuario == creado.id_usuario)).all()
    assert filas == []


def test_eliminar_usuario_inexistente_devuelve_404(db, admin_user):
    with pytest.raises(HTTPException) as error:
        delete_user(999, db, admin_user)

    assert error.value.status_code == 404


def test_administrador_no_puede_eliminarse_a_si_mismo(db, admin_user):
    with pytest.raises(HTTPException) as error:
        delete_user(admin_user.id_usuario, db, admin_user)

    assert error.value.status_code == 409
    assert db.get(Usuario, admin_user.id_usuario) is not None


def test_endpoints_exigen_rol_administrador():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        rol = RolSistema(codigo="PARTICIPANTE", nombre="participante", activo=True)
        user = Usuario(nombres="Lu", apellidos="Gi", email="lu@eventia.test", password_hash=hash_password("x" * 8), roles=[rol])
        session.add(user)
        session.commit()
        token, _ = create_access_token(user.id_usuario, ["participante"])

    def override_db():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/v1/users", headers=headers).status_code == 403
        assert client.delete("/api/v1/users/1", headers=headers).status_code == 403
        assert client.get("/api/v1/users").status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()
