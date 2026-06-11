document.addEventListener('DOMContentLoaded', async () => {
  const user = await requireSession();
  if (!user) return;
  setUserChip(user);

  await cargarPerfil();
  await cargarCarreras();

  document.getElementById('sel-carrera').addEventListener('change', onCarreraChange);
  document.getElementById('sel-semestre').addEventListener('change', onSemestreChange);
  document.getElementById('btn-guardar-perfil').addEventListener('click', guardarPerfil);
  document.getElementById('btn-sync').addEventListener('click', sincronizarMaterias);
});

async function cargarPerfil() {
  try {
    const res = await api.get('/perfil');
    if (res.perfil) mostrarPerfilActual(res.perfil);
  } catch (_) {}
}

function mostrarPerfilActual(p) {
  document.getElementById('perfil-actual').innerHTML = `
    <div class="alert alert-info" style="margin-bottom:1rem">
      <strong>Perfil actual:</strong>
      ${escHtml(p.carrera)} — Semestre ${escHtml(String(p.semestre))}
    </div>`;
}

async function cargarCarreras() {
  try {
    const carreras = await api.get('/perfil/carreras');
    const sel = document.getElementById('sel-carrera');
    if (!carreras.length) {
      sel.innerHTML = '<option value="">— Sin datos —</option>';
      return;
    }
    sel.innerHTML = '<option value="">Selecciona una carrera…</option>' +
      carreras.map(c => `<option value="${escHtml(c)}">${escHtml(c)}</option>`).join('');
  } catch (err) {
    showAlert('#alert-box', 'No se pudo cargar carreras: ' + err.message, 'error');
  }
}

async function onCarreraChange() {
  const carrera = document.getElementById('sel-carrera').value;
  const selSem  = document.getElementById('sel-semestre');
  selSem.innerHTML = '<option value="">Cargando…</option>';
  document.getElementById('btn-sync').style.display = 'none';
  document.getElementById('preview-clases').innerHTML = '';

  if (!carrera) { selSem.innerHTML = '<option value="">—</option>'; return; }

  try {
    const semestres = await api.get('/perfil/semestres?carrera=' + encodeURIComponent(carrera));
    selSem.innerHTML = '<option value="">Selecciona semestre…</option>' +
      semestres.map(s => `<option value="${s}">${s}° Semestre</option>`).join('');
  } catch (err) {
    selSem.innerHTML = '<option value="">Error</option>';
  }
}

function onSemestreChange() {
  const sem = document.getElementById('sel-semestre').value;
  document.getElementById('btn-sync').style.display = sem ? 'inline-flex' : 'none';
}

async function guardarPerfil() {
  const carrera  = document.getElementById('sel-carrera').value;
  const semestre = document.getElementById('sel-semestre').value;
  if (!carrera || !semestre) {
    showAlert('#alert-box', 'Selecciona carrera y semestre', 'error');
    return false;
  }
  try {
    await api.post('/perfil', { carrera, semestre: Number(semestre) });
    showAlert('#alert-box', 'Perfil guardado', 'success');
    mostrarPerfilActual({ carrera, semestre });
    return true;
  } catch (err) {
    showAlert('#alert-box', err.message, 'error');
    return false;
  }
}

async function sincronizarMaterias() {
  const btn = document.getElementById('btn-sync');
  btn.textContent = '⏳ Armando horario…';
  btn.disabled = true;

  const ok = await guardarPerfil();
  if (!ok) { btn.textContent = '🚀 Generar mi horario de clases'; btn.disabled = false; return; }

  try {
    const res = await api.post('/materias/sync', {});
    showAlert('#alert-box',
      `✓ ${res.insertadas} materias nuevas. Horario de clases armado.`, 'success');
    renderPreviewClases(res.horario_clases || []);
  } catch (err) {
    showAlert('#alert-box', err.message, 'error');
  } finally {
    btn.textContent = '🚀 Generar mi horario de clases';
    btn.disabled = false;
  }
}

const DIAS_LABEL = {
  lunes: 'Lun', martes: 'Mar', miercoles: 'Mié',
  jueves: 'Jue', viernes: 'Vie', sabado: 'Sáb',
};

function renderPreviewClases(clases) {
  const box = document.getElementById('preview-clases');
  if (!clases.length) { box.innerHTML = ''; return; }

  const filas = clases.map(m => {
    const dias = {};
    for (const b of (m.bloques || [])) {
      const d = DIAS_LABEL[b.dia] || b.dia;
      if (!dias[d]) dias[d] = [];
      dias[d].push(`${b.hora_inicio}–${b.hora_fin}`);
    }
    const horario = Object.entries(dias)
      .map(([d, hs]) => `<span style="color:var(--accent-secondary)">${d}</span> ${hs.join(', ')}`)
      .join(' &nbsp;|&nbsp; ') || '<span style="color:var(--text-secondary)">Sin horario</span>';

    return `<tr>
      <td><strong>${escHtml(m.materia_codigo)}</strong></td>
      <td>${escHtml(m.materia_nombre || m.materia_codigo)}</td>
      <td><span class="badge badge-admin">${escHtml(m.seccion || '—')}</span></td>
      <td style="font-size:.82rem;color:var(--text-secondary)">${escHtml(m.profesor || '—')}</td>
      <td style="font-size:.82rem">${horario}</td>
    </tr>`;
  }).join('');

  box.innerHTML = `
    <div class="card" style="margin-top:1.5rem">
      <div class="card-header">
        <h3>Horario de clases armado (${clases.length} materias)</h3>
        <a href="/horario/index.html" class="btn btn-primary btn-sm">Ver horario completo →</a>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Código</th><th>Materia</th><th>Sección</th>
              <th>Profesor</th><th>Horario</th>
            </tr>
          </thead>
          <tbody>${filas}</tbody>
        </table>
      </div>
      <p style="margin-top:1rem;color:var(--text-secondary);font-size:.85rem">
        💡 El sistema eligió las secciones sin conflictos y con la menor cantidad de huecos.
        Ve a <a href="/materias/index.html">Mis Materias</a> para ajustar dificultad y horas de estudio.
      </p>
    </div>`;
}
