// ============================================================
// evento-form.js
// Réplica del comportamiento de
// frontend/src/app/pages/evento-form/evento-form.ts
// Modo edición: evento-form.html?id=<id_evento>
// ============================================================

(function () {
  const { escapar, fecha } = MockUtil;
  const $ = id => document.getElementById(id);
  const form = $('form');
  const campo = nombre => form.elements[nombre];

  const rawId = new URLSearchParams(location.search).get('id');
  const eventoId = rawId ? Number(rawId) : null;
  const esEdicion = eventoId !== null;

  let paso = 1;
  let tipos = [];
  let guardando = false;
  let cargando = false;
  let error = null;

  // Validadores equivalentes a los del FormGroup de Angular.
  const VALIDADORES = {
    id_tipo_evento: v => !!v,
    nombre: v => !!v && v.length <= 150,
    descripcion: v => v.length <= 500,
    fecha_inicio: v => !!v,
    fecha_fin: v => !!v,
    cupo_maximo: v => v !== '' && Number(v) >= 1,
    estado: v => !!v,
    min_asistencia_certificado: v => v !== '' && Number(v) >= 0 && Number(v) <= 100,
  };

  function valores() {
    return {
      id_tipo_evento: campo('id_tipo_evento').value,
      nombre: campo('nombre').value,
      descripcion: campo('descripcion').value,
      fecha_inicio: campo('fecha_inicio').value,
      fecha_fin: campo('fecha_fin').value,
      lugar: campo('lugar').value,
      cupo_maximo: campo('cupo_maximo').value,
      estado: campo('estado').value,
      fecha_limite: campo('fecha_limite').value,
      requiere_aprobacion: campo('requiere_aprobacion').checked,
      permite_lista_espera: campo('permite_lista_espera').checked,
      min_asistencia_certificado: campo('min_asistencia_certificado').value,
    };
  }

  function invalido(nombres) {
    const v = valores();
    return nombres.some(n => !VALIDADORES[n](v[n]));
  }

  function nombreTipoSeleccionado() {
    const id = Number(campo('id_tipo_evento').value);
    return tipos.find(t => t.id_tipo_evento === id)?.nombre ?? '-';
  }

  function renderResumen() {
    const v = valores();
    const filas = [
      ['Nombre', v.nombre],
      ['Tipo', nombreTipoSeleccionado()],
      ['Fechas', `${fecha(v.fecha_inicio)} - ${fecha(v.fecha_fin)}`],
      ['Lugar', v.lugar || 'No definido'],
      ['Cupo', `${v.cupo_maximo} personas`],
      ['Estado', v.estado],
      ['Requiere aprobación', v.requiere_aprobacion ? 'Sí' : 'No'],
      ['Lista de espera', v.permite_lista_espera ? 'Sí' : 'No'],
    ];
    $('resumen').innerHTML = filas
      .map(([k, val]) => `<div><span>${escapar(k)}</span><strong>${escapar(val)}</strong></div>`)
      .join('');
  }

  function render() {
    $('titulo').textContent = esEdicion ? 'Editar evento' : 'Crear nuevo evento';
    document.querySelectorAll('.steps div').forEach(d => {
      d.classList.toggle('active', paso >= Number(d.dataset.paso));
    });
    $('error').hidden = !error;
    $('error').textContent = error || '';
    $('cargando').hidden = !cargando;
    form.hidden = cargando;

    form.querySelectorAll('section[data-seccion]').forEach(s => {
      s.hidden = Number(s.dataset.seccion) !== paso;
    });
    if (paso === 3) renderResumen();

    $('anteriorBtn').hidden = paso <= 1;
    $('siguienteBtn').hidden = paso >= 3;
    $('guardarBtn').hidden = paso !== 3;
    $('guardarBtn').disabled = guardando;
    $('guardarBtn').textContent = guardando ? 'Guardando...' : (esEdicion ? 'Guardar cambios' : 'Crear evento');
  }

  function cargarTipos() {
    return MockApi.getTiposEvento().then(data => {
      tipos = data.filter(t => t.activo);
      campo('id_tipo_evento').insertAdjacentHTML('beforeend',
        tipos.map(t => `<option value="${t.id_tipo_evento}">${escapar(t.nombre)}</option>`).join(''));
    }).catch(() => { error = 'No se pudieron cargar los tipos de evento.'; render(); });
  }

  function cargarEvento(id) {
    cargando = true;
    render();
    MockApi.getEvento(id).then(e => {
      const p = e.politica || {};
      campo('id_tipo_evento').value = String(e.id_tipo_evento);
      campo('nombre').value = e.nombre;
      campo('descripcion').value = e.descripcion ?? '';
      campo('fecha_inicio').value = e.fecha_inicio;
      campo('fecha_fin').value = e.fecha_fin;
      campo('lugar').value = e.lugar ?? '';
      campo('cupo_maximo').value = e.cupo_maximo;
      campo('estado').value = e.estado;
      campo('fecha_limite').value = p.fecha_limite ?? '';
      campo('requiere_aprobacion').checked = p.requiere_aprobacion ?? false;
      campo('permite_lista_espera').checked = p.permite_lista_espera ?? false;
      campo('min_asistencia_certificado').value = p.min_asistencia_certificado ?? 75;
      cargando = false;
      render();
    }).catch(() => {
      error = 'No se pudo cargar el evento.';
      cargando = false;
      render();
    });
  }

  $('siguienteBtn').addEventListener('click', () => {
    error = null;
    if (paso === 1) {
      if (invalido(['id_tipo_evento', 'nombre', 'fecha_inicio', 'fecha_fin', 'cupo_maximo'])) { render(); return; }
      const v = valores();
      if (v.fecha_fin < v.fecha_inicio) {
        error = 'La fecha de fin no puede ser anterior a la fecha de inicio.';
        render();
        return;
      }
    }
    if (paso < 3) paso++;
    render();
  });

  $('anteriorBtn').addEventListener('click', () => {
    if (paso > 1) paso--;
    render();
  });

  form.addEventListener('submit', e => {
    e.preventDefault();
    // En Angular el botón de envío solo existe en el paso 3.
    if (paso !== 3 || guardando) return;
    if (invalido(Object.keys(VALIDADORES))) {
      error = 'Revisá los campos obligatorios.';
      render();
      return;
    }
    const v = valores();
    if (v.fecha_fin < v.fecha_inicio) {
      error = 'La fecha de fin no puede ser anterior a la fecha de inicio.';
      paso = 1;
      render();
      return;
    }

    const payload = {
      id_tipo_evento: Number(v.id_tipo_evento), nombre: v.nombre.trim(), descripcion: v.descripcion.trim() || null,
      fecha_inicio: v.fecha_inicio, fecha_fin: v.fecha_fin, lugar: v.lugar.trim() || null,
      cupo_maximo: Number(v.cupo_maximo), estado: v.estado,
      politica: {
        fecha_limite: v.fecha_limite || null,
        requiere_aprobacion: v.requiere_aprobacion,
        permite_lista_espera: v.permite_lista_espera,
        min_asistencia_certificado: Number(v.min_asistencia_certificado),
      },
    };

    guardando = true;
    error = null;
    render();
    const request = esEdicion ? MockApi.updateEvento(eventoId, payload) : MockApi.createEvento(payload);
    request
      .then(() => { location.href = 'eventos.html'; })
      .catch(() => { guardando = false; error = 'No se pudo guardar el evento.'; render(); });
  });

  render();
  cargarTipos().then(() => { if (esEdicion) cargarEvento(eventoId); });
})();
