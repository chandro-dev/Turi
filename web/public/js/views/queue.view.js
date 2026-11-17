/* VISTA: fila general del supervisor (turnos activos y atendidos, con tiempos). */
import { esc } from '../core/dom.js';
import { dur, timeOf } from '../core/format.js';
import { ic, initials } from '../core/icons.js';
import { emptyState, prioBadge, statusBadge } from './components.js';
import { headView } from './layout.js';

export const STATUS_FILTERS = [
  ['ALL', 'Todos'], ['ACTIVE', 'Activos'], ['DONE', 'Atendidos'], ['NO_SHOW', 'No presentados'], ['CANCELLED', 'Cancelados'],
];

export const queueShell = () => `
  ${headView('Fila general', 'Todos los turnos del dia: en curso, atendidos y cerrados.')}
  <div id="qsum"></div>
  <section class="card">
    <div class="card-head"><h2><span class="ic">${ic('list')}</span>Turnos del dia</h2><div class="tabs" id="qstatus"></div></div>
    <div class="tabs" id="qpoints" style="margin-bottom:16px;display:inline-flex"></div>
    <div id="qlist"></div>
  </section>`;

export const summaryView = ({ total, done, active, avgService, avgWait }) => `
  <div class="kpis" style="margin-bottom:20px">
    <div class="kpi" style="--kc:#0d9488"><div class="kic">${ic('ticket')}</div><small>Turnos hoy</small><b>${total}</b><span>${active} activos</span></div>
    <div class="kpi" style="--kc:#16a34a"><div class="kic">${ic('check')}</div><small>Atendidos</small><b>${done}</b><span>atencion finalizada</span></div>
    <div class="kpi" style="--kc:#4f46e5"><div class="kic">${ic('activity')}</div><small>Tiempo de atencion</small><b>${avgService ?? '-'} <em>min</em></b><span>promedio de los atendidos</span></div>
    <div class="kpi" style="--kc:#f59e0b"><div class="kic">${ic('clock')}</div><small>Espera promedio</small><b>${avgWait ?? '-'} <em>min</em></b><span>llegada hasta ser llamado</span></div>
  </div>`;

export const chipsView = (items, current) =>
  items.map(([id, name, n]) => `<button class="tab ${current === id ? 'on' : ''}" data-f="${id}">${esc(name)}${n != null ? ` <span class="muted">${n}</span>` : ''}</button>`).join('');

const timesView = (t) => {
  if (t.status === 'DONE') {
    return `<div class="pos"><b>${dur(t.duration_min)}</b><small>de atencion</small></div>`;
  }
  if (t.status === 'WAITING') return `<div class="pos"><b>#${t.position}</b><small>${t.eta_min < 1 ? 'siguiente' : '~' + t.eta_min + ' min'}</small></div>`;
  if (t.status === 'CALLED' || t.status === 'IN_SERVICE') return `<div class="pos"><small>desde ${timeOf(t.called_at)}</small></div>`;
  return '<div class="pos"><small>-</small></div>';
};

const detailView = (t) => {
  const parts = [`${esc(t.service.name)} · ${esc(t.point.name)}`];
  if (t.status === 'DONE') {
    parts.push(`Llegada ${timeOf(t.created_at)} · esperó ${dur(t.wait_min)} · atendido ${timeOf(t.started_at)}–${timeOf(t.finished_at)}`);
  } else if (t.wait_min != null) {
    parts.push(`Esperó ${dur(t.wait_min)}`);
  } else {
    parts.push(`Llegada ${timeOf(t.created_at)}`);
  }
  return parts.map((p) => `<span>${p}</span>`).join('');
};

export const queueListView = (turns) => {
  if (!turns.length) return emptyState('list', 'Sin turnos', 'No hay turnos con este filtro.');
  return `<div class="tlist">${turns.map((t) => `
    <div class="titem ${t.status === 'IN_SERVICE' ? 'live' : t.status === 'DONE' ? 'done' : t.priority_class === 'PREFERENCIAL' ? 'hot' : ''}" style="--sc:${t.service.color}">
      <div class="avatar sm" style="--av:${t.service.color}">${esc(initials(t.patient_name))}</div>
      <div class="code">${esc(t.code)}</div>
      <div class="who"><b>${esc(t.patient_name)}</b><div class="detail">${detailView(t)}</div>
        <div class="tags">${statusBadge(t.status)} ${prioBadge(t)}</div></div>
      ${timesView(t)}
    </div>`).join('')}</div>`;
};
