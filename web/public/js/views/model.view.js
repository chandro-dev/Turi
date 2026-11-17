/* VISTA: prueba del modelo de IA (entrenamiento, efectividad y consultas). */
import { esc } from '../core/dom.js';
import { fmtMin } from '../core/format.js';
import { ic } from '../core/icons.js';
import { emptyState } from './components.js';
import { headView } from './layout.js';

const num = (v, d = 1) => (v == null ? '-' : Number(v).toFixed(d).replace(/\.0+$/, ''));
const GROUP = { normal: 'Normal', pref: 'Preferencial' };

export const modelShell = (services) => `
  ${headView('Prueba del modelo', 'Como aprende la IA, que tan bien acierta y que responde ante una consulta.',
    `<button class="btn ghost" id="refresh">${ic('undo')} Actualizar</button>`)}
  <div id="mreport"></div>
  <section class="card" style="margin-top:24px">
    <div class="card-head"><h2><span class="ic">${ic('spark')}</span>Preguntale al modelo</h2></div>
    <form id="pf" class="predict-form">
      <div class="field"><label>Servicio</label>
        <select id="p-service">${services.map((s) => `<option value="${esc(s.code)}">${esc(s.name)}</option>`).join('')}</select></div>
      <div class="field"><label>Tipo de paciente</label>
        <div class="chips"><span class="chip-toggle on" data-pref="0">Normal</span><span class="chip-toggle" data-pref="1">${ic('star', 'sm')} Preferencial</span></div></div>
      <button class="btn" id="ask">${ic('spark')} Consultar</button>
    </form>
    <div id="panswer"></div>
  </section>`;

// ---------------------------------------------------------------- efectividad
const VERDICT_ICON = { good: 'check', fair: 'trend', poor: 'alert', insufficient: 'info' };

const kpi = (icon, color, label, val, unit, note) =>
  `<div class="kpi" style="--kc:${color}"><div class="kic">${ic(icon)}</div><small>${label}</small><b>${val}${unit ? ` <em>${unit}</em>` : ''}</b><span>${note}</span></div>`;

/** Curva de aprendizaje: error medio movil del modelo frente a la estimacion base (sin aprender). */
export function curveChart(curve) {
  if (curve.length < 2) return emptyState('chart', 'Aun sin curva', 'Se dibuja cuando haya al menos 10 atenciones aprendidas.');
  const W = 640; const H = 210; const L = 38; const B = 26; const T = 10; const R = 10;
  const maxY = Math.max(1, ...curve.flatMap((c) => [c.mae, c.baseline ?? 0])) * 1.1;
  const x = (i) => L + ((i - curve[0].i) / Math.max(1, curve[curve.length - 1].i - curve[0].i)) * (W - L - R);
  const y = (v) => T + (1 - v / maxY) * (H - T - B);
  const path = (key) => curve.filter((c) => c[key] != null).map((c, k) => `${k ? 'L' : 'M'}${x(c.i).toFixed(1)},${y(c[key]).toFixed(1)}`).join(' ');
  const ticks = [0, 0.5, 1].map((f) => maxY * f);
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Curva de aprendizaje">
    ${ticks.map((t) => `<line x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}" class="grid"/><text x="${L - 6}" y="${y(t) + 4}" class="ax" text-anchor="end">${t.toFixed(1)}</text>`).join('')}
    <text x="${L}" y="${H - 6}" class="ax">atencion ${curve[0].i}</text>
    <text x="${W - R}" y="${H - 6}" class="ax" text-anchor="end">atencion ${curve[curve.length - 1].i}</text>
    <path d="${path('baseline')}" class="l-base"/>
    <path d="${path('mae')}" class="l-model"/>
  </svg>
  <div class="legend-inline"><span><i class="sw model"></i>Modelo (error medio, min)</span><span><i class="sw base"></i>Estimacion base sin aprender</span></div>`;
}

const maturityBar = (pct) => `<div class="hbar" title="${pct}% de madurez"><i style="width:${pct}%;background:${pct >= 100 ? '#16a34a' : pct >= 50 ? '#0ea5e9' : '#f59e0b'}"></i></div>`;

export const reportView = (r) => {
  const v = r.verdict;
  const improv = r.improvement_pct;
  return `
    <div class="verdict v-${v.level}">${ic(VERDICT_ICON[v.level])}<div><b>${esc(v.text)}</b>
      <span>Politica de prioridad vigente: meta de espera ≤ ${fmtMin(r.policy.target_wait_min)}, adelanto de ${fmtMin(r.policy.base_bonus_min)} a ${fmtMin(r.policy.max_bonus_min)} segun lo decida el modelo.</span></div></div>
    <div class="kpis">
      ${kpi('activity', '#0d9488', 'Atenciones aprendidas', r.samples, '', 'muestras de entrenamiento')}
      ${kpi('clock', '#4f46e5', 'Error del modelo', fmtMin(r.mae, 1), '', 'error medio absoluto')}
      ${kpi('alert', '#94a3b8', 'Error sin IA', fmtMin(r.mae_baseline, 1), '', 'solo valor inicial')}
      ${kpi('trend', '#16a34a', 'Mejora', improv == null ? '-' : `${improv > 0 ? '+' : ''}${num(improv, 0)}`, '%', 'frente a no aprender')}
      ${kpi('check', '#0ea5e9', 'Aciertos ±3 min', num(r.within_3min_pct, 0), '%', 'prediccion cercana')}
    </div>
    <div class="grid-2 stretch" style="grid-template-columns:1.6fr 1fr;margin-bottom:24px">
      <section class="card"><div class="card-head"><h2><span class="ic">${ic('trend')}</span>Curva de aprendizaje</h2></div>
        ${curveChart(r.curve)}
        ${r.mae_early != null && r.samples >= 40 ? `<div class="notice info" style="margin-top:14px">Error de las primeras 20 atenciones: <b>${fmtMin(r.mae_early, 1)}</b> · de las ultimas 20: <b>${fmtMin(r.mae_recent, 1)}</b>.</div>` : ''}
      </section>
      <section class="card"><div class="card-head"><h2><span class="ic">${ic('steth')}</span>Efectividad por servicio</h2></div>
        ${r.by_service.length ? `<div class="vs">${r.by_service.map((s) => `
          <div><div style="display:flex;justify-content:space-between"><b>${esc(s.name)}</b><span class="muted">${s.samples} atenciones</span></div>
          <div class="eff"><span>Modelo ${fmtMin(s.mae, 1)}</span><span class="muted">base ${fmtMin(s.mae_baseline, 1)}</span>
          ${s.improvement_pct != null ? `<span class="badge ${s.improvement_pct >= 0 ? 'b-IN_SERVICE' : 'b-CANCELLED'} nodot">${s.improvement_pct > 0 ? '+' : ''}${num(s.improvement_pct, 0)}%</span>` : ''}</div></div>`).join('')}</div>`
          : emptyState('list', 'Sin datos', 'Aparece al finalizar atenciones.')}
      </section>
    </div>
    <section class="card"><div class="card-head"><h2><span class="ic">${ic('list')}</span>Estado del entrenamiento por punto</h2>
      <span class="muted">Madurez = muestras / ${r.mature_samples}</span></div>
      ${r.cells.length ? `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Servicio</th><th>Punto</th><th>Paciente</th><th>Muestras</th><th>Valor inicial</th><th>Aprendido</th><th>Estimacion</th><th style="min-width:120px">Madurez</th></tr></thead><tbody>
        ${r.cells.map((c) => `<tr><td>${esc(c.service_name)}</td><td><b>${esc(c.point_name)}</b></td><td>${GROUP[c.group] || c.group}</td><td>${c.samples}</td>
          <td>${fmtMin(c.prior_min, 1)}</td><td>${fmtMin(c.mean_min, 1)}</td><td><b>${fmtMin(c.estimate_min, 1)}</b></td><td>${maturityBar(c.maturity_pct)}</td></tr>`).join('')}
      </tbody></table></div>` : emptyState('activity', 'Sin entrenamiento', 'El modelo empieza a aprender con la primera atencion finalizada.')}
    </section>`;
};

// ---------------------------------------------------------------- respuesta
const rangeBar = (low, high, minutes, max) => `<div class="range"><i style="left:${(low / max) * 100}%;width:${Math.max(2, ((high - low) / max) * 100)}%"></i><b style="left:${(minutes / max) * 100}%"></b></div>`;

export const answerView = (a) => {
  const max = Math.max(1, ...a.points.map((p) => p.high)) * 1.05;
  const best = a.points.find((p) => p.recommended) || a.points[0];
  return `
    <div class="answer">${ic('spark')}<p>${esc(a.answer)}</p></div>
    ${a.model === 'respaldo-basico' ? '<div class="notice info">El servicio de IA no respondio: se uso la estimacion basica.</div>' : ''}
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Punto</th><th>Duracion estimada</th><th>Rango probable</th><th>Confianza</th><th>Espera ahora</th>${a.preferential ? '<th>Prioridad</th>' : ''}</tr></thead><tbody>
      ${a.points.map((p) => `<tr class="${p.recommended ? 'rec' : ''}">
        <td><b>${esc(p.name)}</b> ${p.recommended ? `<span class="badge b-ai">${ic('spark', 'sm')} Recomendado</span>` : ''}${p.active ? '' : ' <span class="badge b-low">En pausa</span>'}</td>
        <td><b>${fmtMin(p.minutes, 1)}</b></td>
        <td style="min-width:150px">${rangeBar(p.low, p.high, p.minutes, max)}<small class="muted">${fmtMin(p.low, 1)} – ${fmtMin(p.high, 1)}</small></td>
        <td>${p.confidence_pct}% <small class="muted">(${p.samples} muestras)</small></td>
        <td>${p.est_wait_min == null ? '-' : `<b>${fmtMin(p.est_wait_min)}</b>`}</td>
        ${a.preferential ? `<td>${p.est_wait_min == null ? '-' : `+${fmtMin(p.bonus_min)} adelanto · ahorra ${fmtMin(p.saved_min)} ${p.meets_target ? '<span class="badge b-IN_SERVICE nodot">Cumple meta</span>' : '<span class="badge b-CALLED nodot">No cumple meta</span>'}`}</td>` : ''}
      </tr>`).join('')}
    </tbody></table></div>
    ${best ? `<details class="how"><summary>Como calculo la duracion en ${esc(best.name)}</summary>
      <ol>${best.levels.map((l) => `<li><b>${esc(l.label)}</b>: ${l.samples ? `${l.samples} muestras, media ${fmtMin(l.mean, 1)}` : fmtMin(l.mean, 1)} <span class="muted">→ estimacion ${fmtMin(l.estimate, 1)}</span></li>`).join('')}</ol>
      <p class="muted">Cada nivel mezcla su media con la del nivel anterior segun cuantas muestras tiene: con pocas confia en lo general, con muchas confia en lo propio del punto.</p></details>` : ''}`;
};
