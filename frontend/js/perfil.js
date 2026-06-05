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
    if (res.perfil) {
      mostrarPerfilActual(res.perfil);
    }
  } catch (_) {}
}

function mostrarPerfilActual(p) {
  const box = document.getElementById('perfil-actual');
  box.innerHTML = `
    <div class="alert alert-info" style="margin-bottom:1rem">
      <strong>Perfil actual:</strong>
      ${escHtml(p.carrera)} — Semestre ${escHtml(String(p.semestre))} — Grupo ${escHtml(p.grupo)}
    </div>`;
}

async function cargarCarreras() {
  try {
    const carreras = await api.get('/perfil/carreras');
    const sel = document.getElementById('sel-carrera');
    if (carreras.length === 0) {
      sel.innerHTML = '<option value="">— Sin datos USFX cargados —</option>';
      return;
    }
    sel.innerHTML = '<option value="">Selecciona una carrera…</option>' +
      carreras.map(c => `<option value="${escHtml(c)}">${escHtml(c)}</option>`).join('');
  } catch (err) {
    showAlert('#alert-box', 'No se pudo cargar la lista de carreras: ' + err.message, 'error');
  }
}

async function onCarreraChange() {
  const carrera = document.getElementById('sel-carrera').value;
  const selSem  = document.getElementById('sel-semestre');
  const selGrp  = document.getElementById('sel-grupo');
  selSem.innerHTML = '<option value="">Cargando…</option>';
  selGrp.innerHTML = '<option value="">—</option>';
  document.getElementById('btn-sync').style.display = 'none';
  if (!carrera) { selSem.innerHTML = '<option value="">—</option>'; return; }

  try {
    const semestres = await api.get('/perfil/semestres?carrera=' + encodeURIComponent(carrera));
    selSem.innerHTML = '<option value="">Selecciona semestre…</option>' +
      semestres.map(s => `<option value="${s}">${s}° Semestre</option>`).join('');
  } catch (err) {
    selSem.innerHTML = '<option value="">Error</option>';
  }
}

async function onSemestreChange() {
  const carrera  = document.getElementById('sel-carrera').value;
  const semestre = document.getElementById('sel-semestre').value;
  const selGrp   = document.getElementById('sel-grupo');
  selGrp.innerHTML = '<option value="">Cargando…</option>';
  document.getElementById('btn-sync').style.display = 'none';
  if (!semestre) { selGrp.innerHTML = '<option value="">—</option>'; return; }

  try {
    const grupos = await api.get(
      '/perfil/grupos?carrera=' + encodeURIComponent(carrera) +
      '&semestre=' + encodeURIComponent(semestre)
    );
    selGrp.innerHTML = '<option value="">Selecciona grupo…</option>' +
      grupos.map(g => `<option value="${g}">Grupo ${escHtml(g)}</option>`).join('');
    selGrp.addEventListener('change', () => {
      document.getElementById('btn-sync').style.display =
        selGrp.value ? 'inline-flex' : 'none';
    }, { once: false });
  } catch (err) {
    selGrp.innerHTML = '<option value="">Error</option>';
  }
}

async function guardarPerfil() {
  const carrera  = document.getElementById('sel-carrera').value;
  const semestre = document.getElementById('sel-semestre').value;
  const grupo    = document.getElementById('sel-grupo').value;

  if (!carrera || !semestre || !grupo) {
    showAlert('#alert-box', 'Selecciona carrera, semestre y grupo', 'error');
    return;
  }

  try {
    await api.post('/perfil', { carrera, semestre: Number(semestre), grupo });
    showAlert('#alert-box', 'Perfil guardado correctamente', 'success');
    mostrarPerfilActual({ carrera, semestre, grupo });
  } catch (err) {
    showAlert('#alert-box', err.message, 'error');
  }
}

async function sincronizarMaterias() {
  const btn = document.getElementById('btn-sync');
  btn.textContent = 'Sincronizando…';
  btn.disabled = true;

  // Primero guardar el perfil seleccionado
  await guardarPerfil();

  try {
    const res = await api.post('/materias/sync', {});
    showAlert('#alert-box',
      `✓ Materias sincronizadas: ${res.insertadas} nuevas (total ${res.materias.length})`,
      'success'
    );
    renderPreviewMaterias(res.materias);
  } catch (err) {
    showAlert('#alert-box', err.message, 'error');
  } finally {
    btn.textContent = '📚 Cargar mis materias';
    btn.disabled = false;
  }
}

function renderPreviewMaterias(materias) {
  const box = document.getElementById('preview-materias');
  if (!materias.length) {
    box.innerHTML = '';
    return;
  }
  box.innerHTML = `
    <div class="card" style="margin-top:1.5rem">
      <h3 style="margin-bottom:1rem">Materias cargadas (${materias.length})</h3>
      <div class="table-container">
        <table>
          <thead><tr><th>Código</th><th>Materia</th><th>Dificultad</th><th>Horas/sem</th></tr></thead>
          <tbody>
            ${materias.map(m => `
              <tr>
                <td><strong>${escHtml(m.materia_codigo)}</strong></td>
                <td>${escHtml(m.materia_nombre)}</td>
                <td>${renderStars(m.dificultad)}</td>
                <td>${escHtml(String(m.horas_semana))}h</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
      <div style="margin-top:1rem">
        <a href="/materias/index.html" class="btn btn-primary">Ir a Mis Materias →</a>
      </div>
    </div>`;
}

function renderStars(n) {
  return `<span class="stars">${'★'.repeat(n)}${'☆'.repeat(5 - n)}</span>`;
}
