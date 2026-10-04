// ============================================================
// mock-data.js
// Proyecto: Eventia - Mockup interactivo
//
// Reemplaza al backend: guarda roles, expositores, actividades,
// tipos de evento y eventos
// en localStorage para que los cambios hechos en una pantalla se
// vean en las demás. Los datos iniciales replican los catálogos
// de sql/cargar_catalogos_iniciales.sql y los datos de respaldo
// del frontend (roles.ts).
// ============================================================

(function () {
  // v2: expositores con actividades asociadas por id (cambia el formato guardado).
  const STORAGE_KEY = 'eventia-mockup-v2';

  const DATOS_INICIALES = {
    usuarios: ['admin@eventia.test', 'organizador@eventia.test'],
    roles: [
      { id: 1, nombre: 'Estudiante', descripcion: 'Participante matriculado en institución', activo: true, enUso: true },
      { id: 2, nombre: 'Expositor', descripcion: 'Conferencista o ponente de actividad', activo: true, enUso: false },
      { id: 3, nombre: 'General', descripcion: 'Público general asistente', activo: true, enUso: false },
    ],
    expositores: [
      { id_conferencista: 1, nombres: 'Juan', apellidos: 'Pérez', email: 'juan.perez@eventia.test', institucion: 'FP-UNA', especialidad: 'Testing de software', biografia: 'Especialista en pruebas y calidad de software.' },
      { id_conferencista: 2, nombres: 'Carlos Alberto', apellidos: 'Benítez Ramírez', email: 'carlos.benitez@eventia.test', institucion: 'Comunidad tecnológica', especialidad: 'Desarrollo de software', biografia: 'Ponente invitado en actividades de tecnología.' },
      { id_conferencista: 3, nombres: 'María', apellidos: 'González', email: 'maria.gonzalez@eventia.test', institucion: 'Universidad Nacional de Asunción', especialidad: '', biografia: '' },
    ],
    // Actividades de los eventos; "conferencistas" guarda los id_conferencista asociados.
    actividades: [
      { id_actividad: 1, id_evento: 1, titulo: 'Taller de Introducción al Testing', fecha: '2026-10-15', hora_inicio: '09:00', conferencistas: [1, 2] },
      { id_actividad: 2, id_evento: 1, titulo: 'Conferencia: Arquitecturas limpias', fecha: '2026-10-16', hora_inicio: '14:30', conferencistas: [2] },
      { id_actividad: 3, id_evento: 2, titulo: 'Construyendo APIs con FastAPI', fecha: '2026-11-05', hora_inicio: '08:30', conferencistas: [] },
      { id_actividad: 4, id_evento: 4, titulo: 'Optimización de consultas en PostgreSQL', fecha: '2026-12-02', hora_inicio: '10:00', conferencistas: [] },
    ],
    tipos: [
      { id_tipo_evento: 1, nombre: 'Congreso', activo: true },
      { id_tipo_evento: 2, nombre: 'Seminario', activo: true },
      { id_tipo_evento: 3, nombre: 'Taller', activo: true },
      { id_tipo_evento: 4, nombre: 'Jornada', activo: true },
      { id_tipo_evento: 5, nombre: 'Otro', activo: true },
    ],
    eventos: [
      {
        id_evento: 1, id_tipo_evento: 1, nombre: 'Congreso de Ingeniería de Software 2026',
        descripcion: 'Encuentro anual de profesionales, docentes y estudiantes del área de software.',
        fecha_inicio: '2026-10-15', fecha_fin: '2026-10-17', lugar: 'Aula Magna FP-UNA',
        cupo_maximo: 300, estado: 'publicado',
        politica: { fecha_limite: '2026-10-10', requiere_aprobacion: false, permite_lista_espera: true, min_asistencia_certificado: 75 },
      },
      {
        id_evento: 2, id_tipo_evento: 3, nombre: 'Taller de Angular y APIs REST',
        descripcion: 'Taller práctico para construir un frontend conectado a un backend FastAPI.',
        fecha_inicio: '2026-11-05', fecha_fin: '2026-11-05', lugar: 'Laboratorio 3',
        cupo_maximo: 30, estado: 'publicado',
        politica: { fecha_limite: '2026-11-01', requiere_aprobacion: true, permite_lista_espera: true, min_asistencia_certificado: 100 },
      },
      {
        id_evento: 3, id_tipo_evento: 2, nombre: 'Seminario de Calidad de Software',
        descripcion: '',
        fecha_inicio: '2026-11-20', fecha_fin: '2026-11-21', lugar: '',
        cupo_maximo: 80, estado: 'borrador',
        politica: { fecha_limite: '', requiere_aprobacion: false, permite_lista_espera: false, min_asistencia_certificado: 75 },
      },
      {
        id_evento: 4, id_tipo_evento: 4, nombre: 'Jornada de Bases de Datos',
        descripcion: 'Charlas sobre PostgreSQL, modelado y optimización de consultas.',
        fecha_inicio: '2026-12-02', fecha_fin: '2026-12-02', lugar: 'Auditorio Central',
        cupo_maximo: 120, estado: 'borrador',
        politica: { fecha_limite: '2026-11-28', requiere_aprobacion: false, permite_lista_espera: false, min_asistencia_certificado: 80 },
      },
    ],
  };

  function clonar(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  function leer() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) { /* sin almacenamiento: se usan los datos iniciales */ }
    return clonar(DATOS_INICIALES);
  }

  let datos = leer();

  function guardar() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(datos)); } catch (e) { /* ignorar */ }
  }

  function siguienteId(lista, campo) {
    return lista.reduce((max, item) => Math.max(max, item[campo] || 0), 0) + 1;
  }

  // Simula la latencia de una llamada HTTP.
  function demora(valor, ms) {
    return new Promise(resolve => setTimeout(() => resolve(clonar(valor)), ms ?? 400));
  }

  window.MockApi = {
    login(correo, contrasena) {
      const ok = datos.usuarios.includes(String(correo).trim().toLowerCase()) && String(contrasena).length >= 6;
      return new Promise((resolve, reject) => setTimeout(() => (ok ? resolve() : reject()), 700));
    },

    getRoles() { return demora(datos.roles, 250); },
    createRole(rol) {
      const nuevo = { ...rol, id: siguienteId(datos.roles, 'id'), enUso: false };
      datos.roles.push(nuevo);
      guardar();
      return demora(nuevo, 500);
    },
    deleteRole(id) {
      datos.roles = datos.roles.filter(r => r.id !== id);
      guardar();
      return demora(null, 250);
    },

    getExpositores() { return demora(datos.expositores, 300); },
    getActividades() { return demora(datos.actividades, 250); },
    createExpositor(expositor) {
      const email = String(expositor.email).trim().toLowerCase();
      if (datos.expositores.some(e => e.email.toLowerCase() === email)) {
        return new Promise((_, reject) => setTimeout(() => reject({ status: 409 }), 400));
      }
      const nuevo = { ...expositor, id_conferencista: siguienteId(datos.expositores, 'id_conferencista') };
      datos.expositores.push(nuevo);
      guardar();
      return demora(nuevo, 500);
    },
    asociarConferencista(idActividad, idConferencista) {
      const actividad = datos.actividades.find(a => a.id_actividad === idActividad);
      if (!actividad) return Promise.reject({ status: 404 });
      if (actividad.conferencistas.includes(idConferencista)) return Promise.reject({ status: 409 });
      actividad.conferencistas.push(idConferencista);
      guardar();
      return demora(null, 200);
    },
    deleteExpositor(id) {
      datos.expositores = datos.expositores.filter(e => e.id_conferencista !== id);
      datos.actividades.forEach(a => { a.conferencistas = a.conferencistas.filter(c => c !== id); });
      guardar();
      return demora(null, 300);
    },

    getTiposEvento() { return demora(datos.tipos, 150); },
    getEventos(filtros) {
      const q = (filtros?.q || '').toLowerCase();
      const lista = datos.eventos.filter(e =>
        (!q || e.nombre.toLowerCase().includes(q)) &&
        (!filtros?.estado || e.estado === filtros.estado) &&
        (!filtros?.id_tipo_evento || e.id_tipo_evento === filtros.id_tipo_evento));
      return demora(lista, 400);
    },
    getEvento(id) {
      const evento = datos.eventos.find(e => e.id_evento === id);
      return evento ? demora(evento, 300) : Promise.reject(new Error('No encontrado'));
    },
    createEvento(payload) {
      const nuevo = { ...payload, id_evento: siguienteId(datos.eventos, 'id_evento') };
      datos.eventos.push(nuevo);
      guardar();
      return demora(nuevo, 600);
    },
    updateEvento(id, payload) {
      datos.eventos = datos.eventos.map(e => (e.id_evento === id ? { ...payload, id_evento: id } : e));
      guardar();
      return demora(null, 600);
    },

    reiniciar() {
      datos = clonar(DATOS_INICIALES);
      guardar();
    },
  };

  // Utilidades compartidas por las pantallas.
  window.MockUtil = {
    escapar(texto) {
      return String(texto ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    },
    // Equivalente al pipe date:'dd/MM/yyyy' para fechas 'YYYY-MM-DD'.
    fecha(iso) {
      if (!iso) return '';
      const [a, m, d] = iso.split('-');
      return `${d}/${m}/${a}`;
    },
  };
})();
