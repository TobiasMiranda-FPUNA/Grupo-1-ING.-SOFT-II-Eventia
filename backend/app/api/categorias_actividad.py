# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, status
# select: construcción declarativa de consultas SQL.
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CategoriaActividad
from app.schemas import CategoriaActividadResponse

# Router con el prefijo "/api/v1/categorias-actividad", agrupado bajo el tag
# "Categorías de actividad". Expone el catálogo cargado en
# sql/cargar_catalogos_iniciales.sql para que el frontend pueda elegir la
# categoría (id_categoria) al crear una actividad de la agenda (HU06). El
# catálogo se administra por SQL, por lo que acá solo hay lectura.
router = APIRouter(prefix="/api/v1/categorias-actividad", tags=["Categorías de actividad"])


# Lista las categorías de actividad ordenadas por nombre, con filtro
# opcional por estado activo/inactivo. Público, igual que el listado de
# conferencistas y de eventos.
@router.get("", response_model=list[CategoriaActividadResponse])
def list_categorias_actividad(
    db: Session = Depends(get_db),
    activo: bool | None = None,
) -> list[CategoriaActividadResponse]:
    query = select(CategoriaActividad)
    if activo is not None:
        query = query.where(CategoriaActividad.activo == activo)

    categorias = db.scalars(query.order_by(CategoriaActividad.nombre)).all()
    return [CategoriaActividadResponse.model_validate(categoria) for categoria in categorias]


# Obtiene una categoría de actividad puntual por id y lanza 404 si no existe.
@router.get("/{categoria_id}", response_model=CategoriaActividadResponse)
def get_categoria_actividad(categoria_id: int, db: Session = Depends(get_db)) -> CategoriaActividadResponse:
    categoria = db.get(CategoriaActividad, categoria_id)
    if categoria is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría de actividad no encontrada")
    return CategoriaActividadResponse.model_validate(categoria)
