let currentUser = null;
const DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'];

async function init() {
  currentUser = await requireSession();
  if (!currentUser) return;
  setUserChip(currentUser);
  await loadDisponibilidad();
}

async function loadDisponibilidad() {
  try {
    const disp = await api.get('/disponibilidad');
    DIAS.forEach(d => {
      const input = document.getElementById(d);
      if (input) input.value = disp[d] || 0;
    });
    updateTotal();
  } catch (err) {
    showAlert('#alert-box', err.message, 'error');
    return;
  }

  DIAS.forEach(d => {
    const input = document.getElementById(d);
    if (input) input.addEventListener('input', updateTotal);
  });

  const form = document.getElementById('disp-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {};
    DIAS.forEach(d => { data[d] = parseInt(document.getElementById(d).value) || 0; });
    try {
      await api.post('/disponibilidad', data);
      showAlert('#alert-box', 'Disponibilidad guardada correctamente.', 'success');
      updateTotal();
    } catch (err) {
      showAlert('#alert-box', err.message, 'error');
    }
  });
}

function updateTotal() {
  const total = DIAS.reduce((sum, d) => sum + (parseInt(document.getElementById(d)?.value) || 0), 0);
  const el = document.getElementById('total-horas');
  if (el) el.textContent = total;
  const bar = document.getElementById('total-bar');
  if (bar) bar.style.width = Math.min(100, (total / 84) * 100) + '%';
}

document.addEventListener('DOMContentLoaded', init);
