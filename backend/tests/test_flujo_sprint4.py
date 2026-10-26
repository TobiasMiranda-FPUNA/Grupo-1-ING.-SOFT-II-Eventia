from datetime import date, time

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.actividades import create_actividad
from app.api.asistencias import registrar_asistencia_masiva
from app.api.certificados import emitir_certificado, verificar_certificado
from app.api.eventos import create_evento
from app.api.inscripciones import create_inscripcion
from app.db import Base
from app.models import CategoriaActividad, RolParticipante, TipoEvento
from app.schemas import (
    ActividadCreate,
    AsistenciaRegistroItem,
    AsistenciaRegistroMasivo,
    EventoCreate,
    InscripcionCreate,
    PoliticaInscripcionData,
)


def test_flujo_integrado_inscripcion_asistencia_certificado():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        tipo = TipoEvento(nombre="Congreso")
        categoria = CategoriaActividad(nombre="Conferencia", activo=True)
        rol = RolParticipante(nombre="Asistente", activo=True)
        db.add_all([tipo, categoria, rol])
        db.commit()

        evento = create_evento(
            EventoCreate(
                id_tipo_evento=tipo.id_tipo_evento,
                nombre="Sprint 4 Integrado",
                fecha_inicio=date(2026, 10, 20),
                fecha_fin=date(2026, 10, 20),
                cupo_maximo=20,
                estado="publicado",
                politica=PoliticaInscripcionData(
                    min_asistencia_certificado=100,
                    permite_lista_espera=True,
                ),
            ),
            db,
            None,
        )

        actividad = create_actividad(
            evento.id_evento,
            ActividadCreate(
                id_categoria=categoria.id_categoria,
                titulo="Actividad única",
                fecha=date(2026, 10, 20),
                hora_inicio=time(9, 0),
                hora_fin=time(10, 0),
                modalidad="PRESENCIAL",
                cupo=20,
            ),
            db,
            None,
        )

        inscripcion = create_inscripcion(
            InscripcionCreate(
                id_evento=evento.id_evento,
                id_rol_participante=rol.id_rol_participante,
                nombres="Lucía",
                apellidos="Fernández",
                email="lucia.integracion@example.com",
            ),
            db,
        )
        assert inscripcion.estado == "confirmada"

        registrar_asistencia_masiva(
            actividad.id_actividad,
            AsistenciaRegistroMasivo(
                registros=[
                    AsistenciaRegistroItem(
                        id_inscripcion=inscripcion.id_inscripcion,
                        estado="presente",
                    )
                ]
            ),
            db,
            None,
        )

        certificado = emitir_certificado(
            inscripcion.id_inscripcion,
            db,
            None,
        )
        assert certificado.elegible is True
        assert certificado.porcentaje_asistencia == 100
        assert certificado.codigo_validacion

        verificacion = verificar_certificado(
            certificado.codigo_validacion,
            db,
        )
        assert verificacion.valido is True
        assert verificacion.evento == "Sprint 4 Integrado"
        assert verificacion.participante == "Lucía Fernández"
