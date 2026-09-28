-- ============================================================
-- cargar_datos_ejemplo.sql
-- Proyecto: Eventia
-- Motor: PostgreSQL
--
-- Datos de ejemplo para las tablas transaccionales creadas en
-- crear_usuario_rol_sistema_usuario_rol.sql, crear_tipo_evento_
-- evento_politica.sql, crear_participante_inscripcion.sql,
-- crear_categoria_actividad_actividad.sql y crear_conferencista_
-- actividad_conferencista.sql, respetando el modelo entidad-relación
-- y las reglas funcionales descritas en el informe de Sprint 1
-- (secciones 1.3, 1.4 y 1.6).
--
-- Orden de ejecución sugerido (todas idempotentes, se pueden
-- volver a correr sin duplicar datos):
--   1. crear_usuario_rol_sistema_usuario_rol.sql
--   2. crear_rol_participante_y_catalogo.sql
--   3. crear_tipo_evento_evento_politica.sql
--   4. crear_participante_inscripcion.sql
--   5. crear_categoria_actividad_actividad.sql
--   6. crear_conferencista_actividad_conferencista.sql
--   7. cargar_catalogos_iniciales.sql   (ROL_SISTEMA, TIPO_EVENTO y CATEGORIA_ACTIVIDAD)
--   8. cargar_datos_ejemplo.sql         (este script)
--
-- IMPORTANTE: los usuarios y contraseñas creados aquí son
-- únicamente para pruebas locales/desarrollo. No usar en producción.
--   admin@eventia.test        / Admin123!
--   organizador@eventia.test  / Organizador123!
-- Los hashes fueron generados con Argon2 (misma librería que usa
-- el backend en app/core/security.py) para que el login funcione
-- de verdad contra estos datos de ejemplo.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- USUARIO: cuentas de acceso de ejemplo (administrador y
-- organizador). Los participantes de más abajo no requieren
-- cuenta de usuario del sistema (ver 4.2 del informe).
-- ------------------------------------------------------------
INSERT INTO usuario (nombres, apellidos, correo, contrasena_hash)
VALUES
    ('Ana', 'Duarte', 'admin@eventia.test',
     '$argon2id$v=19$m=65536,t=3,p=4$rtUP+TyGwUvWG48J0oml2Q$HqQIuYYQCC+SFTPfCx6MFjtzG4hi612MLp3wiPPdvIA'),
    ('Carlos', 'Benítez', 'organizador@eventia.test',
     '$argon2id$v=19$m=65536,t=3,p=4$GTaSo+LO8hgmOMufEKVP1g$AdoLESyVY4iOsMCZV5Rl9oKKtTx+d2iesc/Lo56a9E4')
ON CONFLICT (correo) DO NOTHING;

-- USUARIO_ROL: asigna el rol de sistema correspondiente a cada
-- cuenta de ejemplo.
INSERT INTO usuario_rol (id_usuario, id_rol_sistema)
SELECT u.id_usuario, rs.id_rol_sistema
FROM usuario u
JOIN rol_sistema rs ON rs.codigo = 'ADMINISTRADOR'
WHERE u.correo = 'admin@eventia.test'
ON CONFLICT (id_usuario, id_rol_sistema) DO NOTHING;

INSERT INTO usuario_rol (id_usuario, id_rol_sistema)
SELECT u.id_usuario, rs.id_rol_sistema
FROM usuario u
JOIN rol_sistema rs ON rs.codigo = 'ORGANIZADOR'
WHERE u.correo = 'organizador@eventia.test'
ON CONFLICT (id_usuario, id_rol_sistema) DO NOTHING;

-- ------------------------------------------------------------
-- EVENTO: un evento por cada tipo relevante mencionado en el
-- informe (congreso, taller, seminario).
-- ------------------------------------------------------------
INSERT INTO evento (
    id_tipo_evento, nombre, descripcion,
    fecha_inicio, fecha_fin, lugar, cupo_maximo, estado
)
SELECT te.id_tipo_evento, v.nombre, v.descripcion,
       v.fecha_inicio, v.fecha_fin, v.lugar, v.cupo_maximo, v.estado
FROM (VALUES
    ('CONGRESO', 'Congreso Nacional de Tecnología 2026',
     'Congreso académico con ponencias sobre desarrollo de software e innovación.',
     DATE '2026-11-10', DATE '2026-11-12', 'Facultad Politécnica - San Lorenzo', 200, 'PUBLICADO'),
    ('TALLER', 'Taller de Testing Ágil',
     'Taller práctico sobre técnicas de testing en equipos ágiles.',
     DATE '2026-10-05', DATE '2026-10-05', 'Laboratorio de Informática 3', 30, 'PUBLICADO'),
    ('SEMINARIO', 'Seminario de Arquitectura de Software',
     'Seminario introductorio a arquitecturas monolíticas y de microservicios.',
     DATE '2026-09-25', DATE '2026-09-25', 'Auditorio Central', 80, 'BORRADOR')
) AS v(codigo_tipo, nombre, descripcion, fecha_inicio, fecha_fin, lugar, cupo_maximo, estado)
JOIN tipo_evento te ON te.codigo = v.codigo_tipo
WHERE NOT EXISTS (
    SELECT 1 FROM evento e WHERE e.nombre = v.nombre
);

-- ------------------------------------------------------------
-- POLITICA_INSCRIPCION: una política por evento de ejemplo.
-- ------------------------------------------------------------
INSERT INTO politica_inscripcion (
    id_evento, fecha_limite, requiere_aprobacion,
    permite_lista_espera, min_asistencia_certificado
)
SELECT e.id_evento, v.fecha_limite, v.requiere_aprobacion,
       v.permite_lista_espera, v.min_asistencia_certificado
FROM (VALUES
    ('Congreso Nacional de Tecnología 2026', DATE '2026-11-05', FALSE, TRUE, 75),
    ('Taller de Testing Ágil', DATE '2026-10-01', TRUE, FALSE, 100),
    ('Seminario de Arquitectura de Software', DATE '2026-09-20', FALSE, TRUE, 60)
) AS v(nombre_evento, fecha_limite, requiere_aprobacion, permite_lista_espera, min_asistencia_certificado)
JOIN evento e ON e.nombre = v.nombre_evento
ON CONFLICT (id_evento) DO NOTHING;

-- ------------------------------------------------------------
-- PARTICIPANTE: personas inscriptas de ejemplo, sin cuenta de
-- usuario del sistema (documento/email de contacto únicamente).
-- ------------------------------------------------------------
INSERT INTO participante (documento, nombres, apellidos, email, institucion)
SELECT v.documento, v.nombres, v.apellidos, v.email, v.institucion
FROM (VALUES
    ('4123456', 'Lucía', 'Fernández', 'lucia.fernandez@example.com', 'Universidad Nacional de Asunción'),
    ('4234567', 'Marcos', 'Ortiz', 'marcos.ortiz@example.com', 'Facultad Politécnica'),
    ('4345678', 'Valeria', 'Gómez', 'valeria.gomez@example.com', NULL),
    ('4456789', 'Diego', 'Cáceres', 'diego.caceres@example.com', 'Instituto Superior de Informática')
) AS v(documento, nombres, apellidos, email, institucion)
WHERE NOT EXISTS (
    SELECT 1 FROM participante p WHERE p.email = v.email
);

-- ------------------------------------------------------------
-- INSCRIPCION: inscripciones de ejemplo, cubriendo distintos
-- estados y roles de participante (regla 1.6.3: máximo una
-- inscripción activa por evento y participante).
-- ------------------------------------------------------------
INSERT INTO inscripcion (id_evento, id_participante, id_rol_participante, estado)
SELECT e.id_evento, p.id_participante, rp.id_rol_participante, v.estado
FROM (VALUES
    ('Congreso Nacional de Tecnología 2026', 'lucia.fernandez@example.com', 'ASISTENTE', 'CONFIRMADA'),
    ('Congreso Nacional de Tecnología 2026', 'marcos.ortiz@example.com', 'ASISTENTE', 'CONFIRMADA'),
    ('Congreso Nacional de Tecnología 2026', 'diego.caceres@example.com', 'MODERADOR', 'CONFIRMADA'),
    ('Taller de Testing Ágil', 'valeria.gomez@example.com', 'ASISTENTE', 'PENDIENTE'),
    ('Taller de Testing Ágil', 'marcos.ortiz@example.com', 'ASISTENTE', 'LISTA_ESPERA')
) AS v(nombre_evento, email_participante, codigo_rol, estado)
JOIN evento e ON e.nombre = v.nombre_evento
JOIN participante p ON p.email = v.email_participante
JOIN rol_participante rp ON rp.codigo = v.codigo_rol
ON CONFLICT (id_evento, id_participante) DO NOTHING;

-- ------------------------------------------------------------
-- CONFERENCISTA: expositores de ejemplo (HU05). Uno queda
-- inactivo para poder probar el filtro ?activo= del listado.
-- ------------------------------------------------------------
INSERT INTO conferencista (nombres, apellidos, email, institucion, biografia, activo)
VALUES
    ('María José', 'Rolón', 'mariajose.rolon@example.com', 'Universidad Nacional de Asunción',
     'Doctora en Ciencias de la Computación. Investiga ingeniería de software empírica y calidad de software.', TRUE),
    ('Jorge', 'Villalba', 'jorge.villalba@example.com', 'Facultad Politécnica',
     'Arquitecto de software con más de 15 años de experiencia en sistemas distribuidos y microservicios.', TRUE),
    ('Sofía', 'Benítez', 'sofia.benitez@example.com', 'Consultora independiente',
     'Especialista en DevOps, integración continua y automatización de pruebas.', TRUE),
    ('Ricardo', 'Aquino', 'ricardo.aquino@example.com', 'Comunidad de Software Libre',
     'Desarrollador y divulgador de proyectos de código abierto.', TRUE),
    ('Elena', 'Martínez', 'elena.martinez@example.com', 'Instituto Superior de Informática',
     'Docente e instructora de testing ágil, TDD y BDD.', TRUE),
    ('Andrés', 'Paredes', 'andres.paredes@example.com', NULL,
     'Conferencista dado de baja, conservado para pruebas del filtro de inactivos.', FALSE)
ON CONFLICT (email) DO NOTHING;

-- ------------------------------------------------------------
-- ACTIVIDAD: agenda de ejemplo de cada evento (HU06). Todas las
-- fechas caen dentro del rango del evento al que pertenecen,
-- igual que valida POST /api/v1/eventos/{id}/actividades.
-- ------------------------------------------------------------
INSERT INTO actividad (
    id_evento, id_categoria, titulo, descripcion,
    fecha, hora_inicio, hora_fin, lugar, modalidad, cupo
)
SELECT e.id_evento, ca.id_categoria, v.titulo, v.descripcion,
       v.fecha, v.hora_inicio, v.hora_fin, v.lugar, v.modalidad, v.cupo
FROM (VALUES
    ('Congreso Nacional de Tecnología 2026', 'Conferencia',
     'Apertura: el futuro del desarrollo de software',
     'Conferencia inaugural sobre las tendencias que marcarán la próxima década de la ingeniería de software.',
     DATE '2026-11-10', TIME '09:00', TIME '10:00', 'Auditorio Central', 'PRESENCIAL', 200),
    ('Congreso Nacional de Tecnología 2026', 'Conferencia',
     'Inteligencia artificial aplicada a la ingeniería de software',
     'Casos reales de uso de modelos de lenguaje en el ciclo de vida del software.',
     DATE '2026-11-10', TIME '10:30', TIME '12:00', 'Auditorio Central', 'HIBRIDA', 200),
    ('Congreso Nacional de Tecnología 2026', 'Panel',
     'Panel: DevOps en la industria local',
     'Experiencias de equipos locales adoptando integración y entrega continua.',
     DATE '2026-11-11', TIME '14:00', TIME '15:30', 'Sala de Conferencias A', 'HIBRIDA', 120),
    ('Congreso Nacional de Tecnología 2026', 'Charla',
     'Cómo contribuir a proyectos open source',
     'Primeros pasos para colaborar en proyectos de código abierto.',
     DATE '2026-11-12', TIME '11:00', TIME '11:45', 'Sala de Conferencias B', 'VIRTUAL', 300),
    ('Congreso Nacional de Tecnología 2026', 'Mesa redonda',
     'Mesa redonda: ética y tecnología',
     'Debate sobre privacidad, sesgos algorítmicos y responsabilidad profesional.',
     DATE '2026-11-12', TIME '16:00', TIME '17:30', 'Auditorio Central', 'PRESENCIAL', 150),
    ('Taller de Testing Ágil', 'Taller',
     'Introducción a TDD con pytest',
     'Ciclo rojo-verde-refactor aplicado a un proyecto Python desde cero.',
     DATE '2026-10-05', TIME '08:30', TIME '10:30', 'Laboratorio de Informática 3', 'PRESENCIAL', 30),
    ('Taller de Testing Ágil', 'Taller',
     'Pruebas de aceptación con BDD',
     'Escritura de escenarios Gherkin y su automatización.',
     DATE '2026-10-05', TIME '11:00', TIME '13:00', 'Laboratorio de Informática 3', 'PRESENCIAL', 30),
    ('Seminario de Arquitectura de Software', 'Conferencia',
     'Del monolito a los microservicios',
     'Criterios para decidir cuándo y cómo descomponer un sistema monolítico.',
     DATE '2026-09-25', TIME '18:00', TIME '20:00', 'Auditorio Central', 'PRESENCIAL', 80)
) AS v(nombre_evento, nombre_categoria, titulo, descripcion,
       fecha, hora_inicio, hora_fin, lugar, modalidad, cupo)
JOIN evento e ON e.nombre = v.nombre_evento
JOIN categoria_actividad ca ON ca.nombre = v.nombre_categoria
WHERE NOT EXISTS (
    SELECT 1 FROM actividad a
    WHERE a.id_evento = e.id_evento AND a.titulo = v.titulo
);

-- ------------------------------------------------------------
-- ACTIVIDAD_CONFERENCISTA: asignación de conferencistas a las
-- actividades, con el rol que cumple cada uno en la sesión.
-- ------------------------------------------------------------
INSERT INTO actividad_conferencista (id_actividad, id_conferencista, rol_en_actividad)
SELECT a.id_actividad, c.id_conferencista, v.rol_en_actividad
FROM (VALUES
    ('Apertura: el futuro del desarrollo de software', 'mariajose.rolon@example.com', 'CONFERENCISTA'),
    ('Inteligencia artificial aplicada a la ingeniería de software', 'jorge.villalba@example.com', 'CONFERENCISTA'),
    ('Inteligencia artificial aplicada a la ingeniería de software', 'mariajose.rolon@example.com', 'MODERADOR'),
    ('Panel: DevOps en la industria local', 'sofia.benitez@example.com', 'PANELISTA'),
    ('Panel: DevOps en la industria local', 'ricardo.aquino@example.com', 'PANELISTA'),
    ('Panel: DevOps en la industria local', 'jorge.villalba@example.com', 'MODERADOR'),
    ('Cómo contribuir a proyectos open source', 'ricardo.aquino@example.com', 'CONFERENCISTA'),
    ('Mesa redonda: ética y tecnología', 'elena.martinez@example.com', 'MODERADOR'),
    ('Mesa redonda: ética y tecnología', 'mariajose.rolon@example.com', 'PANELISTA'),
    ('Mesa redonda: ética y tecnología', 'sofia.benitez@example.com', 'PANELISTA'),
    ('Introducción a TDD con pytest', 'elena.martinez@example.com', 'INSTRUCTOR'),
    ('Pruebas de aceptación con BDD', 'elena.martinez@example.com', 'INSTRUCTOR'),
    ('Pruebas de aceptación con BDD', 'sofia.benitez@example.com', 'INSTRUCTOR'),
    ('Del monolito a los microservicios', 'jorge.villalba@example.com', 'CONFERENCISTA')
) AS v(titulo_actividad, email_conferencista, rol_en_actividad)
JOIN actividad a ON a.titulo = v.titulo_actividad
JOIN conferencista c ON c.email = v.email_conferencista
ON CONFLICT (id_actividad, id_conferencista) DO NOTHING;

COMMIT;
