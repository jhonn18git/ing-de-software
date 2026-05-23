document.addEventListener('DOMContentLoaded', async () => {
  const user = await getCurrentUser();
  if (user) {
    window.location.href = '/panel.html';
    return;
  }

  const form = document.getElementById('login-form');
  const alertBox = document.getElementById('alert-box');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    if (!username || !password) {
      alertBox.innerHTML = '<div class="alert alert-error">Completa todos los campos.</div>';
      return;
    }

    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Iniciando sesión...';

    try {
      await api.post('/auth/login', { username, password });
      window.location.href = '/panel.html';
    } catch (err) {
      alertBox.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
      btn.disabled = false;
      btn.textContent = 'Iniciar Sesión';
    }
  });
});

async function logout() {
  try {
    await api.post('/auth/logout');
  } finally {
    window.location.href = '/index.html';
  }
}
