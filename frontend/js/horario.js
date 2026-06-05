let currentUser = null;
let chart = null;

const DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'];
const DIAS_LABELS = {
  lunes: 'Lunes', martes: 'Martes', miercoles: 'Miércoles',
  jueves: 'Jueves', viernes: 'Viernes', sabado: 'Sábado', domingo: 'Domingo'
};

async function init() {
  currentUser = await requireSession();
  if (!currentUser) return;
  setUserChip(currentUser);
  await checkPrerequisites();
  await loadHorario();
}

async function checkPrerequisites() {
  try {
    const [materias, disp] = await Promise.all([api.get('/materias'), api.get('/disponibilidad')]);
    const avisos = [];
    if (!materias.length)
      avisos.push('No tienes materias registradas. <a href="/materias/create.html">Agregar materias →</a>');
    const totalH = DIAS.reduce((s, d) => s + (disp[d] || 0), 0);
    if (totalH === 0)
      avisos.push('No has configurado horas disponibles. <a href="/disponibilidad/index.html">Configurar →</a>');
    const box = document.getElementById('prereq-box');
    if (box && avisos.length)
      box.innerHTML = avisos.map(a => `<div class="alert alert-info">${a}</div>`).join('');
  } catch (_) { /* silent */ }
}

async function loadHorario() {
  try {
    const res = await api.get('/horarios');
    if (res.horario && Object.values(res.horario).some(d => d.length)) {
      renderHorario(res.horario);
      renderChart(res.horario);
      const ts = document.getElementById('generated-at');
      if (ts && res.generado_at) ts.textContent = 'Generado: ' + formatDate(res.generado_at);
    } else {
      document.getElementById('horario-container').innerHTML =
        '<div class="empty-state"><div class="icon">📅</div><h3>Sin horario generado</h3>' +
        '<p style="color:#64748b;margin-top:.5rem">Configura tus materias y disponibilidad, luego presiona <strong>Generar Horario</strong>.</p></div>';
    }
  } catch (err) {
    document.getElementById('horario-container').innerHTML =
      `<div class="alert alert-error">${escHtml(err.message)}</div>`;
  }
}

function renderHorario(horario) {
  const activeDays = DIAS.filter(d => (horario[d] || []).length > 0);
  if (!activeDays.length) {
    document.getElementById('horario-container').innerHTML =
      '<div class="alert alert-info">El horario está vacío. Verifica tu disponibilidad y materias.</div>';
    return;
  }

  let html = '<div class="horario-grid">';
  activeDays.forEach(dia => {
    const bloques = horario[dia] || [];
    html += `<div class="dia-col">
      <div class="dia-header">${DIAS_LABELS[dia]}</div>
      ${bloques.map(b => `
        <div class="bloque-materia" style="background:${escHtml(b.color)}22;border-left:4px solid ${escHtml(b.color)}">
          <div class="bloque-nombre">${escHtml(b.materia)}</div>
          <div class="bloque-horas">${b.horas}h ${'★'.repeat(b.dificultad)}</div>
        </div>
      `).join('')}
    </div>`;
  });
  html += '</div>';
  document.getElementById('horario-container').innerHTML = html;
}

function renderChart(horario) {
  const totales = {};
  DIAS.forEach(d => {
    (horario[d] || []).forEach(b => {
      if (!totales[b.materia]) totales[b.materia] = { horas: 0, color: b.color };
      totales[b.materia].horas += b.horas;
    });
  });
  const labels = Object.keys(totales);
  if (!labels.length) return;

  const ctx = document.getElementById('chart-horas');
  if (!ctx) return;
  if (chart) chart.destroy();

  chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Horas semanales',
        data: labels.map(k => totales[k].horas),
        backgroundColor: labels.map(k => totales[k].color + 'bb'),
        borderColor: labels.map(k => totales[k].color),
        borderWidth: 2,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: c => `${c.parsed.y}h` } }
      },
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => `${v}h` } }
      }
    }
  });
}

async function generarHorario() {
  const btn = document.getElementById('btn-generar');
  btn.disabled = true;
  btn.textContent = 'Generando...';
  try {
    const res = await api.post('/horarios/generar', {});
    renderHorario(res.horario);
    renderChart(res.horario);
    showAlert('#alert-global', res.message || 'Horario generado.', 'success');
    const ts = document.getElementById('generated-at');
    if (ts) ts.textContent = 'Generado: ahora';
  } catch (err) {
    showAlert('#alert-global', err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '⚡ Generar Horario';
  }
}

document.addEventListener('DOMContentLoaded', init);
