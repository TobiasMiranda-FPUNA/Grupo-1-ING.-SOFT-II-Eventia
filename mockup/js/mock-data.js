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
    // Gestión de usuarios (/usuarios). El id 1 es el administrador "en sesión".
    rolesSistema: [
      { id: 1, nombre: 'administrador', activo: true },
      { id: 2, nombre: 'organizador', activo: true },
      { id: 3, nombre: 'participante', activo: true },
      { id: 4, nombre: 'conferencista', activo: true },
      { id: 5, nombre: 'personal de acreditación', activo: true },
    ],
    cuentas: [
      { id_usuario: 1, nombres: 'Ana', apellidos: 'Duarte', email: 'admin@eventia.test', activo: true, roles: ['administrador'] },
      { id_usuario: 2, nombres: 'Carlos', apellidos: 'Benítez', email: 'organizador@eventia.test', activo: true, roles: ['organizador'] },
      { id_usuario: 3, nombres: 'Lucía', apellidos: 'Giménez', email: 'participante@eventia.test', activo: true, roles: ['participante'] },
      { id_usuario: 4, nombres: 'Pedro', apellidos: 'Ayala', email: 'acreditacion@eventia.test', activo: true, roles: ['personal de acreditación'] },
    ],
    // Mis certificados (/mis-certificados) de la participante Lucía Giménez.
    misCertificados: [
      { id_inscripcion: 11, evento: 'Congreso Nacional de Tecnología 2026', fecha_inicio_evento: '2026-11-10', fecha_fin_evento: '2026-11-12',
        estado_inscripcion: 'confirmada', actividades_evento: 4, asistencias_presentes: 4, porcentaje_asistencia: 100, minimo_requerido: 75,
        elegible: true, certificado_emitido: true, codigo_validacion: '9F2C41A7D03B4E8C9A51F6E2B7C80D13' },
      { id_inscripcion: 12, evento: 'Taller de Testing Ágil', fecha_inicio_evento: '2026-10-05', fecha_fin_evento: '2026-10-05',
        estado_inscripcion: 'confirmada', actividades_evento: 2, asistencias_presentes: 2, porcentaje_asistencia: 100, minimo_requerido: 100,
        elegible: true, certificado_emitido: false, codigo_validacion: null },
      { id_inscripcion: 13, evento: 'Seminario de Ciberseguridad para Desarrolladores', fecha_inicio_evento: '2026-12-18', fecha_fin_evento: '2026-12-18',
        estado_inscripcion: 'confirmada', actividades_evento: 4, asistencias_presentes: 1, porcentaje_asistencia: 25, minimo_requerido: 80,
        elegible: false, certificado_emitido: false, codigo_validacion: null },
      { id_inscripcion: 14, evento: 'Seminario de Arquitectura de Software', fecha_inicio_evento: '2026-09-25', fecha_fin_evento: '2026-09-25',
        estado_inscripcion: 'confirmada', actividades_evento: 2, asistencias_presentes: 0, porcentaje_asistencia: 0, minimo_requerido: 60,
        elegible: false, certificado_emitido: false, codigo_validacion: null },
      { id_inscripcion: 15, evento: 'Taller de Git y GitHub en Equipo', fecha_inicio_evento: '2026-12-20', fecha_fin_evento: '2026-12-20',
        estado_inscripcion: 'lista_de_espera', actividades_evento: 0, asistencias_presentes: 0, porcentaje_asistencia: 0, minimo_requerido: 100,
        elegible: false, certificado_emitido: false, codigo_validacion: null },
    ],
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
      // Completa con los datos iniciales las claves que no existían en
      // versiones anteriores del mockup (ej: cuentas, misCertificados).
      if (raw) return { ...clonar(DATOS_INICIALES), ...JSON.parse(raw) };
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

    // ---------- Gestión de usuarios (solo administrador) ----------
    idUsuarioActual: 1,
    getUsuarios() {
      const lista = [...datos.cuentas].sort((a, b) =>
        `${a.apellidos} ${a.nombres}`.localeCompare(`${b.apellidos} ${b.nombres}`));
      return demora(lista, 300);
    },
    getRolesSistema() { return demora(datos.rolesSistema, 200); },
    createUsuario(payload) {
      const email = String(payload.email).trim().toLowerCase();
      if (datos.cuentas.some(c => c.email.toLowerCase() === email)) {
        return new Promise((_, reject) => setTimeout(() => reject({ status: 409, detail: 'Ya existe un usuario con ese correo' }), 400));
      }
      const rol = datos.rolesSistema.find(r => r.id === Number(payload.id_rol_sistema) && r.activo);
      if (!rol) return Promise.reject({ status: 400, detail: 'El rol seleccionado no existe o está inactivo' });
      const nuevo = {
        id_usuario: siguienteId(datos.cuentas, 'id_usuario'),
        nombres: payload.nombres.trim(), apellidos: payload.apellidos.trim(),
        email, activo: true, roles: [rol.nombre],
      };
      datos.cuentas.push(nuevo);
      // La cuenta nueva también puede usarse en el login del mockup.
      if (!datos.usuarios.includes(email)) datos.usuarios.push(email);
      guardar();
      return demora(nuevo, 500);
    },
    deleteUsuario(id) {
      if (id === this.idUsuarioActual) {
        return Promise.reject({ status: 409, detail: 'No podés eliminar tu propio usuario' });
      }
      const cuenta = datos.cuentas.find(c => c.id_usuario === id);
      datos.cuentas = datos.cuentas.filter(c => c.id_usuario !== id);
      if (cuenta) datos.usuarios = datos.usuarios.filter(u => u !== cuenta.email);
      guardar();
      return demora(null, 300);
    },

    // ---------- Mis certificados (participante) ----------
    getMisCertificados() { return demora(datos.misCertificados, 350); },

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
