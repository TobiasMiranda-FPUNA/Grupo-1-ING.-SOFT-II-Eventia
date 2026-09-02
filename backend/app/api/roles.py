# APIRouter/Depends/HTTPException/status: ver detalle en app/api/auth.py.
from fastapi import APIRouter, Depends, HTTPException, status
# func: funciones SQL (ej: lower(), trim()) usadas en las consultas.
# select: construcción declarativa de consultas SQL.
from sqlalchemy import func, select
# IntegrityError: excepción que lanza SQLAlchemy cuando una operación viola
# una restricción de la base de datos (ej: una clave foránea en uso).
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# Dependencia que exige que el usuario autenticado tenga un rol específico.
from app.api.users import require_system_role
from app.db import get_db
# Modelos ORM involucrados: inscripciones, roles de participante/sistema,
# usuarios y la tabla intermedia usuario-rol.
from app.models import Inscripcion, RolParticipante, RolSistema, Usuario, usuario_rol
from app.schemas import RoleCreate, RoleResponse, RoleUpdate


# Router con el prefijo "/api/v1/roles", agrupado bajo el tag "Parametrización".
router = APIRouter(prefix="/api/v1/roles", tags=["Parametrización"])
# Dependencia reutilizada en todos los endpoints de este router: exige que
# el usuario autenticado tenga el rol de sistema "administrador".
admin_required = Depends(require_system_role("administrador"))
# Estados de una inscripción que se consideran "activos" (no cancelados),
# usados para impedir borrar un rol de participante que esté en uso.
ACTIVE_INSCRIPTION_STATES = {"pendiente", "confirmada", "inscripta", "inscrito", "activa"}


# Construye el error 409 Conflict que se devuelve cuando ya existe un rol
# con el mismo nombre (evita duplicados).
def duplicate_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Ya existe un rol con ese nombre",
    )


# Convierte un modelo de rol (de sistema o de participante) al schema de
# respuesta RoleResponse. Como ambos modelos usan una columna de id
# distinta (id_rol / id_rol_participante), se obtiene la que corresponda
# con getattr para reutilizar la misma función en ambos casos.
def role_response(role: RolSistema | RolParticipante) -> RoleResponse:
    role_id = getattr(role, "id_rol", getattr(role, "id_rol_participante", None))
    return RoleResponse(
        id=role_id,
        nombre=role.nombre,
        descripcion=role.descripcion,
        activo=role.activo,
    )


# Lista todos los roles de sistema, ordenados por nombre. Solo accesible
# para administradores.
@router.get("/sistema", response_model=list[RoleResponse])
def list_system_roles(db: Session = Depends(get_db), _: Usuario = admin_required):
    roles = db.scalars(select(RolSistema).order_by(RolSistema.nombre)).all()
    return [role_response(role) for role in roles]


# Crea un nuevo rol de sistema, validando que no exista ya otro con el
# mismo nombre (comparación insensible a mayúsculas).
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
    db.commit()
    db.refresh(role)
    return role_response(role)


# Actualiza un rol de sistema existente (nombre, descripción y/o estado
# activo). Registrado tanto para PUT como PATCH, ya que todos los campos
# del schema RoleUpdate son opcionales y se actualizan solo si vienen
# presentes en la petición.
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
    db.commit()
    db.refresh(role)
    return role_response(role)


# Elimina un rol de sistema, siempre que no esté asignado a ningún usuario
# (se verifica contra la tabla intermedia usuario_rol) para no dejar
# referencias rotas.
@router.delete("/sistema/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_system_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: Usuario = admin_required,
):
    role = db.get(RolSistema, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    in_use = db.scalar(select(usuario_rol.c.id_usuario).where(usuario_rol.c.id_rol == role_id).limit(1))
    if in_use is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El rol está asignado a usuarios")
    db.delete(role)
    db.commit()


# Lista todos los roles de participante, ordenados por nombre.
@router.get("/participantes", response_model=list[RoleResponse])
def list_participant_roles(db: Session = Depends(get_db), _: Usuario = admin_required):
    roles = db.scalars(select(RolParticipante).order_by(RolParticipante.nombre)).all()
    return [role_response(role) for role in roles]


# Crea un nuevo rol de participante, validando que no exista ya otro con
# el mismo nombre.
@router.post("/participantes", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_participant_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    _: Usuario = admin_required,
):
    name = data.nombre.strip()
    if db.scalar(select(RolParticipante).where(func.lower(RolParticipante.nombre) == name.lower())):
        raise duplicate_error()
    role = RolParticipante(nombre=name, descripcion=data.descripcion)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role_response(role)


# Actualiza un rol de participante existente (nombre, descripción y/o
# estado activo), igual que update_system_role pero sobre RolParticipante.
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
    db.commit()
    db.refresh(role)
    return role_response(role)


# Elimina un rol de participante, siempre que no tenga inscripciones
# activas asociadas (ver ACTIVE_INSCRIPTION_STATES). Además captura
# IntegrityError como resguardo extra por si la base de datos rechaza el
# borrado por alguna otra restricción no contemplada en la validación previa.
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