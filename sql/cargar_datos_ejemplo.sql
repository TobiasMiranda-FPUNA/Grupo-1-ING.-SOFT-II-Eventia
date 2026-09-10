-- ============================================================
-- cargar_datos_ejemplo.sql
-- Proyecto: Eventia
-- Motor: PostgreSQL
--
-- Datos de ejemplo para las tablas transaccionales creadas en
-- crear_usuario_rol_sistema_usuario_rol.sql, crear_tipo_evento_
-- evento_politica.sql y crear_participante_inscripcion.sql,
-- respetando el modelo entidad-relación y las reglas funcionales
-- descritas en el informe de Sprint 1 (secciones 1.3, 1.4 y 1.6).
--
-- Orden de ejecución sugerido (todas idempotentes, se pueden
-- volver a correr sin duplicar datos):
--   1. crear_usuario_rol_sistema_usuario_rol.sql
--   2. crear_rol_participante_y_catalogo.sql
--   3. crear_tipo_evento_evento_politica.sql
--   4. crear_participante_inscripcion.sql
--   5. cargar_catalogos_iniciales.sql   (catálogos ROL_SISTEMA y TIPO_EVENTO)
--   6. cargar_datos_ejemplo.sql         (este script)
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

COMMIT;
