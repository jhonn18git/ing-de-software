let currentUser = null;

async function init() {
  currentUser = await requireSession();
  if (!currentUser) return;

  setUserChip(currentUser);

  if (window.location.pathname.includes('list')) {
    if (currentUser.rol !== 'admin') {
      document.getElementById('content').innerHTML =
        '<div class="alert alert-error">Acceso restringido a administradores.</div>';
      return;
    }
    await loadUsers();
  } else if (window.location.pathname.includes('create')) {
    initCreateForm();
  } else if (window.location.pathname.includes('edit')) {
    const id = new URLSearchParams(window.location.search).get('id');
    if (id) await loadEditForm(id);
  }
}

async function loadUsers() {
  const tbody = document.getElementById('users-tbody');
  tbody.innerHTML = '<tr><td colspan="5" class="loading">Cargando usuarios...</td></tr>';

  try {
    const users = await api.get('/usuarios');
    if (!users.length) {
      tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><div class="icon">👤</div><h3>Sin usuarios</h3></div></td></tr>';
      return;
    }

    tbody.innerHTML = users.map(u => `
      <tr>
        <td><strong>${escHtml(u.name)}</strong></td>
        <td>${escHtml(u.username)}</td>
        <td>${escHtml(u.email)}</td>
        <td>${formatDate(u.created_at)}</td>
        <td>
          <div class="actions">
            <a href="/usuarios/edit.html?id=${u.id}" class="btn btn-sm btn-secondary">Editar</a>
            ${u.id !== currentUser.id
              ? `<button class="btn btn-sm btn-danger" data-action="delete-user" data-id="${u.id}" data-name="${escHtml(u.name)}">Eliminar</button>`
              : ''}
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="alert alert-error">${escHtml(err.message)}</div></td></tr>`;
  }
}

async function deleteUser(id, name) {
  if (!confirm(`¿Eliminar al usuario "${name}"? Esta acción no se puede deshacer.`)) return;

  try {
    await api.delete(`/usuarios/${id}`);
    await loadUsers();
    showAlert('#alert-global', 'Usuario eliminado correctamente.', 'success');
  } catch (err) {
    showAlert('#alert-global', err.message, 'error');
  }
}

function initCreateForm() {
  const form = document.getElementById('user-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      name:     document.getElementById('name').value.trim(),
      username: document.getElementById('username').value.trim(),
      email:    document.getElementById('email').value.trim(),
      password: document.getElementById('password').value,
    };

    if (!data.name || !data.username || !data.email || !data.password) {
      showAlert('#alert-box', 'Todos los campos son obligatorios.', 'error');
      return;
    }

    try {
      await api.post('/usuarios', data);
      window.location.href = '/usuarios/list.html';
    } catch (err) {
      showAlert('#alert-box', err.message, 'error');
    }
  });
}

async function loadEditForm(id) {
  try {
    const user = await api.get(`/usuarios/${id}`);
    document.getElementById('name').value     = user.name;
    document.getElementById('username').value = user.username;
    document.getElementById('email').value    = user.email;

    const form = document.getElementById('user-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const data = {
        name:     document.getElementById('name').value.trim(),
        username: document.getElementById('username').value.trim(),
        email:    document.getElementById('email').value.trim(),
      };

      if (!data.name || !data.username || !data.email) {
        showAlert('#alert-box', 'Nombre, usuario y email son obligatorios.', 'error');
        return;
      }

      const pwd = document.getElementById('password').value;
      if (pwd) data.password = pwd;

      try {
        await api.put(`/usuarios/${id}`, data);
        window.location.href = '/usuarios/list.html';
      } catch (err) {
        showAlert('#alert-box', err.message, 'error');
      }
    });
  } catch (err) {
    showAlert('#alert-box', err.message, 'error');
  }
}

document.addEventListener('click', function (e) {
  const btn = e.target.closest('[data-action="delete-user"]');
  if (!btn) return;
  deleteUser(Number(btn.dataset.id), btn.dataset.name);
});

document.addEventListener('DOMContentLoaded', init);
