from sqlalchemy import Boolean, ForeignKey, Integer, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("id_usuario", ForeignKey("usuario.id_usuario"), primary_key=True),
    Column("id_rol", ForeignKey("rol_sistema.id_rol"), primary_key=True),
)


class RolSistema(Base):
    __tablename__ = "rol_sistema"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RolParticipante(Base):
    __tablename__ = "rol_participante"

    id_rol_participante: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Inscripcion(Base):
    __tablename__ = "inscripcion"

    id_inscripcion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_rol_participante: Mapped[int] = mapped_column(
        ForeignKey("rol_participante.id_rol_participante", ondelete="RESTRICT"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False)


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    roles: Mapped[list[RolSistema]] = relationship(secondary=usuario_rol, lazy="selectin")
