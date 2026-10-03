# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, status

# func: funciones SQL usadas en la búsqueda de duplicados.
# select: construcción declarativa de consultas SQL.
from sqlalchemy import func, select
from sqlalchemy.orm import Session

# Dependencia que exige que el usuario autenticado tenga un rol específico.
from app.api.users import require_system_role
from app.db import get_db
from app.models import Conferencista, Usuario
from app.schemas import (
    ConferencistaCreate,
    ConferencistaResponse,
    ConferencistaUpdate,
)

# Router con el prefijo "/api/v1/conferencistas".
router = APIRouter(
    prefix="/api/v1/conferencistas",
    tags=["Conferencistas"],
)

# Exige el rol de sistema "organizador" para las operaciones de escritura.
organizer_required = Depends(require_system_role("organizador"))


# Construye el error 409 Conflict cuando ya existe un conferencista
# con el mismo email.
def duplicate_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Ya existe un conferencista con ese email",
    )


# Busca un conferencista por ID y lanza 404 si no existe.
def _get_conferencista_or_404(
    db: Session,
    conferencista_id: int,
) -> Conferencista:

    conferencista = db.get(Conferencista, conferencista_id)

    if conferencista is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conferencista no encontrado",
        )

    return conferencista


# ============================================================
# CREAR CONFERENCISTA
# ============================================================

@router.post(
    "",
    response_model=ConferencistaResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conferencista(
    data: ConferencistaCreate,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> ConferencistaResponse:

    # Verifica que no exista otro conferencista con el mismo email.
    if db.scalar(
        select(Conferencista).where(
            func.lower(Conferencista.email) == data.email.lower()
        )
    ):
        raise duplicate_error()

    # Crea el conferencista incluyendo su especialidad.
    conferencista = Conferencista(
        nombres=data.nombres.strip(),
        apellidos=data.apellidos.strip(),
        email=data.email,
        institucion=data.institucion,
        especialidad=data.especialidad,
        biografia=data.biografia,
    )

    db.add(conferencista)
    db.commit()
    db.refresh(conferencista)

    return ConferencistaResponse.model_validate(conferencista)


# ============================================================
# LISTAR CONFERENCISTAS
# ============================================================

# Endpoint público, sin autenticación.
@router.get(
    "",
    response_model=list[ConferencistaResponse],
)
def list_conferencistas(
    db: Session = Depends(get_db),
    q: str | None = None,
    activo: bool | None = None,
) -> list[ConferencistaResponse]:

    query = select(Conferencista)

    # Filtro opcional por nombre o apellido.
    if q:
        like = f"%{q}%"

        query = query.where(
            Conferencista.nombres.ilike(like)
            | Conferencista.apellidos.ilike(like)
        )

    # Filtro opcional por estado activo/inactivo.
    if activo is not None:
        query = query.where(
            Conferencista.activo == activo
        )

    conferencistas = db.scalars(
        query.order_by(
            Conferencista.apellidos,
            Conferencista.nombres,
        )
    ).all()

    return [
        ConferencistaResponse.model_validate(conferencista)
        for conferencista in conferencistas
    ]


# ============================================================
# OBTENER CONFERENCISTA POR ID
# ============================================================

# Endpoint público.
@router.get(
    "/{conferencista_id}",
    response_model=ConferencistaResponse,
)
def get_conferencista(
    conferencista_id: int,
    db: Session = Depends(get_db),
) -> ConferencistaResponse:

    conferencista = _get_conferencista_or_404(
        db,
        conferencista_id,
    )

    return ConferencistaResponse.model_validate(conferencista)


# ============================================================
# ACTUALIZAR CONFERENCISTA
# ============================================================

@router.put(
    "/{conferencista_id}",
    response_model=ConferencistaResponse,
)
@router.patch(
    "/{conferencista_id}",
    response_model=ConferencistaResponse,
)
def update_conferencista(
    conferencista_id: int,
    data: ConferencistaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> ConferencistaResponse:

    conferencista = _get_conferencista_or_404(
        db,
        conferencista_id,
    )

    # Si se modifica el email, verifica que no esté utilizado
    # por otro conferencista.
    if data.email is not None:

        duplicate = db.scalar(
            select(Conferencista).where(
                func.lower(Conferencista.email) == data.email.lower(),
                Conferencista.id_conferencista != conferencista_id,
            )
        )

        if duplicate:
            raise duplicate_error()

        conferencista.email = data.email

    # Actualización de los campos enviados.
    if data.nombres is not None:
        conferencista.nombres = data.nombres.strip()

    if data.apellidos is not None:
        conferencista.apellidos = data.apellidos.strip()

    if data.institucion is not None:
        conferencista.institucion = data.institucion

    # NUEVO: permite actualizar la especialidad.
    if data.especialidad is not None:
        conferencista.especialidad = data.especialidad

    if data.biografia is not None:
        conferencista.biografia = data.biografia

    if data.activo is not None:
        conferencista.activo = data.activo

    db.commit()
    db.refresh(conferencista)

    return ConferencistaResponse.model_validate(conferencista)


# ============================================================
# ELIMINAR CONFERENCISTA
# ============================================================

@router.delete(
    "/{conferencista_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conferencista(
    conferencista_id: int,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> None:

    conferencista = _get_conferencista_or_404(
        db,
        conferencista_id,
    )

    db.delete(conferencista)
    db.commit()