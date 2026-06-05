let materiasDisp = [];
let editId = null;

document.addEventListener('DOMContentLoaded', async () => {
  const user = await requireSession();
  if (!user) return;
  setUserChip(user);

  await cargarMaterias();
  await cargarEvaluaciones();

  document.getElementById('form-eval').addEventListener('submit', onSubmit);
  document.getElementById('btn-cancelar').addEventListener('click', cancelarEdit);
  document.getElementById('fecha').min = new Date().toISOString().slice(0, 10);
});

async function cargarMaterias() {
  try {
    materiasDisp = await api.get('/materias');
    const sel = document.getElementById('sel-materia');
    if (!materiasDisp.length) {
      sel.innerHTML = '<option value="">— Sin materias registradas —</option>';
      return;
    }
    sel.innerHTML = '<option value="">Selecciona materia…</option>' +
      materiasDisp.map(m =>
        `<option value="${escHtml(m.materia_codigo)}" data-nombre="${escHtml(m.materia_nombre)}">
          ${escHtml(m.materia_codigo)} — ${escHtml(m.materia_nombre)}
        </option>`
      ).join('');
  } catch (_) {}
}

async function cargarEvaluaciones() {
  const tbody = document.getElementById('eval-tbody');
  tbody.innerHTML = '<tr><td colspan="6" class="loading">Cargando…</td></tr>';
  try {
    const evals = await api.get('/evaluaciones');
    if (!evals.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No hay evaluaciones registradas</td></tr>';
      return;
    }
    tbody.innerHTML = evals.map(e => {
      const dias = diasRestantes(e.fecha);
      return `
        <tr>
          <td><strong>${escHtml(e.materia_codigo)}</strong><br>
              <small style="color:#64748b">${escHtml(e.materia_nombre)}</small></td>
          <td>${escHtml(e.titulo)}</td>
          <td>${escHtml(e.fecha)}</td>
          <td>${badgeTipo(e.tipo)}</td>
          <td>${badgeDias(dias)}</td>
          <td>
            <button class="btn btn-sm btn-secondary"
                    data-action="edit" data-id="${e.id}">Editar</button>
            <button class="btn btn-sm btn-danger"
                    data-action="del" data-id="${e.id}"
                    data-titulo="${escHtml(e.titulo)}">Eliminar</button>
          </td>
        </tr>`;
    }).join('');

    tbody.addEventListener('click', async ev => {
      const btn = ev.target.closest('[data-action]');
      if (!btn) return;
      const id = Number(btn.dataset.id);
      if (btn.dataset.action === 'edit') cargarEdit(id);
      if (btn.dataset.action === 'del') {
        if (!confirm(`¿Eliminar "${btn.dataset.titulo}"?`)) return;
        await api.delete('/evaluaciones/' + id);
        await cargarEvaluaciones();
      }
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">${escHtml(err.message)}</td></tr>`;
  }
}

function cargarEdit(id) {
  const evals = Array.from(document.querySelectorAll('#eval-tbody tr'))
    .map(tr => {
      const btns = tr.querySelectorAll('[data-id]');
      return btns.length ? btns[0].dataset.id : null;
    });

  // Buscar de la API (o re-cargar)
  api.get('/evaluaciones').then(list => {
    const e = list.find(x => x.id === id);
    if (!e) return;

    editId = id;
    document.getElementById('form-titulo').textContent = 'Editar Evaluación';
    document.getElementById('ev-titulo').value  = e.titulo;
    document.getElementById('fecha').value       = e.fecha;
    document.getElementById('tipo').value        = e.tipo;
    document.getElementById('btn-cancelar').style.display = 'inline-flex';

    // Seleccionar materia
    const sel = document.getElementById('sel-materia');
    sel.value = e.materia_codigo;

    document.getElementById('form-eval').scrollIntoView({ behavior: 'smooth' });
  });
}

function cancelarEdit() {
  editId = null;
  document.getElementById('form-titulo').textContent = 'Agregar Evaluación';
  document.getElementById('form-eval').reset();
  document.getElementById('btn-cancelar').style.display = 'none';
}

async function onSubmit(ev) {
  ev.preventDefault();
  const sel    = document.getElementById('sel-materia');
  const codigo = sel.value;
  const nombre = sel.options[sel.selectedIndex]?.dataset?.nombre || codigo;
  const titulo = document.getElementById('ev-titulo').value.trim();
  const fecha  = document.getElementById('fecha').value;
  const tipo   = document.getElementById('tipo').value;

  if (!codigo || !titulo || !fecha) {
    showAlert('#alert-form', 'Completa todos los campos', 'error');
    return;
  }

  const payload = {
    materia_codigo: codigo,
    materia_nombre: nombre,
    titulo, fecha, tipo,
  };

  try {
    if (editId) {
      await api.put('/evaluaciones/' + editId, payload);
    } else {
      await api.post('/evaluaciones', payload);
    }
    cancelarEdit();
    await cargarEvaluaciones();
  } catch (err) {
    showAlert('#alert-form', err.message, 'error');
  }
}

function diasRestantes(fechaStr) {
  const hoy    = new Date(); hoy.setHours(0, 0, 0, 0);
  const fecha  = new Date(fechaStr + 'T00:00:00');
  return Math.round((fecha - hoy) / 86400000);
}

function badgeDias(dias) {
  if (dias < 0)  return `<span class="badge badge-rechazado">Pasada</span>`;
  if (dias === 0) return `<span class="badge badge-rechazado">¡Hoy!</span>`;
  if (dias <= 3)  return `<span class="badge badge-rechazado">${dias}d</span>`;
  if (dias <= 7)  return `<span class="badge badge-pendiente">${dias}d</span>`;
  return `<span class="badge badge-aprobado">${dias}d</span>`;
}

function badgeTipo(tipo) {
  const map = { examen: 'badge-admin', trabajo: 'badge-ofertante', practica: 'badge-demandante', otro: '' };
  return `<span class="badge ${map[tipo] || ''}">${escHtml(tipo)}</span>`;
}
