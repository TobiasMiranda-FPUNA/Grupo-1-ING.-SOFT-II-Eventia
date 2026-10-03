(function(){
  const form=document.getElementById('formExpositor');
  const lista=document.getElementById('lista');
  const vacio=document.getElementById('vacio');
  const buscar=document.getElementById('buscar');
  const mensaje=document.getElementById('mensaje');
  let expositores=[];
  const esc=window.MockUtil.escapar;
  function render(){
    const q=buscar.value.trim().toLowerCase();
    const visibles=expositores.filter(e=>`${e.nombres} ${e.apellidos} ${e.especialidad||''} ${e.institucion||''}`.toLowerCase().includes(q));
    lista.innerHTML=visibles.map(e=>`<article class="speaker-card"><div class="speaker-top"><div class="avatar">${esc((e.nombres||'?').charAt(0))}${esc((e.apellidos||'?').charAt(0))}</div><div><h3>${esc(e.nombres)} ${esc(e.apellidos)}</h3><p class="muted">${esc(e.email)}</p></div></div><p class="detail"><strong>Institución:</strong> ${esc(e.institucion||'No especificada')}<br><strong>Especialidad:</strong> ${esc(e.especialidad||'No especificada')}<br>${esc(e.biografia||'')}</p><div class="activities"><strong>Actividades asociadas</strong>${(e.actividades||[]).length?(e.actividades||[]).map(a=>`<span class="activity">${esc(a)}</span>`).join(''):'<span class="muted">Sin actividades asociadas</span>'}</div><button class="delete" type="button" data-id="${e.id}">Eliminar</button></article>`).join('');
    vacio.hidden=visibles.length!==0;
    lista.querySelectorAll('[data-id]').forEach(b=>b.addEventListener('click',async()=>{if(confirm('¿Eliminar este expositor del mockup?')){await MockApi.deleteExpositor(Number(b.dataset.id));await cargar();}}));
  }
  async function cargar(){expositores=await MockApi.getExpositores();render();}
  form.addEventListener('submit',async ev=>{ev.preventDefault();const data=Object.fromEntries(new FormData(form));try{await MockApi.createExpositor(data);form.reset();mensaje.textContent='Expositor registrado en los datos simulados.';mensaje.hidden=false;await cargar();}catch{mensaje.textContent='No se pudo registrar el expositor.';mensaje.classList.add('error');mensaje.hidden=false;}});
  buscar.addEventListener('input',render);
  cargar();
})();
