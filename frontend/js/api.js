const API_BASE = '/api';

async function apiRequest(method, endpoint, data = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include'
  };
  if (data) options.body = JSON.stringify(data);

  const res = await fetch(`${API_BASE}${endpoint}`, options);
  const json = await res.json().catch(() => ({}));

  if (!res.ok) throw new Error(json.error || `Error ${res.status}`);
  return json;
}

const api = {
  get: (endpoint) => apiRequest('GET', endpoint),
  post: (endpoint, data) => apiRequest('POST', endpoint, data),
  put: (endpoint, data) => apiRequest('PUT', endpoint, data),
  patch: (endpoint, data) => apiRequest('PATCH', endpoint, data),
  delete: (endpoint) => apiRequest('DELETE', endpoint)
};

function showAlert(container, message, type = 'error') {
  const el = document.querySelector(container);
  if (!el) return;
  el.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
  setTimeout(() => { if (el) el.innerHTML = ''; }, 5000);
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('es-BO', {
    year: 'numeric', month: 'short', day: 'numeric'
  });
}

function getBadgeHtml(rol) {
  const map = { admin: 'badge-admin', ofertante: 'badge-ofertante', demandante: 'badge-demandante' };
  return `<span class="badge ${map[rol] || ''}">${rol}</span>`;
}

function getStatusBadge(status) {
  const map = { pendiente: 'badge-pendiente', aprobado: 'badge-aprobado', rechazado: 'badge-rechazado' };
  return `<span class="badge ${map[status] || ''}">${status}</span>`;
}

async function getCurrentUser() {
  try {
    const data = await api.get('/auth/me');
    return data.user;
  } catch (err) {
    if (err.message && err.message.includes('Failed to fetch')) {
      return 'network-error';
    }
    return null;
  }
}

async function requireSession(redirectTo = '/index.html') {
  const user = await getCurrentUser();
  if (user === 'network-error') {
    setTimeout(() => window.location.reload(), 3000);
    return null;
  }
  if (!user) {
    window.location.href = redirectTo;
    return null;
  }
  return user;
}

function setUserChip(user) {
  const nameEl = document.getElementById('user-name');
  const roleEl = document.getElementById('user-role');
  const avatarEl = document.getElementById('user-avatar');
  if (nameEl) nameEl.textContent = user.name;
  if (roleEl) roleEl.textContent = user.rol;
  if (avatarEl) avatarEl.textContent = user.name.charAt(0).toUpperCase();
}
