/* VISTA: consultorio / punto de atencion. */
import { esc } from '../core/dom.js';
import { mins } from '../core/format.js';
import { ic } from '../core/icons.js';
import { emptyState, prioBadge } from './components.js';
import { headView } from './layout.js';

const stageView = (d) => {
  const cur = d.current;
  if (cur) {
    const calling = cur.status === 'CALLED';
    return `<div class="hero">
      <div class="eyebrow">${calling ? 'LLAMANDO AL PACIENTE' : 'EN ATENCION'}</div>
      <div class="big-code ${calling ? 'ring' : ''}">${esc(cur.code)}</div>
      <div class="pname">${esc(cur.patient_name)}</div>
      <div class="psub">${esc(cur.service.name)} · ${cur.age} anos · Doc. ${esc(cur.doc_number)}</div>
      <div class="tags">${cur.priority_class === 'PREFERENCIAL' ? cur.priority_reasons.map((r) => `<span class="badge nodot">${ic('star', 'sm')} ${esc(r)}</span>`).join('') : ''}${cur.priority_class === 'BAJA' ? '<span class="badge nodot">Reincorporado</span>' : ''}</div>
      <div class="actions">
        ${calling ? `
          <button class="btn big white" data-p="/doctor/turns/${cur.id}/start">${ic('play')} Iniciar atencion</button>
          <button class="btn big glass" data-p="/doctor/turns/${cur.id}/recall">${ic('bell')} Llamar de nuevo</button>
          <button class="btn big glass red" data-p="/doctor/turns/${cur.id}/no-show">${ic('x')} No se presento</button>` : `
          <button class="btn big white" data-p="/doctor/turns/${cur.id}/finish">${ic('check')} Finalizar atencion</button>`}
      </div></div>`;
  }
  const first = d.queue[0];
  return `<div class="hero ${d.point.active ? 'idle' : 'paused'}">
    <div class="eyebrow">${d.point.active ? 'LISTO PARA ATENDER' : 'PUNTO EN PAUSA'}</div>
    <div class="count" style="margin:16px 0 4px">${d.queue.length}</div>
    <div class="pname">${d.queue.length === 1 ? 'paciente en espera' : 'pacientes en espera'}</div>
    ${first ? `<div class="psub">Siguiente: <b>${esc(first.code)}</b> · ${esc(first.patient_name)} ${first.priority_class === 'PREFERENCIAL' ? '★' : ''}</div>` : '<div class="psub">Nadie esperando por ahora</div>'}
    <div class="actions"><button class="btn big white" data-p="/doctor/call-next" ${d.queue.length ? '' : 'disabled'}>${ic('bell')} Llamar siguiente</button></div></div>`;
};

const upcomingView = (d) => (d.queue.length
  ? `<div class="tlist">${d.queue.slice(0, 8).map((t) => `
    <div class="titem ${t.priority_class === 'PREFERENCIAL' ? 'hot' : ''}" style="--sc:${t.service.color};grid-template-columns:auto 1fr auto">
      <div class="code">${esc(t.code)}</div>
      <div class="who"><b>${esc(t.patient_name)}</b><span>${esc(t.service.name)}</span>${t.priority_class === 'PREFERENCIAL' ? `<div class="tags">${prioBadge(t)}</div>` : ''}</div>
      <div class="pos"><b>#${t.position}</b><small>${t.eta_min < 1 ? 'siguiente' : '~' + mins(t.eta_min)}</small></div></div>`).join('')}</div>`
  : emptyState('coffee', 'Fila vacia', 'Buen momento para un cafe.'));

export const doctorView = (d) => `
  ${headView(esc(d.point.name), esc(d.point.services.join(', ')),
    `<label class="switch"><input type="checkbox" id="act" ${d.point.active ? 'checked' : ''}><i></i><span>${d.point.active ? 'Disponible' : 'En pausa'}</span></label>`)}
  <div class="grid-2" style="grid-template-columns:1.25fr 1fr">
    <section>${stageView(d)}
      <div class="mini-stats"><div><b>${d.done_today}</b><span>Atendidos hoy</span></div><div><b>${d.queue.length}</b><span>En espera</span></div><div><b>${d.no_shows.length}</b><span>No presentados</span></div></div>
    </section>
    <section class="card">
      <div class="card-head"><h2><span class="ic">${ic('users')}</span>Proximos pacientes</h2></div>
      ${upcomingView(d)}
      ${d.no_shows.length ? `<div class="notice info" style="margin:16px 0 0">No se presentaron: ${d.no_shows.map((t) => esc(t.code)).join(', ')}. Recepcion puede reincorporarlos.</div>` : ''}
    </section>
  </div>`;
