let chart = null;

const DIAS       = ['lunes','martes','miercoles','jueves','viernes','sabado'];
const DIAS_LABEL = { lunes:'Lunes', martes:'Martes', miercoles:'Miércoles',
                     jueves:'Jueves', viernes:'Viernes', sabado:'Sábado' };

document.addEventListener('DOMContentLoaded', async () => {
  const user = await requireSession();
  if (!user) return;
  setUserChip(user);

  await checkPerfil();
  await cargarHorario();

  document.getElementById('btn-generar').addEventListener('click', generarHorario);
});

async function checkPerfil() {
  const msgBox = document.getElementById('msg-prereq');
  try {
    const res = await api.get('/perfil');
    if (!res.perfil) {
      msgBox.innerHTML = `
        <div class="alert alert-warning">
          Primero configura tu perfil académico para que el sistema conozca tu carrera y semestre.
          <br><a href="/perfil/index.html" class="btn btn-primary btn-sm" style="margin-top:.5rem">
            Ir a Perfil Académico
          </a>
        </div>`;
      document.getElementById('btn-generar').disabled = true;
      return;
    }
    // Verificar materias
    const mats = await api.get('/materias');
    if (!mats.length) {
      msgBox.innerHTML = `
        <div class="alert alert-warning">
          No tienes materias registradas. Sincroniza desde tu perfil académico.
          <br><a href="/perfil/index.html" class="btn btn-primary btn-sm" style="margin-top:.5rem">
            Ir a Perfil
          </a>
        </div>`;
      document.getElementById('btn-generar').disabled = true;
      return;
    }
    msgBox.innerHTML = `
      <div class="alert alert-info">
        Perfil: <strong>${escHtml(res.perfil.carrera)}</strong>
        — Semestre ${escHtml(String(res.perfil.semestre))}
        — ${mats.length} materias
      </div>`;
  } catch (_) {}
}

async function cargarHorario() {
  try {
    const res = await api.get('/horario');
    if (res.horario) {
      mostrarFecha(res.generado_at);
      renderGrid(res.horario);
      renderResumen(res.horario.resumen);
      renderChart(res.horario);
    } else {
      document.getElementById('horario-container').innerHTML =
        '<p style="color:#64748b;text-align:center;padding:2rem">Aún no has generado tu horario. Presiona el botón de arriba.</p>';
    }
  } catch (err) {
    showAlert('#alert-global', err.message, 'error');
  }
}

async function generarHorario() {
  const btn = document.getElementById('btn-generar');
  btn.textContent = 'Generando…';
  btn.disabled = true;
  try {
    const res = await api.post('/horario/generar', {});
    mostrarFecha(res.generado_at);
    renderGrid(res.horario);
    renderResumen(res.horario.resumen);
    renderChart(res.horario);
    showAlert('#alert-global', '✓ Horario generado correctamente', 'success');
  } catch (err) {
    showAlert('#alert-global', err.message, 'error');
  } finally {
    btn.textContent = '🔄 Generar mi horario de estudio';
    btn.disabled = false;
  }
}

function mostrarFecha(ts) {
  const el = document.getElementById('generado-at');
  if (el && ts) el.textContent = 'Generado: ' + new Date(ts).toLocaleString('es-BO');
}

// ── Tabla semanal ─────────────────────────────────────────────────────────────

function renderGrid(horario) {
  const container = document.getElementById('horario-container');
  const horas = horario.dias['lunes']?.map(s => s.hora) || [];

  let html = '<div class="horario-tabla-wrap"><table class="horario-tabla">';

  // Encabezado
  html += '<thead><tr><th class="hora-col">Hora</th>';
  DIAS.forEach(d => { html += `<th>${escHtml(DIAS_LABEL[d])}</th>`; });
  html += '</tr></thead><tbody>';

  // Filas de horas
  horas.forEach(hora => {
    html += `<tr><td class="hora-col">${escHtml(hora)}</td>`;
    DIAS.forEach(dia => {
      const slots = horario.dias[dia] || [];
      const slot  = slots.find(s => s.hora === hora) || { tipo: 'libre' };
      html += renderSlot(slot);
    });
    html += '</tr>';
  });

  html += '</tbody></table></div>';
  container.innerHTML = html;
}

function renderSlot(slot) {
  if (slot.tipo === 'clase') {
    const secDisplay = slot.seccion_lab
      ? `${slot.seccion || ''} + ${slot.seccion_lab}`
      : (slot.seccion || slot.aula || '');
    const detalle = [secDisplay, slot.profesor].filter(Boolean).join(' · ');
    return `<td class="slot-clase" title="${escHtml(slot.nombre)}${detalle ? ' — ' + detalle : ''}">
      <div class="slot-inner">
        <strong>${escHtml(slot.codigo)}</strong>
        <small>${escHtml(secDisplay)}</small>
      </div>
    </td>`;
  }
  if (slot.tipo === 'estudio') {
    const bg = slot.color || '#3182ce';
    const fg = lightColor(bg) ? '#1a202c' : '#fff';
    return `<td class="slot-estudio" style="background:${bg};color:${fg}"
                title="Estudiar: ${escHtml(slot.nombre)}">
      <div class="slot-inner">
        <small>${escHtml(slot.nombre)}</small>
      </div>
    </td>`;
  }
  return '<td class="slot-libre"></td>';
}

function lightColor(hex) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 128;
}

// ── Resumen ───────────────────────────────────────────────────────────────────

function renderResumen(resumen) {
  const box = document.getElementById('resumen-box');
  const items = Object.entries(resumen);
  if (!items.length) { box.innerHTML = ''; return; }

  box.innerHTML = `
    <h3 style="margin-bottom:.75rem">Horas de estudio esta semana</h3>
    ${items.map(([cod, info]) => `
      <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem">
        <span style="width:14px;height:14px;border-radius:3px;background:${escHtml(info.color)};
                     display:inline-block;flex-shrink:0"></span>
        <span style="flex:1;font-size:.9rem">${escHtml(info.nombre)}</span>
        <strong>${info.horas_asignadas}h</strong>
      </div>`).join('')}`;
}

// ── Chart.js ──────────────────────────────────────────────────────────────────

function renderChart(horario) {
  const canvas = document.getElementById('chart-horas');
  if (!canvas) return;

  const resumen = horario.resumen;
  const labels  = Object.values(resumen).map(v => v.nombre);
  const values  = Object.values(resumen).map(v => v.horas_asignadas);
  const colors  = Object.values(resumen).map(v => v.color || '#3182ce');

  if (chart) chart.destroy();
  chart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Horas de estudio',
        data: values,
        backgroundColor: colors,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
        x: { ticks: { maxRotation: 30 } },
      },
    },
  });
}
