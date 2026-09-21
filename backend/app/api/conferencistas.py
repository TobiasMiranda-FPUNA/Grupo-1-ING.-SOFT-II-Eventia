# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, status
# func: funciones SQL (ej: lower()) usadas en la búsqueda de duplicados.
# select: construcción declarativa de consultas SQL.
from sqlalchemy import func, select
from sqlalchemy.orm import Session

# Dependencia que exige que el usuario autenticado tenga un rol específico.
from app.api.users import require_system_role
from app.db import get_db
from app.models import Conferencista, Usuario
from app.schemas import ConferencistaCreate, ConferencistaResponse, ConferencistaUpdate

# Router con el prefijo "/api/v1/conferencistas", agrupado bajo el tag
# "Conferencistas" (expositores invitados a exponer en actividades del
# evento).
router = APIRouter(prefix="/api/v1/conferencistas", tags=["Conferencistas"])
# Dependencia reutilizada en los endpoints de escritura: exige que el
# usuario autenticado tenga el rol de sistema "organizador" (listar/obtener
# conferencistas queda público, igual que en app/api/eventos.py).
organizer_required = Depends(require_system_role("organizador"))


# Construye el error 409 Conflict que se devuelve cuando ya existe un
# conferencista con el mismo email (evita duplicados).
def duplicate_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Ya existe un conferencista con ese email",
    )


# Busca un conferencista por id y lanza 404 si no existe.
def _get_conferencista_or_404(db: Session, conferencista_id: int) -> Conferencista:
    conferencista = db.get(Conferencista, conferencista_id)
    if conferencista is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conferencista no encontrado")
    return conferencista


# Crea un nuevo conferencista, validando que no exista ya otro con el mismo
# email (comparación insensible a mayúsculas).
@router.post("", response_model=ConferencistaResponse, status_code=status.HTTP_201_CREATED)
def create_conferencista(
    data: ConferencistaCreate,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> ConferencistaResponse:
    if db.scalar(select(Conferencista).where(func.lower(Conferencista.email) == data.email.lower())):
        raise duplicate_error()

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


# Lista conferencistas, con filtros opcionales por texto (nombre o apellido)
# y por estado activo/inactivo. Es un endpoint público (sin autenticación),
# igual que el listado de eventos.
@router.get("", response_model=list[ConferencistaResponse])
def list_conferencistas(
    db: Session = Depends(get_db),
    q: str | None = None,
    activo: bool | None = None,
) -> list[ConferencistaResponse]:
    query = select(Conferencista)
    if q:
        like = f"%{q}%"
        query = query.where(
            Conferencista.nombres.ilike(like) | Conferencista.apellidos.ilike(like)
        )
    if activo is not None:
        query = query.where(Conferencista.activo == activo)

    conferencistas = db.scalars(query.order_by(Conferencista.apellidos, Conferencista.nombres)).all()
    return [ConferencistaResponse.model_validate(conferencista) for conferencista in conferencistas]


# Obtiene un conferencista puntual por id. Público, igual que el listado.
@router.get("/{conferencista_id}", response_model=ConferencistaResponse)
def get_conferencista(conferencista_id: int, db: Session = Depends(get_db)) -> ConferencistaResponse:
    conferencista = _get_conferencista_or_404(db, conferencista_id)
    return ConferencistaResponse.model_validate(conferencista)


# Actualiza un conferencista existente de forma parcial: solo se modifican
# los campos presentes en la petición. Si se cambia el email, se revalida
# que no choque con el de otro conferencista.
@router.put("/{conferencista_id}", response_model=ConferencistaResponse)
@router.patch("/{conferencista_id}", response_model=ConferencistaResponse)
def update_conferencista(
    conferencista_id: int,
    data: ConferencistaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> ConferencistaResponse:
    conferencista = _get_conferencista_or_404(db, conferencista_id)

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
    if data.nombres is not None:
        conferencista.nombres = data.nombres.strip()
    if data.apellidos is not None:
        conferencista.apellidos = data.apellidos.strip()
    if data.institucion is not None:
        conferencista.institucion = data.institucion
    if data.especialidad is not None:
        conferencista.especialidad = data.especialidad
    if data.biografia is not None:
        conferencista.biografia = data.biografia
    if data.activo is not None:
        conferencista.activo = data.activo

    db.commit()
    db.refresh(conferencista)
    return ConferencistaResponse.model_validate(conferencista)


# Elimina un conferencista. No hay todavía ninguna tabla que lo referencie
# (la agenda/actividades es HU06, aún no implementada), por lo que no se
# necesita ninguna validación de integridad adicional antes del borrado.
@router.delete("/{conferencista_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conferencista(
    conferencista_id: int,
    db: Session = Depends(get_db),
    _: Usuario = organizer_required,
) -> None:
    conferencista = _get_conferencista_or_404(db, conferencista_id)
    db.delete(conferencista)
    db.commit()
