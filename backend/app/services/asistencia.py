# Servicio de cálculo del porcentaje de asistencia.
#
# El porcentaje de una inscripción se calcula a partir de los registros de la
# tabla ASISTENCIA: cantidad de actividades del evento marcadas como
# "presente" sobre el total de actividades del evento. Las actividades sin
# registro cuentan como no asistidas.

from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Actividad, Asistencia, Inscripcion


@dataclass(frozen=True)
class ResumenAsistencia:
    id_inscripcion: int
    total_actividades: int
    presentes: int
    ausentes: int

    @property
    def sin_registro(self) -> int:
        return self.total_actividades - self.presentes - self.ausentes

    @property
    def porcentaje(self) -> float:
        if not self.total_actividades:
            return 0.0
        return round(self.presentes * 100 / self.total_actividades, 2)


def contar_actividades_evento(db: Session, id_evento: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Actividad)
        .where(Actividad.id_evento == id_evento)
    ) or 0


def _conteos_por_inscripcion(
    db: Session,
    id_evento: int,
    id_inscripcion: int | None = None,
) -> dict[int, tuple[int, int]]:
    # Devuelve {id_inscripcion: (presentes, ausentes)} considerando solo las
    # asistencias a actividades del evento.
    stmt = (
        select(
            Asistencia.id_inscripcion,
            func.sum(case((Asistencia.estado == "presente", 1), else_=0)),
            func.sum(case((Asistencia.estado == "ausente", 1), else_=0)),
        )
        .join(Actividad, Actividad.id_actividad == Asistencia.id_actividad)
        .where(Actividad.id_evento == id_evento)
        .group_by(Asistencia.id_inscripcion)
    )
    if id_inscripcion is not None:
        stmt = stmt.where(Asistencia.id_inscripcion == id_inscripcion)

    return {
        id_insc: (int(presentes or 0), int(ausentes or 0))
        for id_insc, presentes, ausentes in db.execute(stmt).all()
    }


def calcular_porcentaje_asistencia(
    db: Session,
    inscripcion: Inscripcion,
) -> ResumenAsistencia:
    total = contar_actividades_evento(db, inscripcion.id_evento)
    presentes, ausentes = _conteos_por_inscripcion(
        db,
        inscripcion.id_evento,
        inscripcion.id_inscripcion,
    ).get(inscripcion.id_inscripcion, (0, 0))

    return ResumenAsistencia(
        id_inscripcion=inscripcion.id_inscripcion,
        total_actividades=total,
        presentes=presentes,
        ausentes=ausentes,
    )


def calcular_porcentajes_evento(
    db: Session,
    id_evento: int,
) -> dict[int, ResumenAsistencia]:
    # Calcula el resumen de todas las inscripciones del evento con un número
    # fijo de consultas (no una por participante).
    total = contar_actividades_evento(db, id_evento)
    conteos = _conteos_por_inscripcion(db, id_evento)
    ids = db.scalars(
        select(Inscripcion.id_inscripcion).where(
            Inscripcion.id_evento == id_evento
        )
    ).all()

    resumenes = {}
    for id_insc in ids:
        presentes, ausentes = conteos.get(id_insc, (0, 0))
        resumenes[id_insc] = ResumenAsistencia(
            id_inscripcion=id_insc,
            total_actividades=total,
            presentes=presentes,
            ausentes=ausentes,
        )
    return resumenes
