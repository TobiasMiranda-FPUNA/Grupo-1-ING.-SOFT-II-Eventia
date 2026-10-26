# Pruebas de integración - Sprint 4

Estas pruebas sirven como checklist para la evidencia del informe.

| ID | Flujo | Resultado esperado |
|---|---|---|
| PI-01 | Crear evento → consultar catálogo | El evento aparece en el catálogo luego de guardarse. |
| PI-02 | Evento publicado → inscripción pública | Con cupo disponible la inscripción queda `confirmada`. |
| PI-03 | Evento sin cupo + lista de espera | La siguiente inscripción queda `lista_de_espera`. |
| PI-04 | Evento → actividades → agenda pública | Las actividades aparecen ordenadas por fecha y hora. |
| PI-05 | Evento → actividad → asistencia | Se muestran inscriptos confirmados y se guarda presente/ausente. |
| PI-06 | Guardar dos veces la misma asistencia | Se actualiza el registro existente; no se duplica. |
| PI-07 | Asistencias → elegibilidad | Se calcula el porcentaje y se compara con el mínimo del evento. |
| PI-08 | Participante elegible → generar certificado | Se crea un certificado con código único. |
| PI-09 | Certificado → verificación pública | El código devuelve participante, evento y fecha de emisión. |
| PI-10 | Código inexistente | La interfaz informa que el certificado no es válido. |

## Flujo recomendado para la demostración

1. Iniciar sesión como Organizador.
2. Crear o seleccionar un evento con política de certificación.
3. Verificar que existan actividades en su agenda.
4. Realizar una inscripción pública y confirmar que su estado sea `confirmada`.
5. Entrar a **Asistencias**, seleccionar el evento y registrar presencia en las actividades.
6. Entrar a **Certificados** y comprobar el porcentaje calculado.
7. Generar el certificado cuando alcance el mínimo configurado.
8. Descargar el certificado.
9. Abrir **Verificación pública** e ingresar el código generado.
10. Confirmar que los datos mostrados coincidan con el participante y evento.

## Pruebas automatizadas

Desde la carpeta `backend`:

```bash
DATABASE_URL=sqlite:///:memory: python -m pytest -q
```

La suite incluye pruebas de asistencia, certificado y un flujo integrado de Sprint 4.
