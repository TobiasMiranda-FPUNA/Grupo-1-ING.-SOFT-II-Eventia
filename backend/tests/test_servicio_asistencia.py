from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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
from app.services.asistencia import (
    calcular_porcentaje_asistencia,
    calcular_porcentajes_evento,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _evento(db: Session, tipo: TipoEvento, nombre: str) -> Evento:
    evento = Evento(
        id_tipo_evento=tipo.id_tipo_evento,
        nombre=nombre,
        fecha_inicio=date(2026, 11, 10),
        fecha_fin=date(2026, 11, 11),
        cupo_maximo=10,
        estado="publicado",
    )
    db.add(evento)
    db.flush()
    return evento


def _actividad(db: Session, evento: Evento, categoria: CategoriaActividad, hora: int) -> Actividad:
    actividad = Actividad(
        id_evento=evento.id_evento,
        id_categoria=categoria.id_categoria,
        titulo=f"Actividad {hora}",
        fecha=date(2026, 11, 10),
        hora_inicio=time(hora, 0),
        hora_fin=time(hora, 30),
        modalidad="PRESENCIAL",
        cupo=10,
    )
    db.add(actividad)
    db.flush()
    return actividad


def _inscripcion(db: Session, evento: Evento, rol: RolParticipante, email: str) -> Inscripcion:
    participante = Participante(nombres="Ana", apellidos="Gómez", email=email)
    db.add(participante)
    db.flush()
    inscripcion = Inscripcion(
        id_evento=evento.id_evento,
        id_participante=participante.id_participante,
        id_rol_participante=rol.id_rol_participante,
        estado="confirmada",
    )
    db.add(inscripcion)
    db.flush()
    return inscripcion


@pytest.fixture
def escenario(db):
    tipo = TipoEvento(nombre="Congreso")
    categoria = CategoriaActividad(nombre="Conferencia", activo=True)
    rol = RolParticipante(nombre="Asistente", activo=True)
    db.add_all([tipo, categoria, rol])
    db.flush()

    evento = _evento(db, tipo, "Evento")
    actividades = [_actividad(db, evento, categoria, h) for h in (9, 10, 11)]
    ana = _inscripcion(db, evento, rol, "ana@example.com")
    luis = _inscripcion(db, evento, rol, "luis@example.com")

    # Ana: 2 presentes y 1 ausente. Luis: sin registros.
    db.add_all([
        Asistencia(id_inscripcion=ana.id_inscripcion, id_actividad=actividades[0].id_actividad, estado="presente"),
        Asistencia(id_inscripcion=ana.id_inscripcion, id_actividad=actividades[1].id_actividad, estado="presente"),
        Asistencia(id_inscripcion=ana.id_inscripcion, id_actividad=actividades[2].id_actividad, estado="ausente"),
    ])
    db.commit()
    return {"tipo": tipo, "categoria": categoria, "rol": rol, "evento": evento, "ana": ana, "luis": luis}


def test_porcentaje_cuenta_solo_presentes(db, escenario):
    resumen = calcular_porcentaje_asistencia(db, escenario["ana"])

    assert resumen.total_actividades == 3
    assert resumen.presentes == 2
    assert resumen.ausentes == 1
    assert resumen.sin_registro == 0
    assert resumen.porcentaje == 66.67


def test_inscripcion_sin_registros_tiene_cero(db, escenario):
    resumen = calcular_porcentaje_asistencia(db, escenario["luis"])

    assert resumen.presentes == 0
    assert resumen.sin_registro == 3
    assert resumen.porcentaje == 0.0


def test_evento_sin_actividades_devuelve_cero(db, escenario):
    vacio = _evento(db, escenario["tipo"], "Vacío")
    inscripcion = _inscripcion(db, vacio, escenario["rol"], "otra@example.com")
    db.commit()

    resumen = calcular_porcentaje_asistencia(db, inscripcion)
    assert resumen.total_actividades == 0
    assert resumen.porcentaje == 0.0


def test_ignora_asistencias_de_actividades_de_otro_evento(db, escenario):
    otro = _evento(db, escenario["tipo"], "Otro")
    ajena = _actividad(db, otro, escenario["categoria"], 15)
    db.add(Asistencia(
        id_inscripcion=escenario["luis"].id_inscripcion,
        id_actividad=ajena.id_actividad,
        estado="presente",
    ))
    db.commit()

    resumen = calcular_porcentaje_asistencia(db, escenario["luis"])
    assert resumen.presentes == 0
    assert resumen.porcentaje == 0.0


def test_porcentajes_evento_coincide_con_calculo_individual(db, escenario):
    resumenes = calcular_porcentajes_evento(db, escenario["evento"].id_evento)

    assert set(resumenes) == {escenario["ana"].id_inscripcion, escenario["luis"].id_inscripcion}
    for inscripcion in (escenario["ana"], escenario["luis"]):
        assert resumenes[inscripcion.id_inscripcion] == calcular_porcentaje_asistencia(db, inscripcion)
