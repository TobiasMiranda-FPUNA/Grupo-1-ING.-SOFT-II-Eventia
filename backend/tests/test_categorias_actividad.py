import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.categorias_actividad import get_categoria_actividad, list_categorias_actividad
from app.db import Base
from app.models import CategoriaActividad


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def categorias(db):
    db.add_all(
        [
            CategoriaActividad(nombre="Taller"),
            CategoriaActividad(nombre="Conferencia", descripcion="Exposición magistral"),
            CategoriaActividad(nombre="Panel", activo=False),
        ]
    )
    db.commit()


def test_list_categorias_ordena_por_nombre(db, categorias):
    result = list_categorias_actividad(db)

    assert [c.nombre for c in result] == ["Conferencia", "Panel", "Taller"]


def test_list_categorias_filtra_por_activo(db, categorias):
    activas = list_categorias_actividad(db, activo=True)
    inactivas = list_categorias_actividad(db, activo=False)

    assert [c.nombre for c in activas] == ["Conferencia", "Taller"]
    assert [c.nombre for c in inactivas] == ["Panel"]


def test_get_categoria_devuelve_categoria(db, categorias):
    conferencia = next(c for c in list_categorias_actividad(db) if c.nombre == "Conferencia")

    result = get_categoria_actividad(conferencia.id_categoria, db)

    assert result.descripcion == "Exposición magistral"
    assert result.activo is True


def test_get_categoria_inexistente_devuelve_404(db):
    with pytest.raises(HTTPException) as exc:
        get_categoria_actividad(999, db)

    assert exc.value.status_code == 404
