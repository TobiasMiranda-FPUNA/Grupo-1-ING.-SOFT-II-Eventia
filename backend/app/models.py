# Tipos de columna de SQLAlchemy (Boolean, Integer, String), ForeignKey para
# definir claves foráneas, Table/Column para crear tablas "a mano" (como la
# tabla intermedia de la relación muchos-a-muchos usuario-rol).
from sqlalchemy import Boolean, ForeignKey, Integer, String, Table, Column

# Mapped/mapped_column: sintaxis moderna de SQLAlchemy ORM para tipar los
# atributos de los modelos. relationship: define relaciones entre tablas
# (por ejemplo, un usuario que tiene varios roles).
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Base: clase base declarativa de SQLAlchemy de la que heredan todos los
# modelos, y que SQLAlchemy usa para saber qué tablas debe crear/mapear.
from app.db import Base


# Tabla intermedia (muchos a muchos) que vincula usuarios con roles del
# sistema. No es una clase de modelo, sino una tabla "cruda" porque no
# necesita atributos propios más allá de las dos claves foráneas.
usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("id_usuario", ForeignKey("usuario.id_usuario"), primary_key=True),
    Column("id_rol", ForeignKey("rol_sistema.id_rol"), primary_key=True),
)


# Roles a nivel de sistema/aplicación (ej: administrador, organizador),
# usados para controlar permisos y accesos dentro de la plataforma.
class RolSistema(Base):
    __tablename__ = "rol_sistema"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# Roles que puede tomar un participante dentro de un evento (ej: asistente,
# expositor, staff). Es independiente de RolSistema: uno regula permisos en
# la app, el otro el rol dentro de un evento puntual.
class RolParticipante(Base):
    __tablename__ = "rol_participante"

    id_rol_participante: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# Representa la inscripción de un participante a un evento, con el rol que
# ocupará (id_rol_participante) y el estado de esa inscripción (ej:
# pendiente, confirmada, cancelada).
class Inscripcion(Base):
    __tablename__ = "inscripcion"

    id_inscripcion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_rol_participante: Mapped[int] = mapped_column(
        ForeignKey("rol_participante.id_rol_participante", ondelete="RESTRICT"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False)


# Representa a un usuario registrado en el sistema (credenciales y datos
# personales básicos). Se relaciona con RolSistema mediante la tabla
# intermedia usuario_rol para saber qué roles/permisos tiene.
class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    roles: Mapped[list[RolSistema]] = relationship(secondary=usuario_rol, lazy="selectin")
