/* VISTA: indicadores del supervisor. */
import { esc } from '../core/dom.js';
import { fmtMin } from '../core/format.js';
import { ic } from '../core/icons.js';
import { STATUS, STATUS_COLOR } from '../models/constants.js';
import { headView } from './layout.js';

export const supervisorShell = () => `${headView('Indicadores del dia', 'Panorama en tiempo real de la operacion.',
  `<button class="btn" id="sim">${ic('plus')} Simular llegadas</button>`)}<div id="sv"></div>`;

const kpi = (icon, color, label, val, unit, note) =>
  `<div class="kpi" style="--kc:${color}"><div class="kic">${ic(icon)}</div><small>${label}</small><b>${val}${unit ? ` <em>${unit}</em>` : ''}</b><span>${note}</span></div>`;

const ORDER = ['WAITING', 'CALLED', 'IN_SERVICE', 'DONE', 'NO_SHOW', 'CANCELLED'];

export const statsView = (s) => {
  const max = Math.max(1, ...s.hourly.map((h) => h.count));
  const by = s.by_status;
  let acc = 0;
  const stops = s.total
    ? ORDER.map((k) => { const a = acc; acc += ((by[k] || 0) / s.total) * 100; return `${STATUS_COLOR[k]} ${a}% ${acc}%`; }).join(',')
    : '#e6eef5 0 100%';
  const pw = s.priority.avg_wait_min;
  const nw = s.priority.avg_wait_normal_min;
  const wmax = Math.max(1, pw || 0, nw || 0);

  const points = s.per_point.map((p) => {
    const pct = Math.min(100, (p.waiting / 6) * 100);
    const state = !p.active ? '<span class="badge b-low">En pausa</span>'
      : p.in_attention ? '<span class="badge b-IN_SERVICE">Atendiendo</span>' : '<span class="badge b-WAITING">Libre</span>';
    return `<div class="pcard"><div class="top"><b>${esc(p.name)}</b>${state}</div>
      <div class="num">${p.waiting}</div><small>en espera</small>
      <div class="load"><i style="width:${pct}%;background:${pct > 70 ? '#e11d48' : pct > 40 ? '#f59e0b' : '#14b8a6'}"></i></div>
      <small>${p.done} atendidos · prom. ${fmtMin(p.avg_service_min, 1)}</small></div>`;
  }).join('');

  return `
    <div class="kpis">
      ${kpi('ticket', '#0d9488', 'Turnos hoy', s.total, '', `${by.DONE || 0} atendidos`)}
      ${kpi('users', '#0ea5e9', 'En espera', by.WAITING || 0, '', `${(by.CALLED || 0) + (by.IN_SERVICE || 0)} en atencion`)}
      ${kpi('clock', '#f59e0b', 'Espera promedio', fmtMin(s.avg_wait_min, 1), '', 'hasta ser llamado')}
      ${kpi('activity', '#4f46e5', 'Atencion promedio', fmtMin(s.avg_service_min, 1), '', 'duracion real')}
      ${kpi('star', '#d97706', 'Preferenciales', s.priority.total, '', 'adulto mayor, gestante, disc.')}
      ${kpi('alert', '#8b5cf6', 'No se presentaron', s.no_shows_total, '', `${s.reassigned} reasignados`)}
    </div>
    <div class="grid-2 stretch" style="grid-template-columns:1.5fr 1fr;margin-bottom:24px">
      <section class="card"><div class="card-head"><h2><span class="ic">${ic('steth')}</span>Puntos de atencion</h2></div><div class="pcards">${points}</div></section>
      <section class="card"><div class="card-head"><h2><span class="ic">${ic('chart')}</span>Estado de turnos</h2></div>
        <div class="donut-wrap"><div class="donut" data-total="${s.total}" style="background:conic-gradient(${stops})"></div>
        <div class="legend">${ORDER.map((k) => `<div><span class="dot" style="--c:${STATUS_COLOR[k]}"></span>${STATUS[k]}<b>${by[k] || 0}</b></div>`).join('')}</div></div>
      </section>
    </div>
    <div class="grid-2 stretch" style="grid-template-columns:1.5fr 1fr">
      <section class="card"><div class="card-head"><h2><span class="ic">${ic('clock')}</span>Llegadas por hora</h2></div>
        <div class="bars-wrap"><div class="bars">${s.hourly.map((h) => `<div class="bar ${h.count ? 'has' : ''}" style="height:${Math.max(3, (h.count / max) * 100)}%">${h.count ? `<em>${h.count}</em>` : ''}<span>${h.hour}h</span></div>`).join('')}</div></div>
      </section>
      <section class="card"><div class="card-head"><h2><span class="ic">${ic('star')}</span>Prioridad vs. espera</h2></div>
        <div class="vs">
          <div class="r"><span>Preferencial</span><div class="hbar"><i style="width:${((pw || 0) / wmax) * 100}%;background:#f59e0b"></i></div><b>${fmtMin(pw, 1)}</b></div>
          <div class="r"><span>Normal</span><div class="hbar"><i style="width:${((nw || 0) / wmax) * 100}%;background:#0ea5e9"></i></div><b>${fmtMin(nw, 1)}</b></div>
        </div>
        <div class="legend" style="margin-top:20px">${Object.entries(s.priority.reasons).map(([k, v]) => `<div>${ic('star', 'sm')}${esc(k)}<b>${v}</b></div>`).join('') || '<span class="muted">Sin casos prioritarios</span>'}</div>
      </section>
    </div>
    <section class="card" style="margin-top:24px"><div class="card-head"><h2><span class="ic">${ic('trend')}</span>Por servicio</h2></div>
      <div class="vs">${s.per_service.map((x) => `<div class="r" style="grid-template-columns:150px 1fr 70px"><span><span class="dot" style="--c:${x.color}"></span> ${esc(x.name)}</span><div class="hbar"><i style="width:${x.total ? (x.done / x.total) * 100 : 0}%;background:${x.color}"></i></div><b>${x.done}/${x.total}</b></div>`).join('')}</div>
    </section>`;
};
