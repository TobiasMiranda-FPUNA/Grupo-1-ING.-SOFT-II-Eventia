-- ============================================================
-- ajustar_compatibilidad_backend.sql
-- Proyecto: Eventia - Sistema de Gestión de Eventos
-- Motor: PostgreSQL
--
-- Ajusta instalaciones creadas con versiones anteriores de los
-- scripts SQL para que coincidan con los valores y campos que ya
-- utiliza el backend actual. Es seguro volver a ejecutarlo.
-- ============================================================

BEGIN;

-- EVENTO: el backend trabaja con estados en minúsculas.
ALTER TABLE IF EXISTS evento
    DROP CONSTRAINT IF EXISTS ck_evento_estado;

UPDATE evento
SET estado = CASE UPPER(estado)
    WHEN 'BORRADOR' THEN 'borrador'
    WHEN 'PUBLICADO' THEN 'publicado'
    WHEN 'FINALIZADO' THEN 'finalizado'
    WHEN 'CANCELADO' THEN 'cancelado'
    ELSE LOWER(estado)
END;

ALTER TABLE IF EXISTS evento
    ALTER COLUMN estado SET DEFAULT 'borrador';

ALTER TABLE IF EXISTS evento
    ADD CONSTRAINT ck_evento_estado
    CHECK (estado IN ('borrador', 'publicado', 'finalizado', 'cancelado'));

-- INSCRIPCION: estados usados por la lógica pública de cupos/lista de espera.
ALTER TABLE IF EXISTS inscripcion
    DROP CONSTRAINT IF EXISTS ck_inscripcion_estado;

UPDATE inscripcion
SET estado = CASE UPPER(estado)
    WHEN 'PENDIENTE' THEN 'pendiente'
    WHEN 'CONFIRMADA' THEN 'confirmada'
    WHEN 'LISTA_ESPERA' THEN 'lista_de_espera'
    WHEN 'CANCELADA' THEN 'cancelada'
    WHEN 'RECHAZADA' THEN 'rechazada'
    ELSE LOWER(estado)
END;

ALTER TABLE IF EXISTS inscripcion
    ALTER COLUMN estado TYPE VARCHAR(30),
    ALTER COLUMN estado SET DEFAULT 'confirmada';

ALTER TABLE IF EXISTS inscripcion
    ADD CONSTRAINT ck_inscripcion_estado
    CHECK (estado IN ('pendiente', 'confirmada', 'lista_de_espera', 'cancelada', 'rechazada'));

-- El backend actual permite participante sin documento.
ALTER TABLE IF EXISTS participante
    ALTER COLUMN documento DROP NOT NULL;

ALTER TABLE IF EXISTS participante
    DROP CONSTRAINT IF EXISTS ck_participante_documento_no_vacio;

-- El frontend/backend de expositores ya utiliza especialidad.
ALTER TABLE IF EXISTS conferencista
    ADD COLUMN IF NOT EXISTS especialidad VARCHAR(150);

COMMIT;
