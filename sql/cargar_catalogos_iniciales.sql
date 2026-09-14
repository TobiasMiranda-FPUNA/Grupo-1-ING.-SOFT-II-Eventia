-- ============================================================
-- cargar_catalogos_iniciales.sql
-- Proyecto: Eventia
-- Motor: PostgreSQL
--
-- Carga de datos iniciales para los catálogos ROL_SISTEMA y
-- TIPO_EVENTO, según el informe de Sprint 1 (secciones 1.1 y 1.3)
-- y el diagrama entidad-relación de Eventia.
--
-- Dependencias:
--   rol_sistema  (crear_usuario_rol_sistema_usuario_rol.sql)
--   tipo_evento  (crear_tipo_evento_evento_politica.sql)
-- ============================================================

BEGIN;

-- Roles de acceso al sistema, según la tabla "Usuarios principales"
-- del informe (sección 1.3): Administrador, Organizador, Participante,
-- Conferencista y Personal de acreditación o apoyo.
INSERT INTO rol_sistema (codigo, nombre, descripcion)
VALUES
    ('ADMINISTRADOR', 'Administrador',
     'Configura usuarios, roles, catálogos generales y parámetros. Tiene acceso global a la administración de la plataforma.'),
    ('ORGANIZADOR', 'Organizador',
     'Crea eventos, define cupos y políticas, administra inscripciones, arma la agenda, asigna conferencistas, registra o supervisa asistencias y consulta reportes.'),
    ('PARTICIPANTE', 'Participante',
     'Se registra o es registrado en un evento, consulta información y agenda, y queda asociado a sus asistencias y certificados.'),
    ('CONFERENCISTA', 'Conferencista',
     'Responsable de una o más actividades del evento; su perfil se vincula con las sesiones en las que participa.'),
    ('ACREDITACION', 'Personal de acreditación',
     'Rol operativo opcional encargado de verificar inscripciones y registrar asistencia durante el evento.')
ON CONFLICT (codigo) DO UPDATE
SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    activo = TRUE,
    actualizado_en = CURRENT_TIMESTAMP;

-- Tipos de evento parametrizables, según la sección 1.1 del informe:
-- "congresos, seminarios, talleres, jornadas y otros eventos
-- académicos o profesionales".
INSERT INTO tipo_evento (codigo, nombre, descripcion)
VALUES
    ('CONGRESO', 'Congreso',
     'Evento académico o profesional de gran escala con múltiples actividades y conferencistas.'),
    ('SEMINARIO', 'Seminario',
     'Evento de formato acotado orientado a la profundización de un tema específico.'),
    ('TALLER', 'Taller',
     'Actividad práctica y participativa orientada al desarrollo de habilidades concretas.'),
    ('JORNADA', 'Jornada',
     'Evento de una o pocas sesiones dedicado a la difusión o discusión de un tema.'),
    ('OTRO', 'Otro',
     'Otros formatos de evento académico o profesional no cubiertos por los tipos anteriores.')
ON CONFLICT (codigo) DO UPDATE
SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    activo = TRUE,
    actualizado_en = CURRENT_TIMESTAMP;

COMMIT;
