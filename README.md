# Grupo-1-ING.-SOFT-II-Eventia

Proyecto de gestión de eventos académicos y profesionales.
# Eventia - Módulo Frontend

Este proyecto contiene el Frontend de la aplicación **Eventia** (Sistema de Gestión de Eventos), desarrollado con Angular.

## 🚀 Tecnologías utilizadas

* **Angular** (v17+)
* **TypeScript**
* **SCSS** (Estilos)
* **RxJS** & **HttpClient** (Consumo de APIs REST)

---

## 🛠️ Funcionalidades desarrolladas

### 1. Autenticación de Usuarios (HU01)
* **Formulario de Login:** Validación en tiempo real de formato de correo y longitud de contraseña.
* **Manejo de Errores:** Notificación clara ante credenciales incorrectas sin exponer detalles específicos del fallo.
* **Persistencia:** Almacenamiento seguro del token de sesión (`access_token`) en `localStorage`.

### 2. Administración de Catálogos y Roles (HU02)
* **Gestión de Roles:** Interfaz para la creación y visualización de roles de participantes (ej. *Estudiante*, *Expositor*).
* **Control de Regla de Negocio:** Bloqueo de eliminación y notificación en pantalla si un rol está asociado a inscripciones activas.

---

## 💻 Instrucciones para ejecutar el proyecto

### Prerequisitos
* Node.js (v18 o superior)
* npm (v10 o superior)

### Pasos de instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd Grupo-1-ING.-SOFT-II-Eventia/frontend
   Instalar dependencias:

Bash
npm install
Iniciar servidor de desarrollo:

Bash
ng serve
Acceder a la aplicación:
Abre tu navegador web e ingresa a http://localhost:4200/.

## Backend

La API REST está implementada con Python, FastAPI y PostgreSQL dentro de la carpeta `backend/`.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

La documentación interactiva queda disponible en `/docs`. El endpoint de autenticación es `POST /api/v1/auth/login`.
# SCRIPTS SQL DE LA BASE DE DATOS DEL SISTEMA
La base de datos es en PostgresSQL
## Estructura general
La base inicial está compuesta por las siguientes tablas:
## Tabla finalidad

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



---

## Funcionalidades integradas del Sprint 4

### Registro de asistencia (HU07)
- Vista autenticada en `/asistencias`.
- Selección de evento y actividad.
- Lista únicamente las inscripciones confirmadas del evento.
- Permite marcar cada participante como `presente` o `ausente`.
- El backend actualiza el registro si ya existía y conserva la restricción
  `UNIQUE (id_inscripcion, id_actividad)` para impedir duplicados.
- Acceso para Organizador, Administrador y Personal de acreditación.

### Certificados (HU08)
- Vista autenticada en `/certificados`.
- Calcula el porcentaje de asistencia usando las actividades del evento.
- Compara el porcentaje obtenido con `min_asistencia_certificado` de la
  política de inscripción.
- El botón **Generar** solo queda habilitado cuando el participante cumple
  el mínimo configurado.
- Cada certificado posee un `codigo_validacion` único.
- Un certificado emitido puede descargarse y verificarse desde la interfaz
  pública `/certificados/verificar`.

### Flujo integrado
`Evento → Inscripción → Agenda/Actividad → Asistencia → Certificado → Verificación pública`

### Pruebas
Desde `backend/` se puede ejecutar:

```bash
DATABASE_URL=sqlite:///:memory: python -m pytest -q
```

La suite incluye pruebas específicas de asistencia, elegibilidad/emisión de
certificados y un flujo integrado de Sprint 4.
