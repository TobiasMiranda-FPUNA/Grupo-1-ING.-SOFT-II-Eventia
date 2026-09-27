// ============================================================
// login.js
// Réplica del comportamiento de frontend/src/app/pages/login/login.ts
// ============================================================

(function () {
  const form = document.getElementById('loginForm');
  const btn = document.getElementById('submitBtn');
  const alerta = document.getElementById('invalidAlert');
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  // Validadores equivalentes a los del FormGroup de Angular.
  const campos = {
    email: {
      input: document.getElementById('email'),
      errores: document.getElementById('emailErrors'),
      validar: v => (!v ? 'required' : !EMAIL_RE.test(v) ? 'email' : null),
      tocado: false,
    },
    password: {
      input: document.getElementById('password'),
      errores: document.getElementById('passwordErrors'),
      validar: v => (!v ? 'required' : v.length < 6 ? 'minlength' : null),
      tocado: false,
    },
  };

  let cargando = false;

  function formularioInvalido() {
    return Object.values(campos).some(c => c.validar(c.input.value));
  }

  function render() {
    Object.values(campos).forEach(c => {
      const error = c.validar(c.input.value);
      const mostrar = c.tocado && !!error;
      c.input.classList.toggle('is-invalid', mostrar);
      c.errores.hidden = !mostrar;
      c.errores.querySelectorAll('small').forEach(s => { s.hidden = s.dataset.error !== error; });
    });
    btn.disabled = formularioInvalido() || cargando;
    btn.textContent = cargando ? 'Cargando...' : 'Ingresar';
  }

  Object.values(campos).forEach(c => {
    c.input.addEventListener('input', render);
    c.input.addEventListener('blur', () => { c.tocado = true; render(); });
  });

  form.addEventListener('submit', e => {
    e.preventDefault();
    if (formularioInvalido()) {
      Object.values(campos).forEach(c => { c.tocado = true; });
      render();
      return;
    }

    cargando = true;
    render();

    MockApi.login(campos.email.input.value, campos.password.input.value)
      .then(() => { location.href = 'roles.html'; })
      .catch(() => {
        cargando = false;
        render();
        alerta.hidden = false;
      });
  });

  document.getElementById('closeAlertBtn').addEventListener('click', () => {
    alerta.hidden = true;
    form.reset();
    Object.values(campos).forEach(c => { c.tocado = false; });
    render();
  });

  render();
})();
