let currentUser = null;

async function init() {
  currentUser = await requireSession();
  if (!currentUser) return;
  setUserChip(currentUser);

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

async function loadProducts() {
  const tbody = document.getElementById('products-tbody');
  tbody.innerHTML = '<tr><td colspan="6" class="loading">Cargando...</td></tr>';

  try {
    const products = await api.get('/products');
    if (!products.length) {
      tbody.innerHTML = `<tr><td colspan="6">
        <div class="empty-state"><div class="icon">📦</div><h3>Sin productos</h3></div>
      </td></tr>`;
      return;
    }

    tbody.innerHTML = products.map(p => `
      <tr>
        <td><strong>${p.title}</strong></td>
        <td>${p.category}</td>
        <td>Bs. ${parseFloat(p.price).toFixed(2)}</td>
        <td>${getStatusBadge(p.status)}</td>
        <td>${p.ofertante_name || '—'}</td>
        <td>
          <div class="actions">
            ${canEdit(p) ? `<a href="/productos/edit.html?id=${p.id}" class="btn btn-sm btn-secondary">Editar</a>` : ''}
            ${canDelete(p) ? `<button onclick="deleteProduct(${p.id}, '${p.title}')" class="btn btn-sm btn-danger">Eliminar</button>` : ''}
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="alert alert-error">${err.message}</div></td></tr>`;
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
    await api.delete(`/products/${id}`);
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

    if (!data.title || !data.description || isNaN(data.price) || !data.category) {
      showAlert('#alert-box', 'Todos los campos son obligatorios.', 'error');
      return;
    }

    try {
      await api.post('/products', data);
      window.location.href = '/productos/list.html';
    } catch (err) {
      showAlert('#alert-box', err.message, 'error');
    }
  });
}

async function loadEditForm(id) {
  try {
    const product = await api.get(`/products/${id}`);
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

      try {
        await api.put(`/products/${id}`, data);
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
    const products = await api.get('/products/pending');
    if (!products.length) {
      tbody.innerHTML = `<tr><td colspan="6">
        <div class="empty-state"><div class="icon">✅</div><h3>Sin productos pendientes</h3></div>
      </td></tr>`;
      return;
    }

    tbody.innerHTML = products.map(p => `
      <tr>
        <td><strong>${p.title}</strong></td>
        <td>${p.category}</td>
        <td>Bs. ${parseFloat(p.price).toFixed(2)}</td>
        <td>${p.ofertante_name || '—'}</td>
        <td>${formatDate(p.created_at)}</td>
        <td>
          <div class="actions">
            <button onclick="changeStatus(${p.id}, 'aprobado')" class="btn btn-sm btn-success">Aprobar</button>
            <button onclick="changeStatus(${p.id}, 'rechazado')" class="btn btn-sm btn-danger">Rechazar</button>
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="alert alert-error">${err.message}</div></td></tr>`;
  }
}

async function changeStatus(id, status) {
  try {
    const res = await api.patch(`/products/${id}/status`, { status });
    showAlert('#alert-global', res.message || `Producto ${status}.`, 'success');
    await loadPending();
  } catch (err) {
    showAlert('#alert-global', err.message, 'error');
  }
}

document.addEventListener('DOMContentLoaded', init);
