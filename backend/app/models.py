from datetime import date, datetime, time, UTC

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
    text,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ============================================================
# TABLAS INTERMEDIAS
# ============================================================

usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column(
        "id_usuario",
        ForeignKey("usuario.id_usuario"),
        primary_key=True
    ),
    Column(
        "id_rol_sistema",
        ForeignKey("rol_sistema.id_rol_sistema"),
        primary_key=True
    ),
)


# ============================================================
# ROLES DEL SISTEMA
# ============================================================

class RolSistema(Base):
    __tablename__ = "rol_sistema"

    id_rol: Mapped[int] = mapped_column(
        "id_rol_sistema",
        Integer,
        primary_key=True
    )

    nombre: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(String(255))

    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )


# ============================================================
# ROLES DE PARTICIPANTES
# ============================================================

class RolParticipante(Base):
    __tablename__ = "rol_participante"

    id_rol_participante: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    nombre: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(String(255))

    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )


# ============================================================
# TIPOS DE EVENTO
# ============================================================

class TipoEvento(Base):
    __tablename__ = "tipo_evento"

    id_tipo_evento: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    nombre: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(String(255))

    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )


# ============================================================
# EVENTOS
# ============================================================

class Evento(Base):
    __tablename__ = "evento"

    id_evento: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_tipo_evento: Mapped[int] = mapped_column(
        ForeignKey(
            "tipo_evento.id_tipo_evento",
            ondelete="RESTRICT"
        ),
        nullable=False
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(String(500))

    fecha_inicio: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    fecha_fin: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    lugar: Mapped[str | None] = mapped_column(String(200))

    cupo_maximo: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="borrador"
    )

    politica: Mapped["PoliticaInscripcion | None"] = relationship(
        back_populates="evento",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
    )


# ============================================================
# POLÍTICA DE INSCRIPCIÓN
# ============================================================

class PoliticaInscripcion(Base):
    __tablename__ = "politica_inscripcion"

    id_politica: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_evento: Mapped[int] = mapped_column(
        ForeignKey(
            "evento.id_evento",
            ondelete="CASCADE"
        ),
        unique=True,
        nullable=False
    )

    fecha_limite: Mapped[date | None] = mapped_column(Date)

    requiere_aprobacion: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    permite_lista_espera: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    min_asistencia_certificado: Mapped[int] = mapped_column(
        Integer,
        default=75,
        nullable=False
    )

    evento: Mapped[Evento] = relationship(
        back_populates="politica"
    )


# ============================================================
# PARTICIPANTES
# ============================================================

class Participante(Base):
    __tablename__ = "participante"

    id_participante: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    documento: Mapped[str | None] = mapped_column(String(50))

    nombres: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    apellidos: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    institucion: Mapped[str | None] = mapped_column(String(150))


# ============================================================
# INSCRIPCIONES
# ============================================================

class Inscripcion(Base):
    __tablename__ = "inscripcion"

    __table_args__ = (
        UniqueConstraint(
            "id_evento",
            "id_participante",
            name="uq_inscripcion_evento_participante"
        ),
    )

    id_inscripcion: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_evento: Mapped[int] = mapped_column(
        ForeignKey(
            "evento.id_evento",
            ondelete="RESTRICT"
        ),
        nullable=False
    )

    id_participante: Mapped[int] = mapped_column(
        ForeignKey(
            "participante.id_participante",
            ondelete="RESTRICT"
        ),
        nullable=False
    )

    id_rol_participante: Mapped[int] = mapped_column(
        ForeignKey(
            "rol_participante.id_rol_participante",
            ondelete="RESTRICT"
        ),
        nullable=False
    )

    fecha_inscripcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )


# ============================================================
# CONFERENCISTAS / EXPOSITORES
# ============================================================

class Conferencista(Base):
    __tablename__ = "conferencista"

    id_conferencista: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    nombres: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    apellidos: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False
    )

    institucion: Mapped[str | None] = mapped_column(
        String(150)
    )

    # Campo agregado para almacenar la especialidad profesional.
    # La columna ya existe en PostgreSQL.

    especialidad: Mapped[str | None] = mapped_column(
        String(150)
    )

    biografia: Mapped[str | None] = mapped_column(Text)

    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )


# ============================================================
# RELACIÓN ACTIVIDAD - CONFERENCISTA
# ============================================================

actividad_conferencista = Table(
    "actividad_conferencista",
    Base.metadata,

    Column(
        "id_actividad",
        ForeignKey(
            "actividad.id_actividad",
            ondelete="CASCADE"
        ),
        primary_key=True
    ),

    Column(
        "id_conferencista",
        ForeignKey(
            "conferencista.id_conferencista",
            ondelete="CASCADE"
        ),
        primary_key=True
    ),

    Column(
        "rol_en_actividad",
        String(100),
        nullable=False,
        server_default=text("'CONFERENCISTA'")
    ),
)


# ============================================================
# CATEGORÍAS DE ACTIVIDAD
# ============================================================

class CategoriaActividad(Base):
    __tablename__ = "categoria_actividad"

    id_categoria: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    nombre: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(String(255))

    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )


# ============================================================
# ACTIVIDADES
# ============================================================

class Actividad(Base):
    __tablename__ = "actividad"

    id_actividad: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_evento: Mapped[int] = mapped_column(
        ForeignKey("evento.id_evento"),
        nullable=False
    )

    id_categoria: Mapped[int] = mapped_column(
        ForeignKey("categoria_actividad.id_categoria"),
        nullable=False
    )

    titulo: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(Text)

    fecha: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    hora_inicio: Mapped[time] = mapped_column(
        Time,
        nullable=False
    )

    hora_fin: Mapped[time] = mapped_column(
        Time,
        nullable=False
    )

    lugar: Mapped[str | None] = mapped_column(String(200))

    modalidad: Mapped[str] = mapped_column(
        String(30),
        default="PRESENCIAL",
        nullable=False
    )

    cupo: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    conferencistas: Mapped[list[Conferencista]] = relationship(
        secondary=actividad_conferencista,
        lazy="selectin"
    )


# ============================================================
# USUARIOS
# ============================================================

class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    nombres: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    apellidos: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        "correo",
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        "contrasena_hash",
        String(255),
        nullable=False
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    roles: Mapped[list[RolSistema]] = relationship(
        secondary=usuario_rol,
        lazy="selectin"
    )