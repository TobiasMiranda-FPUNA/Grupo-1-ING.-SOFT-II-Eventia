// ============================================================
// roles.js
// Réplica del comportamiento de frontend/src/app/pages/roles/roles.ts
// ============================================================

(function () {
  const { escapar } = MockUtil;
  const form = document.getElementById('roleForm');
  const btn = document.getElementById('submitBtn');
  const tbody = document.getElementById('rolesBody');
  const errorBox = document.getElementById('errorMessage');
  const successBox = document.getElementById('successMessage');

  const campos = {
    nombre: {
      input: document.getElementById('nombre'),
      errores: document.getElementById('nombreErrors'),
      validar: v => (!v ? 'required' : v.length < 3 ? 'minlength' : null),
      tocado: false,
    },
    descripcion: {
      input: document.getElementById('descripcion'),
      errores: document.getElementById('descripcionErrors'),
      validar: v => (!v ? 'required' : null),
      tocado: false,
    },
  };

  let roles = [];
  let cargando = false;

  function formularioInvalido() {
    return Object.values(campos).some(c => c.validar(c.input.value));
  }

  function mostrarMensajes(error, exito) {
    errorBox.hidden = !error;
    errorBox.innerHTML = error ? `<strong>¡Acción Bloqueada!</strong> ${escapar(error)}` : '';
    successBox.hidden = !exito;
    successBox.textContent = exito || '';
  }

  function renderFormulario() {
    Object.values(campos).forEach(c => {
      const error = c.validar(c.input.value);
      const mostrar = c.tocado && !!error;
      c.input.classList.toggle('is-invalid', mostrar);
      c.errores.hidden = !mostrar;
      c.errores.querySelectorAll('small').forEach(s => { s.hidden = s.dataset.error !== error; });
    });
    btn.disabled = formularioInvalido() || cargando;
    btn.textContent = cargando ? 'Guardando...' : 'Guardar Rol';
  }

  function renderTabla() {
    if (!roles.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No hay roles registrados actualmente.</td></tr>';
      return;
    }
    tbody.innerHTML = roles.map(r => `
      <tr>
        <td>#${escapar(r.id)}</td>
        <td><strong>${escapar(r.nombre)}</strong></td>
        <td>${escapar(r.descripcion)}</td>
        <td>
          <span class="badge ${r.enUso ? 'badge-inuse' : 'badge-free'}">
            ${r.enUso ? 'En Uso (Inscripciones)' : 'Disponible'}
          </span>
        </td>
        <td><button class="btn-danger" data-id="${r.id}" title="Eliminar rol">Eliminar</button></td>
      </tr>`).join('');
  }

  function reiniciarFormulario() {
    form.reset();
    Object.values(campos).forEach(c => { c.tocado = false; });
  }

  Object.values(campos).forEach(c => {
    c.input.addEventListener('input', renderFormulario);
    c.input.addEventListener('blur', () => { c.tocado = true; renderFormulario(); });
  });

  form.addEventListener('submit', e => {
    e.preventDefault();
    if (formularioInvalido()) {
      Object.values(campos).forEach(c => { c.tocado = true; });
      renderFormulario();
      return;
    }

    cargando = true;
    mostrarMensajes(null, null);
    renderFormulario();

    MockApi.createRole({
      nombre: campos.nombre.input.value,
      descripcion: campos.descripcion.input.value,
      activo: true,
    }).then(creado => {
      cargando = false;
      roles.push(creado);
      mostrarMensajes(null, 'Rol creado exitosamente.');
      reiniciarFormulario();
      renderFormulario();
      renderTabla();
    });
  });

  // Criterio de aceptación: bloquear la eliminación si el rol está en uso.
  tbody.addEventListener('click', e => {
    const boton = e.target.closest('button[data-id]');
    if (!boton) return;
    const rol = roles.find(r => String(r.id) === boton.dataset.id);
    mostrarMensajes(null, null);

    if (rol.enUso) {
      mostrarMensajes(`No se puede eliminar el rol "${rol.nombre}" porque actualmente se encuentra asignado a inscripciones activas.`, null);
      return;
    }

    MockApi.deleteRole(rol.id).then(() => {
      roles = roles.filter(r => r.id !== rol.id);
      mostrarMensajes(null, 'Rol eliminado correctamente.');
      renderTabla();
    });
  });

  renderFormulario();
  renderTabla();
  MockApi.getRoles().then(data => { roles = data; renderTabla(); });
})();
