# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, status
# func: funciones SQL (ej: lower(), trim()) usadas en las consultas.
# select: construcción declarativa de consultas SQL.
from sqlalchemy import func, select
# IntegrityError: excepción que lanza SQLAlchemy cuando una operación viola
# una restricción de la base de datos.
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import re
import unicodedata
from uuid import uuid4

# Dependencia que exige que el usuario autenticado tenga un rol específico.
from app.api.users import require_system_role
from app.db import get_db
# Modelos ORM involucrados.
from app.models import Inscripcion, RolParticipante, RolSistema, Usuario, usuario_rol
from app.schemas import RoleCreate, RoleResponse, RoleUpdate


router = APIRouter(prefix="/api/v1/roles", tags=["Parametrización"])
admin_required = Depends(require_system_role("administrador"))

ACTIVE_INSCRIPTION_STATES = {
    "pendiente",
    "confirmada",
    "inscripta",
    "inscrito",
    "activa",
    "lista_de_espera",
}


def duplicate_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Ya existe un rol con ese nombre",
    )


def role_response(role: RolSistema | RolParticipante) -> RoleResponse:
    role_id = getattr(role, "id_rol", getattr(role, "id_rol_participante", None))
    return RoleResponse(
        id=role_id,
        nombre=role.nombre,
        descripcion=role.descripcion,
        activo=role.activo,
    )


def participant_code_prefix(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_name).strip("-").upper()
    return slug or "ROL"


@router.get("/sistema", response_model=list[RoleResponse])
def list_system_roles(db: Session = Depends(get_db), _: Usuario = admin_required):
    roles = db.scalars(select(RolSistema).order_by(RolSistema.nombre)).all()
    return [role_response(role) for role in roles]


@router.post("/sistema", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_system_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    _: Usuario = admin_required,
):
    name = data.nombre.strip()
    if db.scalar(select(RolSistema).where(func.lower(RolSistema.nombre) == name.lower())):
        raise duplicate_error()
    role = RolSistema(nombre=name, descripcion=data.descripcion)
    db.add(role)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise duplicate_error() from None
    db.refresh(role)
    return role_response(role)


@router.put("/sistema/{role_id}", response_model=RoleResponse)
@router.patch("/sistema/{role_id}", response_model=RoleResponse)
def update_system_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    _: Usuario = admin_required,
):
    role = db.get(RolSistema, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    if data.nombre is not None:
        name = data.nombre.strip()
        duplicate = db.scalar(
            select(RolSistema).where(
                func.lower(RolSistema.nombre) == name.lower(),
                RolSistema.id_rol != role_id,
            )
        )
        if duplicate:
            raise duplicate_error()
        role.nombre = name
    if data.descripcion is not None:
        role.descripcion = data.descripcion
    if data.activo is not None:
        role.activo = data.activo
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise duplicate_error() from None
    db.refresh(role)
    return role_response(role)


@router.delete("/sistema/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_system_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: Usuario = admin_required,
):
    role = db.get(RolSistema, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    in_use = db.scalar(select(usuario_rol.c.id_usuario).where(usuario_rol.c.id_rol_sistema == role_id).limit(1))
    if in_use is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El rol está asignado a usuarios")
    db.delete(role)
    db.commit()


@router.get("/participantes", response_model=list[RoleResponse])
def list_participant_roles(db: Session = Depends(get_db), _: Usuario = admin_required):
    roles = db.scalars(select(RolParticipante).order_by(RolParticipante.nombre)).all()
    return [role_response(role) for role in roles]


@router.post("/participantes", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_participant_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    _: Usuario = admin_required,
):
    name = data.nombre.strip()
    if db.scalar(select(RolParticipante).where(func.lower(RolParticipante.nombre) == name.lower())):
        raise duplicate_error()

    # Se usa un código temporal para insertar y obtener el ID generado por la BD.
    # Luego se reemplaza por un código legible y único basado en nombre + ID.
    role = RolParticipante(
        codigo=f"TMP-{uuid4().hex.upper()}",
        nombre=name,
        descripcion=data.descripcion,
    )
    db.add(role)

    try:
        db.flush()
        prefix = participant_code_prefix(name)
        suffix = f"-{role.id_rol_participante}"
        role.codigo = f"{prefix[:50 - len(suffix)]}{suffix}"
        db.commit()
    except IntegrityError:
        db.rollback()
        raise duplicate_error() from None

    db.refresh(role)
    return role_response(role)


@router.put("/participantes/{role_id}", response_model=RoleResponse)
@router.patch("/participantes/{role_id}", response_model=RoleResponse)
def update_participant_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    _: Usuario = admin_required,
):
    role = db.get(RolParticipante, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol de participante no encontrado")
    if data.nombre is not None:
        name = data.nombre.strip()
        duplicate = db.scalar(
            select(RolParticipante).where(
                func.lower(RolParticipante.nombre) == name.lower(),
                RolParticipante.id_rol_participante != role_id,
            )
        )
        if duplicate:
            raise duplicate_error()
        role.nombre = name
    if data.descripcion is not None:
        role.descripcion = data.descripcion
    if data.activo is not None:
        role.activo = data.activo
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise duplicate_error() from None
    db.refresh(role)
    return role_response(role)


@router.delete("/participantes/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_participant_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: Usuario = admin_required,
):
    role = db.get(RolParticipante, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol de participante no encontrado")
    active_registration = db.scalar(
        select(Inscripcion.id_inscripcion)
        .where(
            Inscripcion.id_rol_participante == role_id,
            func.lower(func.trim(Inscripcion.estado)).in_(ACTIVE_INSCRIPTION_STATES),
        )
        .limit(1)
    )
    if active_registration is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el rol porque está asignado a inscripciones activas",
        )
    db.delete(role)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el rol porque está en uso",
        ) from None
