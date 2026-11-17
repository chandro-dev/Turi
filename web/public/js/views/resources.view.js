/* VISTA: administracion (servicios, consultorios/laboratorios, usuarios y horarios). */
import { esc } from '../core/dom.js';
import { fmtMin } from '../core/format.js';
import { ic, initials, SERVICE_ICON } from '../core/icons.js';
import { POINT_STATUS } from '../models/constants.js';
import { emptyState } from './components.js';
import { headView } from './layout.js';

const DAYS = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'];
const ROLE_LABEL = { RECEPCION: 'Recepcion', MEDICO: 'Atencion', SUPERVISOR: 'Supervision' };
const ROLE_BADGE = { RECEPCION: 'b-WAITING', MEDICO: 'b-IN_SERVICE', SUPERVISOR: 'b-NO_SHOW' };

/** [0,1,2,3,4] -> "Lun-Vie"; [0,2,4] -> "Lun, Mie, Vie". */
export function daysText(days) {
  const d = [...days].sort((a, b) => a - b);
  const runs = [];
  d.forEach((x) => {
    const last = runs[runs.length - 1];
    if (last && x === last[1] + 1) last[1] = x; else runs.push([x, x]);
  });
  return runs.map(([a, b]) => (a === b ? DAYS[a] : b === a + 1 ? `${DAYS[a]}, ${DAYS[b]}` : `${DAYS[a]}-${DAYS[b]}`)).join(', ');
}

const range = (s) => `${s.start}–${s.end}${s.overnight ? ' <em>(+1 dia)</em>' : ''}`;

const statusBadge = (s) => {
  const cls = { open: 'b-IN_SERVICE', paused: 'b-CALLED', off_hours: 'b-WAITING', closed: 'b-CANCELLED' }[s] || 'b-low';
  return `<span class="badge ${cls}">${POINT_STATUS[s] || s}</span>`;
};

export const resourcesShell = () => `
  ${headView('Administracion', 'Servicios, consultorios y laboratorios, usuarios y horarios del personal.',
    `<div class="head-actions">
      <button class="btn" id="new-point">${ic('plus')} Nuevo punto</button>
      <button class="btn soft" id="new-service">${ic('plus')} Nuevo servicio</button>
      <button class="btn soft" id="new-user">${ic('users')} Nuevo usuario</button>
      <button class="btn soft" id="new-shift">${ic('clock')} Asignar horario</button>
    </div>`)}
  <div id="res"></div>`;

const shiftChip = (s, showUser) => `<span class="shift-chip">${ic('clock', 'sm')}<span><b>${daysText(s.weekdays)}</b> ${range(s)}${showUser ? ` · ${esc(s.user_name)}` : ` · ${esc(s.point_name)}`}</span>
  <button class="x" data-del-shift="${s.id}" title="Quitar horario">${ic('x', 'sm')}</button></span>`;

const pointCard = (p) => `
  <div class="rcard ${p.status === 'closed' ? 'closed' : ''}">
    <div class="rtop"><b>${esc(p.name)}</b>${statusBadge(p.status)}</div>
    <div class="chips-mini">${p.services.map((s) => `<span class="svc" style="--c:${s.color}"><i></i>${esc(s.name)}</span>`).join('')}</div>
    <div class="rline">${ic('users', 'sm')} ${p.on_duty.length ? `Atiende ahora: <b>${esc(p.on_duty.join(', '))}</b>` : (p.scheduled ? 'Sin personal en este horario' : '<span class="muted">Sin horarios: siempre disponible</span>')}</div>
    <div class="rline">${ic('ticket', 'sm')} ${p.active_turns} turno(s) activo(s) hoy</div>
    <div class="shifts">${p.shifts.map((s) => shiftChip(s, true)).join('')}</div>
    <div class="acts" style="margin-top:12px">
      <button class="btn sm soft" data-shift-point="${p.id}">${ic('clock', 'sm')} Horario</button>
      <button class="btn sm ghost" data-edit-point="${p.id}">${ic('edit', 'sm')} Editar</button>
      <button class="btn sm ${p.enabled ? 'amber' : 'soft'}" data-toggle-point="${p.id}">${p.enabled ? 'Cerrar' : 'Abrir'}</button>
      <button class="btn sm danger" data-del-point="${p.id}">${ic('x', 'sm')}</button>
    </div>
  </div>`;

const serviceCard = (s) => `
  <div class="rcard">
    <div class="rtop"><span class="svc-ic" style="--c:${s.color}">${ic(SERVICE_ICON[s.code] || 'activity')}</span>
      <div style="flex:1;min-width:0"><b>${esc(s.name)}</b><div class="muted" style="font-size:12.5px">${esc(s.code)} · ~${fmtMin(s.prior_minutes)} por paciente</div></div></div>
    <div class="acts">
      <button class="btn sm ghost" data-edit-service="${s.id}">${ic('edit', 'sm')} Editar</button>
      <button class="btn sm danger" data-del-service="${s.id}">${ic('x', 'sm')}</button>
    </div>
  </div>`;

const userRow = (u) => `
  <div class="titem staff ${u.active ? '' : 'inactive'}" style="--sc:#4f46e5;grid-template-columns:auto 1fr auto">
    <div class="avatar sm" style="--av:linear-gradient(135deg,#14b8a6,#4f46e5)">${esc(initials(u.name))}</div>
    <div class="who"><b>${esc(u.name)} <span class="badge ${ROLE_BADGE[u.role]} nodot">${ROLE_LABEL[u.role]}</span>${u.active ? '' : ' <span class="badge b-low nodot">Desactivado</span>'}</b>
      <span>@${esc(u.username)}${u.role === 'MEDICO' ? ` · ${u.current_point ? `atendiendo <b>${esc(u.current_point)}</b>` : (u.shifts.length ? 'fuera de turno' : (u.fixed_point ? `punto fijo: ${esc(u.fixed_point)}` : 'sin horarios asignados'))}` : ''}</span>
      ${u.role === 'MEDICO' && u.next_shift && !u.current_point ? `<span>Proximo: ${u.next_shift.weekday} ${u.next_shift.start}–${u.next_shift.end} en ${esc(u.next_shift.point)}</span>` : ''}
      <div class="shifts">${u.shifts.map((s) => shiftChip(s, false)).join('')}</div></div>
    <div class="acts" style="flex-direction:column;align-items:stretch">
      ${u.role === 'MEDICO' ? `<button class="btn sm soft" data-shift-user="${u.id}">${ic('clock', 'sm')} Horario</button>` : ''}
      <button class="btn sm ghost" data-edit-user="${u.id}">${ic('edit', 'sm')} Editar</button>
      <button class="btn sm ghost" data-pw="${u.id}">Clave</button>
      <button class="btn sm ${u.active ? 'amber' : 'soft'}" data-toggle-user="${u.id}">${u.active ? 'Desactivar' : 'Activar'}</button>
      <button class="btn sm danger" data-del-user="${u.id}">${ic('x', 'sm')}</button>
    </div>
  </div>`;

/** Rejilla semanal: filas = puntos, columnas = dias, celdas = franjas con el personal. */
const weekGrid = (points) => `
  <div class="tbl-wrap"><table class="tbl weekgrid"><thead><tr><th>Punto</th>${DAYS.map((d) => `<th>${d}</th>`).join('')}</tr></thead><tbody>
    ${points.map((p) => `<tr><td><b>${esc(p.name)}</b></td>${DAYS.map((_, i) => {
    const cell = p.shifts.filter((s) => s.weekdays.includes(i)).sort((a, b) => a.start.localeCompare(b.start));
    return `<td>${cell.length ? cell.map((s) => `<div class="slot"><b>${range(s)}</b><span>${esc(s.user_name)}</span></div>`).join('') : (p.scheduled ? '<span class="muted">—</span>' : '<span class="muted">24 h</span>')}</td>`;
  }).join('')}</tr>`).join('')}
  </tbody></table></div>`;

export const overviewView = (o) => `
  <section class="card"><div class="card-head"><h2><span class="ic">${ic('steth')}</span>Consultorios y laboratorios</h2><span class="muted">${o.points.length} puntos</span></div>
    ${o.points.length ? `<div class="rgrid">${o.points.map(pointCard).join('')}</div>` : emptyState('steth', 'Sin puntos', 'Crea el primer punto de atencion.')}</section>
  <section class="card" style="margin-top:24px"><div class="card-head"><h2><span class="ic">${ic('activity')}</span>Servicios</h2><span class="muted">${o.services.length} servicios</span></div>
    ${o.services.length ? `<div class="rgrid">${o.services.map(serviceCard).join('')}</div>` : emptyState('activity', 'Sin servicios', 'Crea el primer servicio.')}</section>
  <section class="card" style="margin-top:24px"><div class="card-head"><h2><span class="ic">${ic('clock')}</span>Horario semanal</h2>
    <span class="muted">Un punto sin horarios esta siempre disponible</span></div>${weekGrid(o.points)}</section>
  <section class="card" style="margin-top:24px"><div class="card-head"><h2><span class="ic">${ic('users')}</span>Usuarios</h2><span class="muted">${o.users.length} usuarios</span></div>
    ${o.users.length ? `<div class="tlist">${o.users.map(userRow).join('')}</div>` : emptyState('users', 'Sin usuarios', 'Registra al personal.')}</section>`;

// ------------------------------------------------------------------ formularios (modales)
export const pointFormView = (services, p) => `<h2>${p ? 'Editar punto' : 'Nuevo punto de atencion'}</h2>
  <div class="field"><label>Nombre</label><input type="text" id="f-name" value="${esc(p?.name || '')}" placeholder="Ej. Consultorio 3, Laboratorio 2" maxlength="80"></div>
  <div class="field"><label>Servicios que atiende</label>
    <div class="chips" id="f-services">${services.map((s) => `<span class="chip-toggle ${p?.services.some((x) => x.code === s.code) ? 'on' : ''}" data-code="${esc(s.code)}">${esc(s.name)}</span>`).join('')}</div></div>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">${p ? 'Guardar' : 'Crear punto'}</button></div>`;

export const serviceFormView = (s) => `<h2>${s ? 'Editar servicio' : 'Nuevo servicio'}</h2>
  <div class="row"><div class="field"><label>Codigo</label><input type="text" id="f-code" value="${esc(s?.code || '')}" ${s ? 'disabled' : ''} maxlength="8" placeholder="Ej. RX" style="text-transform:uppercase"></div>
  <div class="field"><label>Color</label><input type="color" id="f-color" value="${esc(s?.color || '#0d9488')}" style="height:46px;padding:4px"></div></div>
  <div class="field"><label>Nombre</label><input type="text" id="f-name" value="${esc(s?.name || '')}" placeholder="Ej. Rayos X" maxlength="80"></div>
  <div class="field"><label>Duracion inicial estimada (minutos)</label><input type="number" id="f-prior" min="1" max="240" value="${s?.prior_minutes ?? 10}"></div>
  <p class="muted" style="font-size:13px">La IA parte de este valor y lo corrige con las atenciones reales.</p>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">${s ? 'Guardar' : 'Crear servicio'}</button></div>`;

const roleSelect = (cur, id = 'f-role') => `<select id="${id}">${Object.entries(ROLE_LABEL).map(([k, v]) => `<option value="${k}" ${cur === k ? 'selected' : ''}>${v}</option>`).join('')}</select>`;

export const userFormView = () => `<h2>Nuevo usuario</h2>
  <div class="field"><label>Nombre completo</label><input type="text" id="f-name" maxlength="120"></div>
  <div class="row"><div class="field"><label>Usuario</label><input type="text" id="f-user" autocomplete="off" placeholder="ej. dr.perez" maxlength="40"></div>
  <div class="field"><label>Contrasena</label><input type="password" id="f-pass" autocomplete="new-password" placeholder="minimo 6"></div></div>
  <div class="field"><label>Rol</label>${roleSelect('MEDICO')}</div>
  <p class="muted" style="font-size:13px">El personal de atencion necesita un horario para atender un punto.</p>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">Crear</button></div>`;

export const userEditView = (u, isSelf) => `<h2>Editar usuario</h2>
  <div class="field"><label>Nombre completo</label><input type="text" id="f-name" value="${esc(u.name)}" maxlength="120"></div>
  <div class="field"><label>Rol</label>${roleSelect(u.role)}${isSelf ? '<div class="hint">No puedes cambiar tu propio rol.</div>' : ''}</div>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">Guardar</button></div>`;

export const passwordFormView = (u) => `<h2>Cambiar clave de ${esc(u.name)}</h2>
  <div class="field"><label>Nueva contrasena</label><input type="password" id="f-pass" autocomplete="new-password" placeholder="minimo 6"></div>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">Guardar</button></div>`;

export const shiftFormView = (o, pre) => {
  const staff = o.users.filter((u) => u.role === 'MEDICO' && u.active);
  return `<h2>Asignar horario</h2>
  <div class="row"><div class="field"><label>Personal de atencion</label><select id="f-user">${staff.map((u) => `<option value="${u.id}" ${pre.userId === u.id ? 'selected' : ''}>${esc(u.name)}</option>`).join('')}</select></div>
  <div class="field"><label>Punto</label><select id="f-point">${o.points.map((p) => `<option value="${p.id}" ${pre.pointId === p.id ? 'selected' : ''}>${esc(p.name)}</option>`).join('')}</select></div></div>
  <div class="field"><label>Dias</label><div class="chips" id="f-days">${DAYS.map((d, i) => `<span class="chip-toggle ${[0, 1, 2, 3, 4].includes(i) ? 'on' : ''}" data-day="${i}">${d}</span>`).join('')}</div>
    <div class="quick"><a href="#" data-q="weekdays">Lun-Vie</a><a href="#" data-q="all">Todos</a><a href="#" data-q="weekend">Fin de semana</a></div></div>
  <div class="row"><div class="field"><label>Desde</label><input type="time" id="f-start" value="07:00"></div>
  <div class="field"><label>Hasta</label><input type="time" id="f-end" value="13:00"></div></div>
  <p class="muted" style="font-size:13px" id="f-hint">Si la hora de fin es menor que la de inicio, el turno cruza la medianoche (ej. 22:00 a 06:00).</p>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">Asignar</button></div>`;
};

export const confirmView = (title, text, label) => `<h2>${esc(title)}</h2><p>${text}</p>
  <div class="foot"><button class="btn ghost" id="cx">Volver</button><button class="btn danger" id="yes">${esc(label)}</button></div>`;
