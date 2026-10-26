# Scripts SQL de Eventia

La base de datos utiliza PostgreSQL. Los scripts se ejecutan en orden desde `scripts/setup_local_db.sh` o `scripts/setup_local_db.ps1`.

## Tablas principales

- `usuario`: cuentas que pueden autenticarse en la aplicación.
- `rol_sistema`: catálogo de roles para permisos del sistema.
- `usuario_rol`: relaciona usuarios con roles del sistema.
- `rol_participante`: funciones que una persona puede cumplir dentro de un evento.
- `tipo_evento`: tipos de eventos, como congresos, seminarios, talleres o jornadas.
- `evento`: información principal de cada evento.
- `politica_inscripcion`: reglas de inscripción y certificación de un evento.
- `participante`: datos de las personas que participan o se inscriben.
- `inscripcion`: relaciona un participante con un evento y su estado.
- `categoria_actividad`: categorías de las actividades del evento.
- `actividad`: sesiones o actividades que conforman la agenda.
- `conferencista`: datos de expositores o especialistas.
- `actividad_conferencista`: relaciona actividades con conferencistas.
- `asistencia`: registra la presencia de una inscripción en una actividad e impide duplicados mediante `UNIQUE (id_inscripcion, id_actividad)`.
- `certificado`: registra certificados emitidos y genera un código único para su verificación pública.

## Prueba rápida de certificado

Una vez que exista una inscripción válida, se puede crear un certificado de prueba dejando que PostgreSQL genere el código automáticamente:

```sql
INSERT INTO certificado (id_inscripcion)
VALUES (1)
RETURNING id_certificado, codigo_validacion;
```

El código retornado puede verificarse desde la ruta pública del frontend `/certificados/verificar`.

## Compatibilidad con instalaciones anteriores

`ajustar_compatibilidad_backend.sql` normaliza los estados de `evento` e `inscripcion` a los valores en minúsculas que usa el backend actual, permite participante sin documento y agrega `especialidad` a `conferencista` si todavía no existe.
