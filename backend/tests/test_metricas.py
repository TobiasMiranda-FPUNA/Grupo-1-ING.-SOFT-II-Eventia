from datetime import date, time

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.api.eventos import get_dashboard_evento
from app.db import Base
from app.models import (
    Actividad,
    Asistencia,
    CategoriaActividad,
    Evento,
    Inscripcion,
    Participante,
    RolParticipante,
    TipoEvento,
)
from app.services.metricas import metricas_evento, resumen_eventos


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session


def _inscribir(db, evento, rol, nombre, estado):
    participante = Participante(nombres=nombre, apellidos="Test", email=f"{nombre}@example.com")
    db.add(participante)
    db.flush()
    inscripcion = Inscripcion(
        id_evento=evento.id_evento,
        id_participante=participante.id_participante,
        id_rol_participante=rol.id_rol_participante,
        estado=estado,
    )
    db.add(inscripcion)
    db.flush()
    return inscripcion


def _actividad(db, evento, categoria, hora):
    actividad = Actividad(
        id_evento=evento.id_evento,
        id_categoria=categoria.id_categoria,
        titulo=f"Actividad {hora}",
        fecha=date(2026, 11, 10),
        hora_inicio=time(hora, 0),
        hora_fin=time(hora, 30),
        modalidad="PRESENCIAL",
        cupo=20,
    )
    db.add(actividad)
    db.flush()
    return actividad


@pytest.fixture
def escenario(db):
    tipo = TipoEvento(nombre="Congreso")
    categoria = CategoriaActividad(nombre="Conferencia", activo=True)
    rol = RolParticipante(nombre="Asistente", activo=True)
    db.add_all([tipo, categoria, rol])
    db.flush()

    evento = Evento(
        id_tipo_evento=tipo.id_tipo_evento,
        nombre="Congreso",
        fecha_inicio=date(2026, 11, 10),
        fecha_fin=date(2026, 11, 11),
        cupo_maximo=4,
        estado="publicado",
    )
    vacio = Evento(
        id_tipo_evento=tipo.id_tipo_evento,
        nombre="Vacío",
        fecha_inicio=date(2026, 12, 1),
        fecha_fin=date(2026, 12, 1),
        cupo_maximo=10,
        estado="borrador",
    )
    db.add_all([evento, vacio])
    db.flush()

    act1 = _actividad(db, evento, categoria, 9)
    act2 = _actividad(db, evento, categoria, 11)

    ana = _inscribir(db, evento, rol, "ana", "confirmada")
    beto = _inscribir(db, evento, rol, "beto", "confirmada")
    caro = _inscribir(db, evento, rol, "caro", "confirmada")
    _inscribir(db, evento, rol, "dani", "lista_de_espera")
    eli = _inscribir(db, evento, rol, "eli", "cancelada")

    def marcar(inscripcion, actividad, estado):
        db.add(Asistencia(
            id_inscripcion=inscripcion.id_inscripcion,
            id_actividad=actividad.id_actividad,
            estado=estado,
        ))

    marcar(ana, act1, "presente")
    marcar(beto, act1, "presente")
    marcar(caro, act1, "ausente")
    marcar(ana, act2, "presente")
    # Asistencia de una inscripción cancelada: no debe contarse.
    marcar(eli, act1, "presente")
    db.commit()
    return {"evento": evento, "vacio": vacio, "rol": rol, "categoria": categoria}


def test_metricas_evento_inscripciones_y_cupos(db, escenario):
    metricas = metricas_evento(db, escenario["evento"])

    assert metricas.inscripciones.model_dump() == {
        "total": 5,
        "confirmadas": 3,
        "lista_de_espera": 1,
        "pendientes": 0,
        "canceladas": 1,
        "rechazadas": 0,
    }
    assert metricas.cupos.model_dump() == {
        "cupo_maximo": 4,
        "ocupados": 3,
        "disponibles": 1,
        "porcentaje_ocupacion": 75.0,
    }


def test_metricas_evento_asistencia_por_actividad(db, escenario):
    asistencia = metricas_evento(db, escenario["evento"]).asistencia

    assert asistencia.total_actividades == 2
    assert asistencia.presentes == 3
    assert asistencia.ausentes == 1
    assert asistencia.sin_registro == 2
    assert asistencia.porcentaje_asistencia == 50.0

    act1, act2 = asistencia.actividades
    assert (act1.presentes, act1.ausentes, act1.sin_registro) == (2, 1, 0)
    assert act1.porcentaje_asistencia == 66.67
    assert (act2.presentes, act2.ausentes, act2.sin_registro) == (1, 0, 2)
    assert act2.porcentaje_asistencia == 33.33


def test_resumen_eventos(db, escenario):
    resumen = {r.id_evento: r for r in resumen_eventos(db)}

    congreso = resumen[escenario["evento"].id_evento]
    assert congreso.inscriptos_confirmados == 3
    assert congreso.lista_de_espera == 1
    assert congreso.porcentaje_ocupacion == 75.0
    assert congreso.total_actividades == 2
    assert congreso.porcentaje_asistencia == 50.0

    vacio = resumen[escenario["vacio"].id_evento]
    assert vacio.inscriptos_confirmados == 0
    assert vacio.total_actividades == 0
    assert vacio.porcentaje_ocupacion == 0.0
    assert vacio.porcentaje_asistencia == 0.0


def test_cantidad_de_consultas_no_depende_del_volumen(engine, db, escenario):
    evento = escenario["evento"]
    # Se agregan más participantes y actividades con asistencia.
    for i in range(20):
        inscripcion = _inscribir(db, evento, escenario["rol"], f"extra{i}", "confirmada")
        actividad = _actividad(db, evento, escenario["categoria"], 12 + i % 8)
        db.add(Asistencia(
            id_inscripcion=inscripcion.id_inscripcion,
            id_actividad=actividad.id_actividad,
            estado="presente",
        ))
    db.commit()
    db.refresh(evento)

    consultas = []
    listener = lambda *args: consultas.append(args[2])  # noqa: E731
    event.listen(engine, "before_cursor_execute", listener)
    try:
        metricas_evento(db, evento)
        detalle = len(consultas)
        consultas.clear()
        resumen_eventos(db)
        resumen = len(consultas)
    finally:
        event.remove(engine, "before_cursor_execute", listener)

    assert detalle == 2
    assert resumen == 1


def test_dashboard_evento(db, escenario):
    dashboard = get_dashboard_evento(escenario["evento"].id_evento, db, None)

    assert dashboard.id_evento == escenario["evento"].id_evento
    assert dashboard.inscripciones.confirmadas == 3
    assert dashboard.cupos.disponibles == 1
    assert dashboard.asistencia.porcentaje_asistencia == 50.0
    assert len(dashboard.asistencia.actividades) == 2


def test_dashboard_evento_inexistente_devuelve_404(db):
    with pytest.raises(HTTPException) as error:
        get_dashboard_evento(9999, db, None)
    assert error.value.status_code == 404
