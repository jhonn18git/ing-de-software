let currentUser = null;

async function init() {
  currentUser = await requireSession();
  if (!currentUser) return;
  setUserChip(currentUser);
  updateSidebar(currentUser);

  const path = window.location.pathname;

  if (path.includes('list')) await loadProducts();
  else if (path.includes('create')) initCreateForm();
  else if (path.includes('edit')) {
    const id = new URLSearchParams(window.location.search).get('id');
    if (id) await loadEditForm(id);
  } else if (path.includes('pendiente')) {
    if (currentUser.rol !== 'admin') {
      document.getElementById('content').innerHTML =
        '<div class="alert alert-error">Acceso restringido a administradores.</div>';
      return;
    }
    await loadPending();
  }
}

function updateSidebar(user) {
  const navAdmin = document.getElementById('nav-admin-section');
  const navUsers = document.getElementById('nav-users');
  const navPending = document.getElementById('nav-pending');
  const navCreate = document.getElementById('nav-create');
  const btnCreate = document.getElementById('btn-create');

  if (user.rol === 'admin') {
    if (navAdmin) navAdmin.style.display = 'block';
    if (navUsers) navUsers.style.display = 'flex';
    if (navPending) navPending.style.display = 'flex';
  }
  if (user.rol !== 'demandante') {
    if (navCreate) navCreate.style.display = 'flex';
    if (btnCreate) btnCreate.style.display = 'inline-flex';
  }
}

async function loadProducts() {
  const tbody = document.getElementById('products-tbody');
  tbody.innerHTML = '<tr><td colspan="6" class="loading">Cargando...</td></tr>';

  try {
    const products = await api.get('/productos');
    if (!products.length) {
      tbody.innerHTML = `<tr><td colspan="6">
        <div class="empty-state"><div class="icon">📦</div><h3>Sin productos</h3></div>
      </td></tr>`;
      return;
    }

    tbody.innerHTML = products.map(p => `
      <tr>
        <td><strong>${escHtml(p.title)}</strong></td>
        <td>${escHtml(p.category)}</td>
        <td>Bs. ${parseFloat(p.price).toFixed(2)}</td>
        <td>${getStatusBadge(p.status)}</td>
        <td>${escHtml(p.ofertante_name || '—')}</td>
        <td>
          <div class="actions">
            ${canEdit(p) ? `<a href="/productos/edit.html?id=${p.id}" class="btn btn-sm btn-secondary">Editar</a>` : ''}
            ${canDelete(p) ? `<button class="btn btn-sm btn-danger" data-action="delete-product" data-id="${p.id}" data-title="${escHtml(p.title)}">Eliminar</button>` : ''}
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="alert alert-error">${escHtml(err.message)}</div></td></tr>`;
  }
}

function canEdit(p) {
  return currentUser.rol === 'admin' || (currentUser.rol === 'ofertante' && p.ofertante_id === currentUser.id);
}

function canDelete(p) {
  return currentUser.rol === 'admin' || (currentUser.rol === 'ofertante' && p.ofertante_id === currentUser.id);
}

async function deleteProduct(id, title) {
  if (!confirm(`¿Eliminar el producto "${title}"?`)) return;
  try {
    await api.delete(`/productos/${id}`);
    await loadProducts();
    showAlert('#alert-global', 'Producto eliminado.', 'success');
  } catch (err) {
    showAlert('#alert-global', err.message, 'error');
  }
}

function initCreateForm() {
  if (currentUser.rol === 'demandante') {
    document.getElementById('content').innerHTML =
      '<div class="alert alert-error">Solo ofertantes pueden crear productos.</div>';
    return;
  }

  const form = document.getElementById('product-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      title: document.getElementById('title').value.trim(),
      description: document.getElementById('description').value.trim(),
      price: parseFloat(document.getElementById('price').value),
      category: document.getElementById('category').value.trim()
    };

    if (!data.title || !data.description || isNaN(data.price) || data.price < 0 || !data.category) {
      showAlert('#alert-box', 'Todos los campos son obligatorios y el precio debe ser ≥ 0.', 'error');
      return;
    }

    try {
      await api.post('/productos', data);
      window.location.href = '/productos/list.html';
    } catch (err) {
      showAlert('#alert-box', err.message, 'error');
    }
  });
}

async function loadEditForm(id) {
  try {
    const product = await api.get(`/productos/${id}`);
    document.getElementById('title').value = product.title;
    document.getElementById('description').value = product.description;
    document.getElementById('price').value = product.price;
    document.getElementById('category').value = product.category;

    const form = document.getElementById('product-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const data = {
        title: document.getElementById('title').value.trim(),
        description: document.getElementById('description').value.trim(),
        price: parseFloat(document.getElementById('price').value),
        category: document.getElementById('category').value.trim()
      };

      if (!data.title || !data.description || isNaN(data.price) || data.price < 0 || !data.category) {
        showAlert('#alert-box', 'Todos los campos son obligatorios y el precio debe ser ≥ 0.', 'error');
        return;
      }

      try {
        await api.put(`/productos/${id}`, data);
        window.location.href = '/productos/list.html';
      } catch (err) {
        showAlert('#alert-box', err.message, 'error');
      }
    });
  } catch (err) {
    showAlert('#alert-box', err.message, 'error');
  }
}

async function loadPending() {
  const tbody = document.getElementById('pending-tbody');
  tbody.innerHTML = '<tr><td colspan="6" class="loading">Cargando...</td></tr>';

  try {
    const products = await api.get('/productos/pendientes');
    if (!products.length) {
      tbody.innerHTML = `<tr><td colspan="6">
        <div class="empty-state"><div class="icon">✅</div><h3>Sin productos pendientes</h3></div>
      </td></tr>`;
      return;
    }

    tbody.innerHTML = products.map(p => `
      <tr>
        <td><strong>${escHtml(p.title)}</strong></td>
        <td>${escHtml(p.category)}</td>
        <td>Bs. ${parseFloat(p.price).toFixed(2)}</td>
        <td>${escHtml(p.ofertante_name || '—')}</td>
        <td>${formatDate(p.created_at)}</td>
        <td>
          <div class="actions">
            <button class="btn btn-sm btn-success" data-action="status" data-id="${p.id}" data-status="aprobado">Aprobar</button>
            <button class="btn btn-sm btn-danger" data-action="status" data-id="${p.id}" data-status="rechazado">Rechazar</button>
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="alert alert-error">${escHtml(err.message)}</div></td></tr>`;
  }
}

async function changeStatus(id, status) {
  try {
    const res = await api.patch(`/productos/${id}/status`, { status });
    showAlert('#alert-global', res.message || `Producto ${status}.`, 'success');
    await loadPending();
  } catch (err) {
    showAlert('#alert-global', err.message, 'error');
  }
}

document.addEventListener('click', function (e) {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;
  const id = Number(btn.dataset.id);
  if (action === 'delete-product') deleteProduct(id, btn.dataset.title);
  if (action === 'status') changeStatus(id, btn.dataset.status);
});

document.addEventListener('DOMContentLoaded', init);
