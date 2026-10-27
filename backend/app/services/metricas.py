# Servicio de métricas para el dashboard de eventos (HU09).
#
# Todas las métricas se resuelven con consultas agregadas (GROUP BY en la
# base de datos) y una cantidad fija de consultas, sin importar cuántos
# participantes o actividades tenga el evento.
#
# Criterios:
# - Cupos ocupados = inscripciones confirmadas.
# - La asistencia solo considera inscripciones confirmadas: lo esperado por
#   actividad es la cantidad de confirmados, y lo que no está marcado como
#   presente o ausente cuenta como "sin registro".

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models import Actividad, Asistencia, Evento, Inscripcion
from app.schemas import (
    MetricasAsistencia,
    MetricasAsistenciaActividad,
    MetricasCupos,
    MetricasEventoResponse,
    MetricasEventoResumen,
    MetricasInscripciones,
)


CONFIRMADA = "confirmada"


def _porcentaje(parte: int, total: int) -> float:
    return round(parte * 100 / total, 2) if total else 0.0


def _contar_si(condicion):
    return func.coalesce(func.sum(case((condicion, 1), else_=0)), 0)


def _asistencias_confirmadas(*columnas):
    # Asistencias de inscripciones confirmadas, a actividades del mismo
    # evento de la inscripción.
    return (
        select(*columnas)
        .select_from(Asistencia)
        .join(Inscripcion, Inscripcion.id_inscripcion == Asistencia.id_inscripcion)
        .join(
            Actividad,
            and_(
                Actividad.id_actividad == Asistencia.id_actividad,
                Actividad.id_evento == Inscripcion.id_evento,
            ),
        )
        .where(Inscripcion.estado == CONFIRMADA)
    )


def _metricas_inscripciones(db: Session, id_evento: int) -> MetricasInscripciones:
    conteos = dict(
        db.execute(
            select(Inscripcion.estado, func.count())
            .where(Inscripcion.id_evento == id_evento)
            .group_by(Inscripcion.estado)
        ).all()
    )
    return MetricasInscripciones(
        total=sum(conteos.values()),
        confirmadas=conteos.get(CONFIRMADA, 0),
        lista_de_espera=conteos.get("lista_de_espera", 0),
        pendientes=conteos.get("pendiente", 0),
        canceladas=conteos.get("cancelada", 0),
        rechazadas=conteos.get("rechazada", 0),
    )


def _metricas_asistencia(db: Session, id_evento: int, confirmadas: int) -> MetricasAsistencia:
    por_actividad = (
        _asistencias_confirmadas(
            Asistencia.id_actividad,
            _contar_si(Asistencia.estado == "presente").label("presentes"),
            _contar_si(Asistencia.estado == "ausente").label("ausentes"),
        )
        .where(Inscripcion.id_evento == id_evento)
        .group_by(Asistencia.id_actividad)
        .subquery()
    )

    rows = db.execute(
        select(
            Actividad.id_actividad,
            Actividad.titulo,
            Actividad.fecha,
            Actividad.hora_inicio,
            Actividad.cupo,
            func.coalesce(por_actividad.c.presentes, 0),
            func.coalesce(por_actividad.c.ausentes, 0),
        )
        .outerjoin(por_actividad, por_actividad.c.id_actividad == Actividad.id_actividad)
        .where(Actividad.id_evento == id_evento)
        .order_by(Actividad.fecha, Actividad.hora_inicio, Actividad.id_actividad)
    ).all()

    actividades = [
        MetricasAsistenciaActividad(
            id_actividad=id_actividad,
            titulo=titulo,
            fecha=fecha,
            hora_inicio=hora_inicio,
            cupo=cupo,
            presentes=presentes,
            ausentes=ausentes,
            sin_registro=max(confirmadas - presentes - ausentes, 0),
            porcentaje_asistencia=_porcentaje(presentes, confirmadas),
        )
        for id_actividad, titulo, fecha, hora_inicio, cupo, presentes, ausentes in rows
    ]

    presentes = sum(a.presentes for a in actividades)
    esperados = confirmadas * len(actividades)
    return MetricasAsistencia(
        total_actividades=len(actividades),
        presentes=presentes,
        ausentes=sum(a.ausentes for a in actividades),
        sin_registro=sum(a.sin_registro for a in actividades),
        porcentaje_asistencia=_porcentaje(presentes, esperados),
        actividades=actividades,
    )


def metricas_evento(db: Session, evento: Evento) -> MetricasEventoResponse:
    inscripciones = _metricas_inscripciones(db, evento.id_evento)
    ocupados = inscripciones.confirmadas

    return MetricasEventoResponse(
        id_evento=evento.id_evento,
        nombre=evento.nombre,
        estado=evento.estado,
        inscripciones=inscripciones,
        cupos=MetricasCupos(
            cupo_maximo=evento.cupo_maximo,
            ocupados=ocupados,
            disponibles=max(evento.cupo_maximo - ocupados, 0),
            porcentaje_ocupacion=_porcentaje(ocupados, evento.cupo_maximo),
        ),
        asistencia=_metricas_asistencia(db, evento.id_evento, ocupados),
    )


def resumen_eventos(db: Session) -> list[MetricasEventoResumen]:
    # Una sola consulta: cada agregado se calcula en una subconsulta
    # agrupada por evento y se une al evento con LEFT JOIN.
    inscripciones = (
        select(
            Inscripcion.id_evento,
            _contar_si(Inscripcion.estado == CONFIRMADA).label("confirmadas"),
            _contar_si(Inscripcion.estado == "lista_de_espera").label("lista_de_espera"),
        )
        .group_by(Inscripcion.id_evento)
        .subquery()
    )
    actividades = (
        select(Actividad.id_evento, func.count().label("total"))
        .group_by(Actividad.id_evento)
        .subquery()
    )
    presentes = (
        _asistencias_confirmadas(Inscripcion.id_evento, func.count().label("presentes"))
        .where(Asistencia.estado == "presente")
        .group_by(Inscripcion.id_evento)
        .subquery()
    )

    rows = db.execute(
        select(
            Evento,
            func.coalesce(inscripciones.c.confirmadas, 0),
            func.coalesce(inscripciones.c.lista_de_espera, 0),
            func.coalesce(actividades.c.total, 0),
            func.coalesce(presentes.c.presentes, 0),
        )
        .outerjoin(inscripciones, inscripciones.c.id_evento == Evento.id_evento)
        .outerjoin(actividades, actividades.c.id_evento == Evento.id_evento)
        .outerjoin(presentes, presentes.c.id_evento == Evento.id_evento)
        .order_by(Evento.fecha_inicio.desc(), Evento.id_evento)
    ).all()

    return [
        MetricasEventoResumen(
            id_evento=evento.id_evento,
            nombre=evento.nombre,
            estado=evento.estado,
            fecha_inicio=evento.fecha_inicio,
            cupo_maximo=evento.cupo_maximo,
            inscriptos_confirmados=confirmadas,
            lista_de_espera=lista_de_espera,
            porcentaje_ocupacion=_porcentaje(confirmadas, evento.cupo_maximo),
            total_actividades=total_actividades,
            porcentaje_asistencia=_porcentaje(total_presentes, confirmadas * total_actividades),
        )
        for evento, confirmadas, lista_de_espera, total_actividades, total_presentes in rows
    ]
