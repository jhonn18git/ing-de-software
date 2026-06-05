let currentUser = null;

async function init() {
  currentUser = await requireSession();
  if (!currentUser) return;
  setUserChip(currentUser);

  const path = window.location.pathname;
  if (path.includes('list')) await loadMaterias();
  else if (path.includes('create')) initCreateForm();
  else if (path.includes('edit')) {
    const id = new URLSearchParams(window.location.search).get('id');
    if (id) await loadEditForm(Number(id));
  }
}

function renderStars(n) {
  return `<span class="stars" title="Dificultad ${n}/5">${'★'.repeat(n)}${'☆'.repeat(5 - n)}</span>`;
}

async function loadMaterias() {
  const tbody = document.getElementById('materias-tbody');
  tbody.innerHTML = '<tr><td colspan="4" class="loading">Cargando...</td></tr>';
  try {
    const materias = await api.get('/materias');
    if (!materias.length) {
      tbody.innerHTML = `<tr><td colspan="4">
        <div class="empty-state">
          <div class="icon">📚</div>
          <h3>Sin materias registradas</h3>
          <p style="margin-top:.75rem"><a href="/materias/create.html" class="btn btn-primary btn-sm">+ Agregar materia</a></p>
        </div>
      </td></tr>`;
      return;
    }
    tbody.innerHTML = materias.map(m => `
      <tr>
        <td>
          <span class="color-dot" style="background:${escHtml(m.color)}"></span>
          <strong>${escHtml(m.nombre)}</strong>
        </td>
        <td>${renderStars(m.dificultad)}</td>
        <td><code class="color-code" style="border-left:4px solid ${escHtml(m.color)}">${escHtml(m.color)}</code></td>
        <td>
          <div class="actions">
            <a href="/materias/edit.html?id=${m.id}" class="btn btn-sm btn-secondary">Editar</a>
            <button class="btn btn-sm btn-danger"
              data-action="delete-materia" data-id="${m.id}" data-nombre="${escHtml(m.nombre)}">
              Eliminar
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4"><div class="alert alert-error">${escHtml(err.message)}</div></td></tr>`;
  }
}

function initCreateForm() {
  setupStarPreview();
  const form = document.getElementById('materia-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      nombre: document.getElementById('nombre').value.trim(),
      dificultad: parseInt(document.getElementById('dificultad').value),
      color: document.getElementById('color').value
    };
    if (!data.nombre) { showAlert('#alert-box', 'El nombre es obligatorio.', 'error'); return; }
    try {
      await api.post('/materias', data);
      window.location.href = '/materias/list.html';
    } catch (err) {
      showAlert('#alert-box', err.message, 'error');
    }
  });
}

async function loadEditForm(id) {
  try {
    const materias = await api.get('/materias');
    const m = materias.find(x => x.id === id);
    if (!m) { showAlert('#alert-box', 'Materia no encontrada.', 'error'); return; }

    document.getElementById('nombre').value = m.nombre;
    document.getElementById('dificultad').value = m.dificultad;
    document.getElementById('color').value = m.color;
    setupStarPreview();

    const form = document.getElementById('materia-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const data = {
        nombre: document.getElementById('nombre').value.trim(),
        dificultad: parseInt(document.getElementById('dificultad').value),
        color: document.getElementById('color').value
      };
      if (!data.nombre) { showAlert('#alert-box', 'El nombre es obligatorio.', 'error'); return; }
      try {
        await api.put(`/materias/${id}`, data);
        window.location.href = '/materias/list.html';
      } catch (err) {
        showAlert('#alert-box', err.message, 'error');
      }
    });
  } catch (err) {
    showAlert('#alert-box', err.message, 'error');
  }
}

function setupStarPreview() {
  const input = document.getElementById('dificultad');
  const preview = document.getElementById('star-preview');
  if (!input || !preview) return;
  const update = () => { preview.innerHTML = renderStars(parseInt(input.value)); };
  input.addEventListener('input', update);
  update();
}

async function deleteMateria(id, nombre) {
  if (!confirm(`¿Eliminar la materia "${nombre}"? También se eliminarán sus evaluaciones.`)) return;
  try {
    await api.delete(`/materias/${id}`);
    await loadMaterias();
    showAlert('#alert-global', 'Materia eliminada.', 'success');
  } catch (err) {
    showAlert('#alert-global', err.message, 'error');
  }
}

document.addEventListener('click', function (e) {
  const btn = e.target.closest('[data-action="delete-materia"]');
  if (!btn) return;
  deleteMateria(Number(btn.dataset.id), btn.dataset.nombre);
});

document.addEventListener('DOMContentLoaded', init);
