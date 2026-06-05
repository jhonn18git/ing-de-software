let currentUser = null;

async function init() {
  currentUser = await requireSession();
  if (!currentUser) return;
  setUserChip(currentUser);

  const path = window.location.pathname;
  if (path.includes('list')) await loadEvaluaciones();
  else if (path.includes('create')) await initForm(null);
  else if (path.includes('edit')) {
    const id = new URLSearchParams(window.location.search).get('id');
    if (id) await initForm(Number(id));
  }
}

function diasRestantes(fechaStr) {
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
  const fecha = new Date(fechaStr + 'T00:00:00');
  return Math.round((fecha - hoy) / 86400000);
}

function proximidadBadge(fechaStr) {
  const dias = diasRestantes(fechaStr);
  if (dias < 0) return '<span class="badge badge-rechazado">Vencida</span>';
  if (dias === 0) return '<span class="badge badge-rechazado">¡Hoy!</span>';
  if (dias <= 3) return `<span class="badge badge-rechazado">${dias}d restantes</span>`;
  if (dias <= 7) return `<span class="badge badge-pendiente">${dias}d restantes</span>`;
  return `<span class="badge badge-aprobado">${dias}d restantes</span>`;
}

async function loadEvaluaciones() {
  const tbody = document.getElementById('eval-tbody');
  tbody.innerHTML = '<tr><td colspan="6" class="loading">Cargando...</td></tr>';
  try {
    const evs = await api.get('/evaluaciones');
    if (!evs.length) {
      tbody.innerHTML = `<tr><td colspan="6">
        <div class="empty-state">
          <div class="icon">📝</div>
          <h3>Sin evaluaciones registradas</h3>
          <p style="margin-top:.75rem"><a href="/evaluaciones/create.html" class="btn btn-primary btn-sm">+ Agregar evaluación</a></p>
        </div>
      </td></tr>`;
      return;
    }
    tbody.innerHTML = evs.map(e => `
      <tr>
        <td><strong>${escHtml(e.titulo)}</strong></td>
        <td>
          ${e.materia_color ? `<span class="color-dot" style="background:${escHtml(e.materia_color)}"></span>` : ''}
          ${escHtml(e.materia_nombre || '—')}
        </td>
        <td>${formatDate(e.fecha)}</td>
        <td><span class="badge tipo-${escHtml(e.tipo)}">${escHtml(e.tipo)}</span></td>
        <td>${proximidadBadge(e.fecha)}</td>
        <td>
          <div class="actions">
            <a href="/evaluaciones/edit.html?id=${e.id}" class="btn btn-sm btn-secondary">Editar</a>
            <button class="btn btn-sm btn-danger"
              data-action="delete-eval" data-id="${e.id}" data-titulo="${escHtml(e.titulo)}">
              Eliminar
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="alert alert-error">${escHtml(err.message)}</div></td></tr>`;
  }
}

async function initForm(editId) {
  const select = document.getElementById('materia_id');
  try {
    const materias = await api.get('/materias');
    if (!materias.length) {
      document.getElementById('content').innerHTML =
        '<div class="alert alert-info" style="margin:1rem">Primero debes <a href="/materias/create.html" class="btn btn-sm btn-primary" style="margin-left:.5rem">registrar materias</a></div>';
      return;
    }
    materias.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.nombre;
      select.appendChild(opt);
    });
  } catch (err) {
    showAlert('#alert-box', err.message, 'error');
    return;
  }

  if (editId) {
    try {
      const evs = await api.get('/evaluaciones');
      const ev = evs.find(x => x.id === editId);
      if (!ev) { showAlert('#alert-box', 'Evaluación no encontrada.', 'error'); return; }
      document.getElementById('titulo').value = ev.titulo;
      document.getElementById('materia_id').value = ev.materia_id;
      document.getElementById('fecha').value = ev.fecha;
      document.getElementById('tipo').value = ev.tipo;
    } catch (err) {
      showAlert('#alert-box', err.message, 'error');
      return;
    }
  }

  const form = document.getElementById('eval-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      titulo: document.getElementById('titulo').value.trim(),
      materia_id: parseInt(document.getElementById('materia_id').value),
      fecha: document.getElementById('fecha').value,
      tipo: document.getElementById('tipo').value
    };
    if (!data.titulo || !data.fecha) {
      showAlert('#alert-box', 'Título y fecha son obligatorios.', 'error');
      return;
    }
    try {
      if (editId) await api.put(`/evaluaciones/${editId}`, data);
      else await api.post('/evaluaciones', data);
      window.location.href = '/evaluaciones/list.html';
    } catch (err) {
      showAlert('#alert-box', err.message, 'error');
    }
  });
}

async function deleteEvaluacion(id, titulo) {
  if (!confirm(`¿Eliminar la evaluación "${titulo}"?`)) return;
  try {
    await api.delete(`/evaluaciones/${id}`);
    await loadEvaluaciones();
    showAlert('#alert-global', 'Evaluación eliminada.', 'success');
  } catch (err) {
    showAlert('#alert-global', err.message, 'error');
  }
}

document.addEventListener('click', function (e) {
  const btn = e.target.closest('[data-action="delete-eval"]');
  if (!btn) return;
  deleteEvaluacion(Number(btn.dataset.id), btn.dataset.titulo);
});

document.addEventListener('DOMContentLoaded', init);
