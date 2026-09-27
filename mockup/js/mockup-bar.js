// ============================================================
// mockup-bar.js
// Barra inferior del mockup para saltar entre pantallas y
// reiniciar los datos simulados. No forma parte del diseño real.
// ============================================================

(function () {
  const PANTALLAS = [
    { archivo: 'login.html', nombre: 'Login' },
    { archivo: 'roles.html', nombre: 'Roles' },
    { archivo: 'eventos.html', nombre: 'Eventos' },
    { archivo: 'evento-form.html', nombre: 'Nuevo evento' },
    { archivo: 'evento-form.html?id=1', nombre: 'Editar evento' },
  ];

  const actual = location.pathname.split('/').pop() + location.search;

  const barra = document.createElement('nav');
  barra.className = 'mk-bar';
  barra.innerHTML =
    '<a class="mk-brand" href="index.html">MOCKUP · Eventia</a>' +
    PANTALLAS.map(p => {
      return `<a href="${p.archivo}"${actual === p.archivo ? ' class="mk-active"' : ''}>${p.nombre}</a>`;
    }).join('') +
    '<button type="button" class="mk-reset" title="Vuelve a los datos de ejemplo">Reiniciar datos</button>';

  barra.querySelector('.mk-reset').addEventListener('click', () => {
    window.MockApi.reiniciar();
    location.reload();
  });

  document.body.appendChild(barra);
  document.body.classList.add('mk-with-bar');
})();
