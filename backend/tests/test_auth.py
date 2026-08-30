import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.auth import login
from app.core.security import decode_access_token, hash_password
from app.db import Base
from app.models import RolSistema, Usuario
from app.schemas import LoginRequest


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def registered_user(db):
    role = RolSistema(nombre="administrador", activo=True)
    user = Usuario(
        nombres="Ana",
        apellidos="Pérez",
        email="ana@example.com",
        password_hash=hash_password("secreto"),
        activo=True,
        roles=[role],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_login_with_valid_credentials_returns_session_token(db, registered_user):
    response = login(LoginRequest(email="ana@example.com", password="secreto"), db)
    payload = decode_access_token(response.access_token)

    assert response.token_type == "bearer"
    assert response.user.email == "ana@example.com"
    assert response.user.roles == ["administrador"]
    assert payload["sub"] == str(registered_user.id_usuario)


@pytest.mark.parametrize(
    "email,password",
    [("ana@example.com", "incorrecta"), ("desconocido@example.com", "secreto")],
)
def test_login_with_invalid_credentials_returns_generic_error(db, registered_user, email, password):
    with pytest.raises(HTTPException) as error:
        login(LoginRequest(email=email, password=password), db)

    assert error.value.status_code == 401
    assert error.value.detail == "Credenciales inválidas"
