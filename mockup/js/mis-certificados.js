// ============================================================
// mis-certificados.js
// Réplica del comportamiento de
// frontend/src/app/pages/mis-certificados/mis-certificados.ts
// En el mockup no hay PDF real: "Descargar PDF" solo simula la descarga.
// ============================================================

(function () {
  const { escapar, fecha } = MockUtil;
  const lista = document.getElementById('lista');
  const resumen = document.getElementById('resumen');
  const aviso = document.getElementById('aviso');

  function estado(c) {
    if (c.certificado_emitido) return 'emitido';
    if (c.estado_inscripcion !== 'confirmada') return 'no_aplica';
    if (c.elegible) return 'disponible';
    const hoy = new Date().toISOString().slice(0, 10);
    return c.fecha_fin_evento >= hoy ? 'en_curso' : 'no_alcanza';
  }

  const TEXTO = {
    emitido: 'Emitido',
    disponible: 'Pendiente de emisión',
    en_curso: 'Evento en curso',
    no_alcanza: 'No alcanzó el mínimo',
  };
  const DETALLE = {
    emitido: 'Ya podés descargarlo o compartir su código de verificación.',
    disponible: 'Cumpliste la asistencia mínima. El organizador emitirá tu certificado.',
    en_curso: 'Tu asistencia se sigue registrando en cada actividad.',
    no_alcanza: 'Tu asistencia quedó por debajo del mínimo exigido por el evento.',
    no_aplica: 'Solo las inscripciones confirmadas pueden recibir certificado.',
  };

  function textoEstado(c) {
    const e = estado(c);
    if (e !== 'no_aplica') return TEXTO[e];
    return c.estado_inscripcion === 'lista_de_espera' ? 'En lista de espera' : 'Sin certificado';
  }

  function tarjeta(c) {
    const e = estado(c);
    const pct = Math.round(c.porcentaje_asistencia);
    const fechas = fecha(c.fecha_inicio_evento) +
      (c.fecha_fin_evento !== c.fecha_inicio_evento ? ` – ${fecha(c.fecha_fin_evento)}` : '');
    const asistencia = c.estado_inscripcion !== 'confirmada' ? '' : `
      <div class="asistencia">
        <div class="barra" role="img" aria-label="Asistencia ${pct}% de un mínimo de ${c.minimo_requerido}%">
          <div class="relleno ${c.porcentaje_asistencia >= c.minimo_requerido ? 'ok' : ''}" style="width:${c.porcentaje_asistencia}%"></div>
          <div class="minimo" style="left:${c.minimo_requerido}%"></div>
        </div>
        <p class="cifras">Asistencia <strong>${pct}%</strong> (${c.asistencias_presentes} de ${c.actividades_evento} actividades) · Mínimo ${c.minimo_requerido}%</p>
      </div>`;
    const acciones = !(c.certificado_emitido && c.codigo_validacion) ? '' : `
      <div class="acciones">
        <p class="codigo">Código <code>${escapar(c.codigo_validacion)}</code></p>
        <div class="botones">
          <button type="button" class="btn-secondary" data-verificar="${escapar(c.codigo_validacion)}">Verificar</button>
          <button type="button" class="btn-primary" data-descargar="${c.id_inscripcion}">Descargar PDF</button>
        </div>
      </div>`;
    return `<article class="card cert ${e === 'emitido' ? 'emitido' : ''}">
      <div class="cert-head">
        <div><h2>${escapar(c.evento)}</h2><p class="fechas">${fechas}</p></div>
        <span class="estado" data-estado="${e}">${textoEstado(c)}</span>
      </div>
      ${asistencia}
      <p class="detalle">${DETALLE[e]}</p>
      ${acciones}
    </article>`;
  }

  lista.addEventListener('click', ev => {
    const descargar = ev.target.closest('[data-descargar]');
    const verificar = ev.target.closest('[data-verificar]');
    if (descargar) {
      descargar.disabled = true;
      descargar.textContent = 'Descargando…';
      setTimeout(() => {
        descargar.disabled = false;
        descargar.textContent = 'Descargar PDF';
        aviso.hidden = false;
        aviso.textContent = 'Mockup: en el sistema real se descarga el certificado en PDF.';
      }, 600);
    } else if (verificar) {
      aviso.hidden = false;
      aviso.textContent = `Mockup: en el sistema real se abre la verificación pública del código ${verificar.dataset.verificar}.`;
    }
  });

  MockApi.getMisCertificados().then(certificados => {
    if (certificados.length === 0) {
      lista.innerHTML = '<div class="card empty"><p>Todavía no tenés inscripciones.</p></div>';
      return;
    }
    const emitidos = certificados.filter(c => c.certificado_emitido).length;
    resumen.hidden = false;
    resumen.innerHTML = `<strong>${emitidos}</strong> de ${certificados.length} ` +
      (certificados.length === 1 ? 'inscripción tiene' : 'inscripciones tienen') + ' certificado emitido.';
    lista.innerHTML = certificados.map(tarjeta).join('');
  });
})();
