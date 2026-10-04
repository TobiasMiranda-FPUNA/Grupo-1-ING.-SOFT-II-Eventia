// ============================================================
// expositores.js
// Réplica del comportamiento de
// frontend/src/app/pages/expositores/expositores.ts
// ============================================================

(function () {
  const { escapar } = MockUtil;
  const form = document.getElementById('expositoresForm');
  const btn = document.getElementById('submitBtn');
  const selectActividades = document.getElementById('actividades');
  const inputBusqueda = document.getElementById('busqueda');
  const listCount = document.getElementById('listCount');
  const lista = document.getElementById('lista');
  const errorBox = document.getElementById('errorMessage');
  const successBox = document.getElementById('successMessage');

  // Mismos validadores que el FormGroup del componente.
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const campos = {
    nombres: { validar: v => v.trim().length >= 2 },
    apellidos: { validar: v => v.trim().length >= 2 },
    email: { validar: v => EMAIL_RE.test(v.trim()) },
  };
  Object.entries(campos).forEach(([id, c]) => {
    c.input = document.getElementById(id);
    c.error = form.querySelector(`[data-error-for="${id}"]`);
    c.tocado = false;
  });

  let expositores = [];
  let actividades = [];
  let busqueda = '';
  let cargando = false;

  // --- Mensajes ---
  function setMensaje(box, texto) {
    box.hidden = !texto;
    box.querySelector('span').textContent = texto || '';
  }
  const setError = t => setMensaje(errorBox, t);
  const setExito = t => setMensaje(successBox, t);
  errorBox.querySelector('button').addEventListener('click', () => setError(null));
  successBox.querySelector('button').addEventListener('click', () => setExito(null));

  // --- Utilidades de la vista ---
  function iniciales(e) {
    const ini = `${(e.nombres || '').trim().charAt(0)}${(e.apellidos || '').trim().charAt(0)}`;
    return ini.toLocaleUpperCase() || 'EX';
  }

  // Igual que Intl.DateTimeFormat('es-PY') con día/mes/año de 2-2-4 dígitos.
  function fechaActividad(fecha) {
    if (!fecha) return 'Fecha no disponible';
    const [anio, mes, dia] = fecha.slice(0, 10).split('-').map(Number);
    if (!anio || !mes || !dia) return fecha;
    return new Intl.DateTimeFormat('es-PY', { day: '2-digit', month: '2-digit', year: 'numeric' })
      .format(new Date(anio, mes - 1, dia));
  }

  function filtrados() {
    const termino = busqueda.trim().toLocaleLowerCase();
    if (!termino) return expositores;
    return expositores.filter(e =>
      `${e.nombres} ${e.apellidos}`.toLocaleLowerCase().includes(termino) ||
      (e.especialidad || '').toLocaleLowerCase().includes(termino));
  }

  // --- Render ---
  function renderFormulario() {
    Object.values(campos).forEach(c => {
      const mostrar = c.tocado && !c.validar(c.input.value);
      c.error.hidden = !mostrar;
    });
    btn.disabled = cargando;
    btn.textContent = cargando ? 'Registrando…' : '+ Registrar expositor';
  }

  function renderActividades() {
    selectActividades.innerHTML = actividades
      .map(a => `<option value="${a.id_actividad}">${escapar(a.titulo)}</option>`)
      .join('');
    selectActividades.disabled = actividades.length === 0;
  }

  function renderTarjeta(e) {
    const acts = e.actividades.length
      ? `<div class="activity-list">${e.actividades.map(a => `
          <div class="activity-item">
            <span class="activity-tag">${escapar(a.titulo)}</span>
            <p class="activity-date"><strong>Fecha de inicio:</strong> ${escapar(fechaActividad(a.fecha))}</p>
            <p class="activity-time"><strong>Hora de inicio:</strong> ${escapar(a.hora_inicio)}</p>
          </div>`).join('')}
        </div>`
      : '<span class="no-activities">Sin actividades asignadas</span>';

    return `
      <article class="expositor-card">
        <div class="card-person">
          <div class="avatar" aria-hidden="true">${escapar(iniciales(e))}</div>
          <div class="person-data">
            <h3>${escapar(e.nombres)} ${escapar(e.apellidos)}</h3>
            <a href="mailto:${escapar(e.email)}">${escapar(e.email)}</a>
          </div>
        </div>

        <div class="person-details">
          ${e.institucion ? `<p><strong>Institución:</strong> ${escapar(e.institucion)}</p>` : ''}
          <p class="detail-line"><strong>Especialidad:</strong> ${escapar((e.especialidad || '').trim() || 'No especificada')}</p>
          ${e.biografia ? `<p class="biography">${escapar(e.biografia)}</p>` : ''}
        </div>

        <div class="activities">
          <h4>Actividades asociadas</h4>
          ${acts}
        </div>

        <div class="card-actions">
          <button type="button" class="delete-button" data-id="${e.id_conferencista}"${cargando ? ' disabled' : ''}>× Eliminar</button>
        </div>
      </article>`;
  }

  function renderLista() {
    const visibles = filtrados();
    listCount.textContent = `${visibles.length} de ${expositores.length} expositores`;

    if (cargando && expositores.length === 0) {
      lista.innerHTML = '<div class="empty-state">Cargando expositores…</div>';
    } else if (visibles.length === 0) {
      lista.innerHTML = `
        <div class="empty-state">
          <strong>${busqueda ? 'No se encontraron coincidencias' : 'Todavía no hay expositores registrados'}</strong>
          <span>${busqueda ? 'Probá con otro nombre o especialidad.' : 'Completá el formulario para registrar el primero.'}</span>
        </div>`;
    } else {
      lista.innerHTML = `<div class="expositores-grid">${visibles.map(renderTarjeta).join('')}</div>`;
    }
  }

  function render() {
    renderFormulario();
    renderLista();
  }

  // --- Carga ---
  // El componente arma la relación recorriendo las actividades de cada evento
  // y buscando el conferencista en su lista de conferencistas.
  async function cargar() {
    cargando = true;
    render();
    const [confs, acts] = await Promise.all([MockApi.getExpositores(), MockApi.getActividades()]);
    actividades = acts;
    expositores = confs.map(e => ({
      ...e,
      actividades: acts.filter(a => a.conferencistas.includes(e.id_conferencista)),
    }));
    cargando = false;
    renderActividades();
    render();
  }

  function mensajeHttp(error, porDefecto) {
    switch (error?.status) {
      case 400: return 'Los datos enviados no son válidos. Revisá la información ingresada.';
      case 401: return 'Tu sesión expiró. Iniciá sesión nuevamente.';
      case 403: return 'No tenés permisos para realizar esta operación.';
      case 404: return 'No se encontró el recurso solicitado.';
      case 409: return 'Ya existe un expositor registrado con ese correo electrónico o la asociación ya existe.';
      case 422: return 'Los datos ingresados no cumplen con las validaciones requeridas.';
      default: return porDefecto;
    }
  }

  function reiniciarFormulario() {
    form.reset();
    Object.values(campos).forEach(c => { c.tocado = false; });
  }

  // --- Eventos ---
  Object.values(campos).forEach(c => {
    c.input.addEventListener('input', renderFormulario);
    c.input.addEventListener('blur', () => { c.tocado = true; renderFormulario(); });
  });

  inputBusqueda.addEventListener('input', () => {
    busqueda = inputBusqueda.value;
    renderLista();
  });

  form.addEventListener('submit', async ev => {
    ev.preventDefault();

    if (Object.values(campos).some(c => !c.validar(c.input.value))) {
      Object.values(campos).forEach(c => { c.tocado = true; });
      setError('Revisá los campos obligatorios antes de continuar.');
      renderFormulario();
      return;
    }

    cargando = true;
    setError(null);
    setExito(null);
    render();

    const valor = id => document.getElementById(id).value.trim();
    const nuevo = {
      nombres: valor('nombres'),
      apellidos: valor('apellidos'),
      email: valor('email'),
      institucion: valor('institucion') || undefined,
      especialidad: valor('especialidad') || undefined,
      biografia: valor('biografia') || undefined,
    };
    const seleccionadas = [...new Set(
      Array.from(selectActividades.selectedOptions)
        .map(o => Number(o.value))
        .filter(id => Number.isInteger(id) && id > 0))];

    let creado;
    try {
      creado = await MockApi.createExpositor(nuevo);
    } catch (error) {
      cargando = false;
      setError(mensajeHttp(error, 'No fue posible registrar el expositor.'));
      render();
      return;
    }

    // Las asociaciones se procesan en orden, una por una.
    try {
      for (const idActividad of seleccionadas) {
        await MockApi.asociarConferencista(idActividad, creado.id_conferencista);
      }
      setExito(seleccionadas.length
        ? 'Expositor registrado y asociado correctamente a las actividades seleccionadas.'
        : 'Expositor registrado correctamente.');
    } catch (error) {
      setError(mensajeHttp(error, 'El expositor fue creado, pero no se pudieron asignar todas las actividades.'));
    }

    reiniciarFormulario();
    await cargar();
  });

  lista.addEventListener('click', async ev => {
    const boton = ev.target.closest('button[data-id]');
    if (!boton) return;
    const expositor = expositores.find(e => String(e.id_conferencista) === boton.dataset.id);
    const nombre = `${expositor.nombres} ${expositor.apellidos}`.trim();

    if (!window.confirm(`¿Estás seguro de eliminar a ${nombre}?`)) return;

    setError(null);
    setExito(null);
    await MockApi.deleteExpositor(expositor.id_conferencista);
    setExito('Expositor eliminado correctamente.');
    await cargar();
  });

  cargar();
})();
