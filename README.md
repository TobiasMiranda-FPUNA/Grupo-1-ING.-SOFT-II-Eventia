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
La base inicial está compuesta por cuatro tablas principales:
## Tabla	Finalidad
- usuario	Almacena las cuentas que pueden autenticarse en la aplicación.
- rol_sistema	Catálogo de roles utilizados para controlar permisos y acceso al sistema.
- usuario_rol	Tabla intermedia que relaciona usuarios con roles del sistema.
- rol_participante	Catálogo de funciones que una persona puede cumplir dentro de un evento.

