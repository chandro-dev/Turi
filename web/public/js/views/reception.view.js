/* VISTA: recepcion (registro de pacientes y fila activa). */
import { esc } from '../core/dom.js';
import { greeting, mins, timeOf } from '../core/format.js';
import { ic, initials, SERVICE_ICON } from '../core/icons.js';
import { MAX_AGE } from '../models/rules.js';
import { emptyState, prioBadge, statusBadge } from './components.js';
import { headView } from './layout.js';

export const receptionView = (user) => `
  ${headView(`${greeting()}, ${esc(user.name.split(' ')[0])}`, 'Registra la llegada y deja que la IA sugiera el mejor punto.')}
  <div class="grid-2">
    <section class="card" id="form-card">
      <div class="card-head"><h2><span class="ic">${ic('plus')}</span>Nuevo ingreso</h2></div>
      <form id="nf" autocomplete="off">
        <div class="step"><i>1</i>Datos del paciente<span class="line"></span></div>
        <div class="row">
          <div class="field"><label>Documento</label><input type="text" id="doc" inputmode="numeric" placeholder="1.065.000.000" required></div>
          <div class="field" style="max-width:110px"><label>Edad</label><input type="number" id="age" min="0" max="${MAX_AGE}" required></div>
        </div>
        <div class="field"><label>Nombre completo</label><input type="text" id="name" required></div>
        <div class="field"><label>Telefono (opcional)</label><input type="text" id="phone"></div>
        <div class="field"><label>Condiciones de prioridad</label>
          <div class="chips">
            <span class="chip-toggle" data-flag="pregnant" id="chip-pregnant">${ic('star', 'sm')} Gestante</span>
            <span class="chip-toggle" data-flag="disability">${ic('star', 'sm')} Discapacidad</span>
          </div>
          <div class="hint hide" id="preg-hint"></div>
        </div>
        <div class="step" style="margin-top:22px"><i>2</i>Servicio<span class="line"></span></div>
        <div class="service-tiles" id="tiles" style="margin-bottom:20px"></div>
        <div id="sugg"></div>
        <button class="btn big" style="width:100%" id="submit" disabled>${ic('ticket')} Generar turno</button>
      </form>
    </section>
    <section class="card">
      <div class="card-head"><h2><span class="ic">${ic('users')}</span>Fila en tiempo real</h2><div class="tabs" id="tabs"></div></div>
      <div id="queue"></div>
    </section>
  </div>`;

export const tilesView = (services, selected) => services.map((s) => `
  <button type="button" class="tile ${selected === s.code ? 'on' : ''}" data-c="${s.code}" style="--tile:${s.color}">
    <div class="tic">${ic(SERVICE_ICON[s.code] || 'activity')}</div>
    <div><b>${esc(s.name)}</b><small>~${s.prior_minutes} min por paciente</small></div></button>`).join('');

export const suggestionView = (r, selectedPoint) => {
  let html = '';
  const pref = r.priority_class === 'PREFERENCIAL';
  if (pref) {
    html += `<div class="notice prio">${ic('star')}<div><b>Atencion preferencial: ${esc(r.priority_reasons.join(' · '))}</b>
      <span>El modelo adelanta su turno para que espere como maximo ${r.policy.target_wait_min} min, si la fila lo permite.</span></div></div>`;
  }
  if (!r.options.length) return html + `<div class="notice">${ic('alert')} No hay puntos disponibles para este servicio.</div>`;
  const max = Math.max(1, ...r.options.map((o) => o.est_wait_min));
  return html + `<div class="ai-box"><div class="ai-title">${ic('spark')} Sugerencia de IA<small>${r.model === 'respaldo-basico' ? 'estimacion basica' : 'aprende de cada atencion'}</small></div>
    <div class="options">${r.options.map((o) => `
      <div class="opt ${o.point_id === selectedPoint ? 'on' : ''}" data-p="${o.point_id}">
        <div class="nm"><b>${esc(o.name)}</b> ${o.recommended ? `<span class="badge b-ai">${ic('spark', 'sm')} Recomendado</span>` : ''}</div>
        <div class="eta"><b>${Math.round(o.est_wait_min)}</b><small>min</small></div>
        <div class="meta">${esc(o.reason)}</div>
        ${pref ? `<div class="prio-line">${ic('star', 'sm')} Adelanto +${Math.round(o.bonus_min)} min${o.saved_min > 0 ? ` · ahorra ${Math.round(o.saved_min)} min` : ''}
          <span class="badge ${o.meets_target ? 'b-IN_SERVICE' : 'b-CALLED'} nodot">${o.meets_target ? 'Cumple meta' : 'Supera la meta de ' + r.policy.target_wait_min + ' min'}</span></div>` : ''}
        <div class="meter"><i style="width:${Math.max(6, (o.est_wait_min / max) * 100)}%"></i></div>
      </div>`).join('')}</div></div>`;
};

export const ageNoticeView = (service) => (service
  ? '<div class="notice info">Ingresa la edad para calcular la prioridad y sugerir un punto.</div>' : '');

export const tabsView = (points, filter) =>
  [{ id: 'all', name: 'Todos' }, ...points.map((p) => ({ id: String(p.id), name: p.name }))]
    .map((t) => `<button class="tab ${filter === t.id ? 'on' : ''}" data-f="${t.id}">${esc(t.name)}</button>`).join('');

export const queueRowsView = (list) => {
  if (!list.length) return emptyState('coffee', 'Sin turnos activos', 'Todo al dia por ahora.');
  return `<div class="tlist">${list.map((t) => `
    <div class="titem ${t.status === 'IN_SERVICE' ? 'live' : t.priority_class === 'PREFERENCIAL' ? 'hot' : ''}" data-id="${t.id}" style="--sc:${t.service.color}">
      <div class="avatar sm" style="--av:${t.service.color}">${esc(initials(t.patient_name))}</div>
      <div class="code">${esc(t.code)}</div>
      <div class="who"><b>${esc(t.patient_name)}</b><span>${esc(t.service.name)} · ${esc(t.point.name)}</span>
        <div class="tags">${statusBadge(t.status)} ${prioBadge(t)}</div></div>
      <div class="pos">${t.status === 'WAITING'
        ? `<b>#${t.position}</b><small>${t.eta_min < 1 ? 'siguiente' : '~' + mins(t.eta_min)}</small>`
        : `<small>${t.status === 'NO_SHOW' ? 'por reingresar' : 'desde ' + timeOf(t.called_at)}</small>`}</div>
      ${['WAITING', 'NO_SHOW', 'CALLED'].includes(t.status) ? `<div class="acts">
        ${t.status === 'NO_SHOW' ? `<button class="btn sm amber" data-a="reassign">${ic('undo', 'sm')} Reincorporar</button>` : ''}
        ${t.status === 'WAITING' ? `<button class="btn sm soft" data-a="reassign">${ic('swap', 'sm')} Reasignar</button><button class="btn sm ghost" data-a="edit">${ic('edit', 'sm')} Editar</button>` : ''}
        <button class="btn sm danger" data-a="cancel">${ic('x', 'sm')} Cancelar</button>
      </div>` : ''}
    </div>`).join('')}</div>`;
};

export const ticketModalView = (t) => `
  <div class="top">
    <div style="font-weight:800;letter-spacing:.18em;font-size:13px;opacity:.85">TURNO ASIGNADO</div>
    <div class="big-code">${esc(t.code)}</div>
    <div style="font-size:19px;font-weight:700">${esc(t.patient_name)}</div>
    <div style="opacity:.85">${esc(t.service.name)}${t.priority_class === 'PREFERENCIAL' ? ' · ★ Preferencial' : ''}</div>
    ${t.priority_class === 'PREFERENCIAL' && t.bonus_min ? `<div class="ticket-prio">★ Prioridad aplicada: adelanto de ${Math.round(t.bonus_min)} min</div>` : ''}
  </div>
  <div class="bottom">
    <div class="line">
      <div><b>${esc(t.point.name)}</b><small>Punto</small></div>
      <div><b>#${t.position ?? '-'}</b><small>En la fila</small></div>
      <div><b>${mins(t.eta_min)}</b><small>Espera aprox.</small></div>
    </div>
    <button class="btn big" id="ok" style="width:100%">Listo, siguiente paciente</button>
  </div>`;

export const reassignModalView = (t, points) => {
  const requeue = t.status === 'NO_SHOW';
  return `<h2>${requeue ? 'Reincorporar' : 'Reasignar'} ${esc(t.code)}</h2>
    <p class="muted" style="margin-bottom:14px">${requeue ? 'El paciente vuelve a la fila con prioridad baja.' : 'Elige el nuevo punto de atencion.'}</p>
    <div class="options">${points.map((p) => `<div class="opt ${p.id === t.point.id ? 'on' : ''}" data-p="${p.id}">
      <div class="nm"><b>${esc(p.name)}</b></div><div class="eta"><b>${p.waiting}</b><small>en fila</small></div>
      <div class="meta">${p.active ? 'Disponible' : 'En pausa'}</div></div>`).join('')}</div>
    <div class="foot"><button class="btn ghost" id="cx">Cancelar</button></div>`;
};

export const editModalView = (t) => `<h2>Editar ${esc(t.code)}</h2>
  <div class="field"><label>Nombre</label><input type="text" id="en" value="${esc(t.patient_name)}"></div>
  <div class="row"><div class="field"><label>Documento</label><input type="text" id="ed" value="${esc(t.doc_number)}"></div>
  <div class="field"><label>Edad</label><input type="number" id="ea" value="${t.age}" min="0" max="${MAX_AGE}"></div></div>
  <div class="field"><label>Telefono</label><input type="text" id="ep" value="${esc(t.phone || '')}"></div>
  <div class="chips"><span class="chip-toggle ${t.pregnant ? 'on' : ''}" data-f="pregnant">Gestante</span>
  <span class="chip-toggle ${t.disability ? 'on' : ''}" data-f="disability">Discapacidad</span></div>
  <div class="hint hide" id="e-hint"></div>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">Guardar</button></div>`;

export const cancelModalView = (t) => `<h2>Cancelar ${esc(t.code)}</h2>
  <p>Se retirara a <b>${esc(t.patient_name)}</b> de la fila. Esta accion no se puede deshacer.</p>
  <div class="foot"><button class="btn ghost" id="cx">Volver</button><button class="btn danger" id="yes">Cancelar turno</button></div>`;
