// ============================================================
// mock-data.js
// Proyecto: Eventia - Mockup interactivo
//
// Reemplaza al backend: guarda roles, tipos de evento y eventos
// en localStorage para que los cambios hechos en una pantalla se
// vean en las demás. Los datos iniciales replican los catálogos
// de sql/cargar_catalogos_iniciales.sql y los datos de respaldo
// del frontend (roles.ts).
// ============================================================

(function () {
  const STORAGE_KEY = 'eventia-mockup-v1';

  const DATOS_INICIALES = {
    usuarios: ['admin@eventia.test', 'organizador@eventia.test'],
    roles: [
      { id: 1, nombre: 'Estudiante', descripcion: 'Participante matriculado en institución', activo: true, enUso: true },
      { id: 2, nombre: 'Expositor', descripcion: 'Conferencista o ponente de actividad', activo: true, enUso: false },
      { id: 3, nombre: 'General', descripcion: 'Público general asistente', activo: true, enUso: false },
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
