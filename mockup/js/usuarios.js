// ============================================================
// usuarios.js
// Réplica del comportamiento de frontend/src/app/pages/usuarios/usuarios.ts
// En el mockup, el administrador en sesión es Ana Duarte (id 1).
// ============================================================

(function () {
  const { escapar } = MockUtil;
  const form = document.getElementById('usuarioForm');
  const btn = document.getElementById('submitBtn');
  const tbody = document.getElementById('usuariosBody');
  const count = document.getElementById('count');
  const busqueda = document.getElementById('busqueda');
  const rolSelect = document.getElementById('rol');
  const errorBox = document.getElementById('errorMessage');
  const successBox = document.getElementById('successMessage');

  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const campos = {
    nombres: { input: document.getElementById('nombres'), validar: v => !!v.trim() && v.length <= 100 },
    apellidos: { input: document.getElementById('apellidos'), validar: v => !!v.trim() && v.length <= 100 },
    email: { input: document.getElementById('email'), validar: v => EMAIL_RE.test(v.trim()) },
    // Cédula: sin puntos ni espacios, 3 a 20 dígitos, letras o guiones.
    documento: { input: document.getElementById('documento'), validar: v => /^[A-Z0-9-]{3,20}$/.test(v.replace(/[\s.]/g, '').toUpperCase()) },
    password: { input: document.getElementById('password'), validar: v => v.length >= 8 && v.length <= 128 },
    rol: { input: rolSelect, validar: v => Number(v) > 0 },
  };

  let usuarios = [];
  let cargando = true;
  let eliminandoId = null;

  function mensaje(caja, texto) {
    caja.hidden = !texto;
    caja.innerHTML = texto
      ? `<span>${escapar(texto)}</span><button type="button" class="close" aria-label="Cerrar">×</button>`
      : '';
    if (texto) caja.querySelector('.close').addEventListener('click', () => mensaje(caja, null));
  }
  function limpiarMensajes() { mensaje(errorBox, null); mensaje(successBox, null); }

  function mostrarErrorCampo(nombre, visible) {
    const c = campos[nombre];
    c.input.classList.toggle('is-invalid', visible);
    form.querySelector(`.field-error[data-campo="${nombre}"]`).hidden = !visible;
    const hint = form.querySelector(`.hint[data-hint="${nombre}"]`);
    if (hint) hint.hidden = visible;
  }

  Object.entries(campos).forEach(([nombre, c]) => {
    const evento = c.input.tagName === 'SELECT' ? 'change' : 'blur';
    c.input.addEventListener(evento, () => mostrarErrorCampo(nombre, !c.validar(c.input.value)));
  });

  function render() {
    count.textContent = usuarios.length;
    if (cargando) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Cargando usuarios…</td></tr>';
      return;
    }
    const q = busqueda.value.trim().toLowerCase();
    const filtrados = usuarios.filter(u =>
      !q || `${u.nombres} ${u.apellidos} ${u.email} ${u.documento || ''} ${u.roles.join(' ')}`.toLowerCase().includes(q));

    if (filtrados.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="empty-state">${q ? 'Ningún usuario coincide con la búsqueda.' : 'No hay usuarios registrados.'}</td></tr>`;
      return;
    }
    tbody.innerHTML = filtrados.map(u => {
      const soyYo = u.id_usuario === MockApi.idUsuarioActual;
      const accion = soyYo
        ? '<span class="hint">—</span>'
        : `<button type="button" class="btn-danger" data-id="${u.id_usuario}" ${eliminandoId === u.id_usuario ? 'disabled' : ''}
             aria-label="Eliminar usuario ${escapar(u.email)}">${eliminandoId === u.id_usuario ? 'Eliminando…' : 'Eliminar'}</button>`;
      return `<tr>
        <td><strong>${escapar(u.nombres)} ${escapar(u.apellidos)}</strong>${soyYo ? '<span class="you">(vos)</span>' : ''}</td>
        <td>${escapar(u.email)}</td>
        <td>${escapar(u.documento || '—')}</td>
        <td>${escapar(u.roles.join(', ') || 'Sin rol')}</td>
        <td><span class="badge ${u.activo ? 'badge-ok' : 'badge-off'}">${u.activo ? 'Activo' : 'Inactivo'}</span></td>
        <td class="actions">${accion}</td>
      </tr>`;
    }).join('');
  }

  function cargarUsuarios() {
    cargando = true;
    render();
    MockApi.getUsuarios().then(lista => {
      usuarios = lista;
      cargando = false;
      render();
    });
  }

  tbody.addEventListener('click', e => {
    const boton = e.target.closest('button[data-id]');
    if (!boton) return;
    const usuario = usuarios.find(u => u.id_usuario === Number(boton.dataset.id));
    if (!usuario) return;
    const ok = window.confirm(
      `¿Eliminar la cuenta de ${usuario.nombres} ${usuario.apellidos} (${usuario.email})? Esta acción no se puede deshacer.`);
    if (!ok) return;

    limpiarMensajes();
    eliminandoId = usuario.id_usuario;
    render();
    MockApi.deleteUsuario(usuario.id_usuario)
      .then(() => {
        usuarios = usuarios.filter(u => u.id_usuario !== usuario.id_usuario);
        mensaje(successBox, `Usuario ${usuario.email} eliminado.`);
      })
      .catch(err => mensaje(errorBox, err?.detail || 'No se pudo eliminar el usuario.'))
      .finally(() => { eliminandoId = null; render(); });
  });

  busqueda.addEventListener('input', render);

  form.addEventListener('submit', e => {
    e.preventDefault();
    const invalidos = Object.entries(campos).filter(([, c]) => !c.validar(c.input.value));
    Object.keys(campos).forEach(n => mostrarErrorCampo(n, invalidos.some(([m]) => m === n)));
    if (invalidos.length) return;

    limpiarMensajes();
    btn.disabled = true;
    btn.textContent = 'Creando…';
    MockApi.createUsuario({
      nombres: campos.nombres.input.value,
      apellidos: campos.apellidos.input.value,
      email: campos.email.input.value,
      documento: campos.documento.input.value,
      password: campos.password.input.value,
      id_rol_sistema: Number(rolSelect.value),
    })
      .then(u => {
        mensaje(successBox, `Usuario ${u.email} creado con rol ${u.roles.join(', ')}.`);
        form.reset();
        rolSelect.value = '0';
        cargarUsuarios();
      })
      .catch(err => mensaje(errorBox, err?.detail || 'No se pudo crear el usuario.'))
      .finally(() => { btn.disabled = false; btn.textContent = 'Crear usuario'; });
  });

  MockApi.getRolesSistema().then(roles => {
    rolSelect.insertAdjacentHTML('beforeend', roles.filter(r => r.activo)
      .map(r => `<option value="${r.id}">${escapar(r.nombre)}</option>`).join(''));
  });
  cargarUsuarios();
})();
