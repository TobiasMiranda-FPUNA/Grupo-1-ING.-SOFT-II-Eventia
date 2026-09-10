# date/datetime: tipos usados para las columnas de fechas de eventos y para
# marcar el momento en que se registra una inscripción.
from datetime import date, datetime, UTC

# Tipos de columna de SQLAlchemy (Boolean, Integer, String), ForeignKey para
# definir claves foráneas, Table/Column para crear tablas "a mano" (como la
# tabla intermedia de la relación muchos-a-muchos usuario-rol). Date/DateTime
# para columnas de fecha/fecha-hora, y UniqueConstraint para restricciones de
# unicidad que involucran más de una columna.
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
)

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


# Catálogo parametrizable de tipos de evento (ej: congreso, seminario,
# taller, jornada), usado para clasificar cada Evento.
class TipoEvento(Base):
    __tablename__ = "tipo_evento"

    id_tipo_evento: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# Representa un evento concreto (congreso, seminario, etc.) con su rango de
# fechas, lugar y cupo máximo de inscripciones. El estado controla su
# visibilidad ("borrador" o "publicado").
class Evento(Base):
    __tablename__ = "evento"

    id_evento: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_tipo_evento: Mapped[int] = mapped_column(
        ForeignKey("tipo_evento.id_tipo_evento", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    lugar: Mapped[str | None] = mapped_column(String(200))
    cupo_maximo: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="borrador")

    # Política de inscripción asociada 1 a 1 al evento (lista de espera,
    # aprobación manual, mínimo de asistencia para certificado, etc.).
    # lazy="joined" trae la política en la misma consulta que el evento.
    politica: Mapped["PoliticaInscripcion | None"] = relationship(
        back_populates="evento",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
    )


# Reglas de inscripción parametrizables de un evento: si permite lista de
# espera cuando se agota el cupo, si requiere aprobación manual, la fecha
# límite de inscripción y el mínimo de asistencia para emitir certificado.
class PoliticaInscripcion(Base):
    __tablename__ = "politica_inscripcion"

    id_politica: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_evento: Mapped[int] = mapped_column(
        ForeignKey("evento.id_evento", ondelete="CASCADE"), unique=True, nullable=False
    )
    fecha_limite: Mapped[date | None] = mapped_column(Date)
    requiere_aprobacion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permite_lista_espera: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_asistencia_certificado: Mapped[int] = mapped_column(Integer, default=75, nullable=False)

    evento: Mapped[Evento] = relationship(back_populates="politica")


# Persona inscripta a uno o más eventos. Es independiente de Usuario: un
# participante no necesariamente tiene una cuenta de acceso al sistema (por
# eso no lleva id_usuario en esta primera versión, solo sus datos de
# contacto usados para la inscripción pública).
class Participante(Base):
    __tablename__ = "participante"

    id_participante: Mapped[int] = mapped_column(Integer, primary_key=True)
    documento: Mapped[str | None] = mapped_column(String(50))
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    institucion: Mapped[str | None] = mapped_column(String(150))


# Representa la inscripción de un participante a un evento, con el rol que
# ocupará (id_rol_participante) y el estado de esa inscripción (ej:
# confirmada, lista_de_espera, cancelada). La restricción de unicidad evita
# que un mismo participante quede inscripto dos veces al mismo evento.
class Inscripcion(Base):
    __tablename__ = "inscripcion"
    __table_args__ = (
        UniqueConstraint("id_evento", "id_participante", name="uq_inscripcion_evento_participante"),
    )

    id_inscripcion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_evento: Mapped[int] = mapped_column(
        ForeignKey("evento.id_evento", ondelete="RESTRICT"), nullable=False
    )
    id_participante: Mapped[int] = mapped_column(
        ForeignKey("participante.id_participante", ondelete="RESTRICT"), nullable=False
    )
    id_rol_participante: Mapped[int] = mapped_column(
        ForeignKey("rol_participante.id_rol_participante", ondelete="RESTRICT"), nullable=False
    )
    fecha_inscripcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
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
