let materiasData = [];

document.addEventListener('DOMContentLoaded', async () => {
  const user = await requireSession();
  if (!user) return;
  setUserChip(user);
  await cargarMaterias();

  document.getElementById('btn-sync').addEventListener('click', syncMaterias);
  document.addEventListener('change', onFieldChange);
});

async function cargarMaterias() {
  try {
    const rows = await api.get('/materias');
    materiasData = rows;
    renderTabla(rows);
  } catch (err) {
    showAlert('#alert-global', 'Error al cargar materias: ' + err.message, 'error');
  }
}

function renderTabla(materias) {
  const tbody = document.getElementById('materias-tbody');
  if (!materias.length) {
    tbody.innerHTML = `
      <tr><td colspan="6" class="empty-state">
        No tienes materias registradas.<br>
        <a href="/perfil/index.html" class="btn btn-primary" style="margin-top:.75rem">
          Configura tu perfil académico
        </a>
      </td></tr>`;
    return;
  }

  tbody.innerHTML = materias.map(m => `
    <tr data-id="${m.id}">
      <td><strong>${escHtml(m.materia_codigo)}</strong></td>
      <td>${escHtml(m.materia_nombre)}</td>
      <td>
        <div class="stars-edit">
          ${[1,2,3,4,5].map(n =>
            `<span class="star-btn ${n <= m.dificultad ? 'active' : ''}"
                   data-id="${m.id}" data-val="${n}"
                   title="${n} estrella${n>1?'s':''}">★</span>`
          ).join('')}
        </div>
      </td>
      <td>
        <input type="number" value="${m.horas_semana}"
               min="1" max="20" data-id="${m.id}" data-field="horas_semana"
               class="input-sm" style="width:60px">
        <span style="color:#64748b;font-size:.85rem">h/sem</span>
      </td>
      <td>
        <input type="color" value="${escHtml(m.color)}"
               data-id="${m.id}" data-field="color">
        <span class="color-preview" style="background:${escHtml(m.color)}"></span>
      </td>
      <td>
        <button class="btn btn-sm btn-danger"
                data-action="del" data-id="${m.id}"
                data-nombre="${escHtml(m.materia_nombre)}">Eliminar</button>
      </td>
    </tr>`).join('');

  // Estrellas clickeables
  document.querySelectorAll('.star-btn').forEach(star => {
    star.addEventListener('click', async e => {
      const id  = Number(e.target.dataset.id);
      const val = Number(e.target.dataset.val);
      await guardarCampo(id, 'dificultad', val);
    });
  });

  // Eliminar (delegación)
  tbody.addEventListener('click', async e => {
    const btn = e.target.closest('[data-action="del"]');
    if (!btn) return;
    const id = Number(btn.dataset.id);
    const nombre = btn.dataset.nombre;
    if (!confirm(`¿Eliminar "${nombre}"?`)) return;
    try {
      await api.delete('/materias/' + id);
      await cargarMaterias();
    } catch (err) {
      showAlert('#alert-global', err.message, 'error');
    }
  });
}

async function onFieldChange(e) {
  const el = e.target;
  if (!el.dataset.field || !el.dataset.id) return;
  const id    = Number(el.dataset.id);
  const field = el.dataset.field;
  let val = el.value;
  if (field === 'horas_semana') val = Number(val);
  await guardarCampo(id, field, val);
  if (field === 'color') {
    const preview = el.closest('td').querySelector('.color-preview');
    if (preview) preview.style.background = val;
  }
}

async function guardarCampo(id, field, value) {
  try {
    const m = materiasData.find(x => x.id === id);
    const payload = {
      dificultad:   m ? m.dificultad   : 3,
      horas_semana: m ? m.horas_semana : 2,
      color:        m ? m.color        : '#3182ce',
    };
    payload[field] = value;
    const updated = await api.put('/materias/' + id, payload);
    const idx = materiasData.findIndex(x => x.id === id);
    if (idx >= 0) materiasData[idx] = updated;
    if (field === 'dificultad') {
      document.querySelectorAll(`.star-btn[data-id="${id}"]`).forEach(s => {
        s.classList.toggle('active', Number(s.dataset.val) <= value);
      });
    }
  } catch (err) {
    showAlert('#alert-global', 'Error al guardar: ' + err.message, 'error');
  }
}

async function syncMaterias() {
  const btn = document.getElementById('btn-sync');
  btn.textContent = 'Sincronizando…';
  btn.disabled = true;
  try {
    const res = await api.post('/materias/sync', {});
    showAlert('#alert-global', `✓ ${res.insertadas} materias nuevas importadas`, 'success');
    await cargarMaterias();
  } catch (err) {
    showAlert('#alert-global', err.message, 'error');
  } finally {
    btn.textContent = '🔄 Re-sincronizar';
    btn.disabled = false;
  }
}
