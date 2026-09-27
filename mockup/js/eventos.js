// ============================================================
// eventos.js
// Réplica del comportamiento de frontend/src/app/pages/eventos/eventos.ts
// ============================================================

(function () {
  const { escapar, fecha } = MockUtil;
  const $ = id => document.getElementById(id);

  const busqueda = $('busqueda');
  const estado = $('estado');
  const tipo = $('tipo');

  let eventos = [];
  let tipos = [];
  let cargando = false;
  let error = null;
  let vista = 'grilla';

  function nombreTipo(id) {
    return tipos.find(t => t.id_tipo_evento === id)?.nombre ?? `Tipo #${id}`;
  }

  function linkEditar(e) {
    return `evento-form.html?id=${encodeURIComponent(e.id_evento)}`;
  }

  function badge(e) {
    return `<span class="badge${e.estado === 'publicado' ? ' published' : ''}">${escapar(e.estado)}</span>`;
  }

  function render() {
    $('contador').textContent = `${eventos.length} evento(s)`;
    document.querySelectorAll('.view-toggle button').forEach(b => {
      b.classList.toggle('active', b.dataset.vista === vista);
    });

    $('error').hidden = !error;
    $('error').textContent = error || '';
    $('cargando').hidden = !cargando;

    const hayEventos = !cargando && eventos.length > 0;
    $('grilla').hidden = !(hayEventos && vista === 'grilla');
    $('lista').hidden = !(hayEventos && vista === 'lista');
    $('vacio').hidden = cargando || eventos.length > 0;

    $('grilla').innerHTML = eventos.map(e => `
      <article class="event-card">
        <div class="card-top">
          ${badge(e)}
          <span class="type">${escapar(nombreTipo(e.id_tipo_evento))}</span>
        </div>
        <h3>${escapar(e.nombre)}</h3>
        <p class="description">${escapar(e.descripcion || 'Sin descripción.')}</p>
        <dl>
          <div><dt>Fecha</dt><dd>${fecha(e.fecha_inicio)} - ${fecha(e.fecha_fin)}</dd></div>
          <div><dt>Lugar</dt><dd>${escapar(e.lugar || 'No definido')}</dd></div>
          <div><dt>Cupo</dt><dd>${escapar(e.cupo_maximo)} personas</dd></div>
        </dl>
        <a href="${linkEditar(e)}" class="edit-link">Editar evento →</a>
      </article>`).join('');

    $('listaBody').innerHTML = eventos.map(e => `
      <tr>
        <td><strong>${escapar(e.nombre)}</strong></td>
        <td>${escapar(nombreTipo(e.id_tipo_evento))}</td>
        <td>${fecha(e.fecha_inicio)}</td>
        <td>${escapar(e.lugar || '-')}</td>
        <td>${escapar(e.cupo_maximo)}</td>
        <td>${badge(e)}</td>
        <td><a href="${linkEditar(e)}">Editar</a></td>
      </tr>`).join('');
  }

  function cargarTipos() {
    MockApi.getTiposEvento().then(data => {
      tipos = data.filter(t => t.activo);
      tipo.insertAdjacentHTML('beforeend',
        tipos.map(t => `<option value="${t.id_tipo_evento}">${escapar(t.nombre)}</option>`).join(''));
      render();
    });
  }

  function cargarEventos() {
    cargando = true;
    error = null;
    render();
    MockApi.getEventos({
      q: busqueda.value.trim() || undefined,
      estado: estado.value || undefined,
      id_tipo_evento: tipo.value ? Number(tipo.value) : undefined,
    }).then(data => {
      eventos = data;
      cargando = false;
      render();
    }).catch(() => {
      error = 'No se pudo cargar el catálogo de eventos.';
      cargando = false;
      render();
    });
  }

  busqueda.addEventListener('keyup', e => { if (e.key === 'Enter') cargarEventos(); });
  $('filtrarBtn').addEventListener('click', cargarEventos);
  $('limpiarBtn').addEventListener('click', () => {
    busqueda.value = '';
    estado.value = '';
    tipo.value = '';
    cargarEventos();
  });
  document.querySelectorAll('.view-toggle button').forEach(b => {
    b.addEventListener('click', () => { vista = b.dataset.vista; render(); });
  });

  cargarTipos();
  cargarEventos();
})();
