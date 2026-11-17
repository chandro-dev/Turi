/* VISTA: consultorios, laboratorios y personal con sus horarios (supervisor). */
import { esc } from '../core/dom.js';
import { ic, initials } from '../core/icons.js';
import { POINT_STATUS } from '../models/constants.js';
import { emptyState } from './components.js';
import { headView } from './layout.js';

const DAYS = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'];

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

const statusBadge = (s) => {
  const cls = { open: 'b-IN_SERVICE', paused: 'b-CALLED', off_hours: 'b-WAITING', closed: 'b-CANCELLED' }[s] || 'b-low';
  return `<span class="badge ${cls}">${POINT_STATUS[s] || s}</span>`;
};

export const resourcesShell = () => `
  ${headView('Consultorios y personal', 'Abre puntos de atencion, registra al personal y asignale horarios.',
    `<div class="head-actions">
      <button class="btn" id="new-point">${ic('plus')} Nuevo punto</button>
      <button class="btn soft" id="new-staff">${ic('users')} Nuevo personal</button>
      <button class="btn soft" id="new-shift">${ic('clock')} Asignar horario</button>
    </div>`)}
  <div id="res"></div>`;

const shiftChip = (s, showUser) => `<span class="shift-chip">${ic('clock', 'sm')}<span><b>${daysText(s.weekdays)}</b> ${s.start}–${s.end}${showUser ? ` · ${esc(s.user_name)}` : ` · ${esc(s.point_name)}`}</span>
  <button class="x" data-del-shift="${s.id}" title="Quitar horario">${ic('x', 'sm')}</button></span>`;

const pointCard = (p) => `
  <div class="rcard ${p.status === 'closed' ? 'closed' : ''}">
    <div class="rtop"><b>${esc(p.name)}</b>${statusBadge(p.status)}</div>
    <div class="chips-mini">${p.services.map((s) => `<span class="svc" style="--c:${s.color}"><i></i>${esc(s.name)}</span>`).join('')}</div>
    <div class="rline">${ic('users', 'sm')} ${p.on_duty.length ? `Atiende ahora: <b>${esc(p.on_duty.join(', '))}</b>` : (p.scheduled ? 'Sin personal en este horario' : '<span class="muted">Sin horarios: siempre disponible</span>')}</div>
    <div class="rline">${ic('ticket', 'sm')} ${p.active_turns} turno(s) activo(s) hoy</div>
    <div class="shifts">${p.shifts.length ? p.shifts.map((s) => shiftChip(s, true)).join('') : ''}</div>
    <div class="acts" style="margin-top:12px">
      <button class="btn sm soft" data-shift-point="${p.id}">${ic('clock', 'sm')} Horario</button>
      <button class="btn sm ghost" data-edit-point="${p.id}">${ic('edit', 'sm')} Editar</button>
      <button class="btn sm ${p.enabled ? 'amber' : 'soft'}" data-toggle-point="${p.id}">${p.enabled ? 'Cerrar' : 'Abrir'}</button>
      <button class="btn sm danger" data-del-point="${p.id}">${ic('x', 'sm')}</button>
    </div>
  </div>`;

const staffRow = (u) => `
  <div class="titem staff" style="--sc:#4f46e5;grid-template-columns:auto 1fr auto">
    <div class="avatar sm" style="--av:linear-gradient(135deg,#14b8a6,#4f46e5)">${esc(initials(u.name))}</div>
    <div class="who"><b>${esc(u.name)}</b><span>@${esc(u.username)} · ${u.current_point ? `atendiendo <b>${esc(u.current_point)}</b>` : (u.shifts.length ? 'fuera de turno' : (u.fixed_point ? `punto fijo: ${esc(u.fixed_point)}` : 'sin horarios asignados'))}</span>
      ${u.next_shift && !u.current_point ? `<span>Proximo: ${u.next_shift.weekday} ${u.next_shift.start}–${u.next_shift.end} en ${esc(u.next_shift.point)}</span>` : ''}
      <div class="shifts">${u.shifts.map((s) => shiftChip(s, false)).join('')}</div></div>
    <div class="acts" style="flex-direction:column;align-items:stretch">
      <button class="btn sm soft" data-shift-user="${u.id}">${ic('clock', 'sm')} Horario</button>
      <button class="btn sm ghost" data-pw="${u.id}">Clave</button>
      <button class="btn sm danger" data-del-staff="${u.id}">${ic('x', 'sm')}</button>
    </div>
  </div>`;

/** Rejilla semanal: filas = puntos, columnas = dias, celdas = franjas con el personal. */
const weekGrid = (points) => `
  <div class="tbl-wrap"><table class="tbl weekgrid"><thead><tr><th>Punto</th>${DAYS.map((d) => `<th>${d}</th>`).join('')}</tr></thead><tbody>
    ${points.map((p) => `<tr><td><b>${esc(p.name)}</b></td>${DAYS.map((_, i) => {
    const cell = p.shifts.filter((s) => s.weekdays.includes(i)).sort((a, b) => a.start.localeCompare(b.start));
    return `<td>${cell.length ? cell.map((s) => `<div class="slot"><b>${s.start}–${s.end}</b><span>${esc(s.user_name)}</span></div>`).join('') : (p.scheduled ? '<span class="muted">—</span>' : '<span class="muted">24 h</span>')}</td>`;
  }).join('')}</tr>`).join('')}
  </tbody></table></div>`;

export const overviewView = (o) => `
  <section class="card"><div class="card-head"><h2><span class="ic">${ic('steth')}</span>Puntos de atencion</h2><span class="muted">${o.points.length} puntos</span></div>
    ${o.points.length ? `<div class="rgrid">${o.points.map(pointCard).join('')}</div>` : emptyState('steth', 'Sin puntos', 'Crea el primer punto de atencion.')}</section>
  <section class="card" style="margin-top:24px"><div class="card-head"><h2><span class="ic">${ic('clock')}</span>Horario semanal</h2>
    <span class="muted">Un punto sin horarios esta siempre disponible</span></div>${weekGrid(o.points)}</section>
  <section class="card" style="margin-top:24px"><div class="card-head"><h2><span class="ic">${ic('users')}</span>Personal</h2><span class="muted">${o.staff.length} funcionarios</span></div>
    ${o.staff.length ? `<div class="tlist">${o.staff.map(staffRow).join('')}</div>` : emptyState('users', 'Sin personal', 'Registra al personal que atiende los puntos.')}</section>`;

// ------------------------------------------------------------------ formularios (modales)
export const pointFormView = (services, p) => `<h2>${p ? 'Editar punto' : 'Nuevo punto de atencion'}</h2>
  <div class="field"><label>Nombre</label><input type="text" id="f-name" value="${esc(p?.name || '')}" placeholder="Ej. Consultorio 3, Laboratorio 2" maxlength="80"></div>
  <div class="field"><label>Servicios que atiende</label>
    <div class="chips" id="f-services">${services.map((s) => `<span class="chip-toggle ${p?.services.some((x) => x.code === s.code) ? 'on' : ''}" data-code="${esc(s.code)}">${esc(s.name)}</span>`).join('')}</div></div>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">${p ? 'Guardar' : 'Crear punto'}</button></div>`;

export const staffFormView = () => `<h2>Nuevo personal</h2>
  <div class="field"><label>Nombre completo</label><input type="text" id="f-name" maxlength="120"></div>
  <div class="row"><div class="field"><label>Usuario</label><input type="text" id="f-user" autocomplete="off" placeholder="ej. dr.perez" maxlength="40"></div>
  <div class="field"><label>Contrasena</label><input type="password" id="f-pass" autocomplete="new-password" placeholder="minimo 6"></div></div>
  <p class="muted" style="font-size:13px">Despues asignale un horario para que pueda atender un punto.</p>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">Crear</button></div>`;

export const passwordFormView = (u) => `<h2>Cambiar clave de ${esc(u.name)}</h2>
  <div class="field"><label>Nueva contrasena</label><input type="password" id="f-pass" autocomplete="new-password" placeholder="minimo 6"></div>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">Guardar</button></div>`;

export const shiftFormView = (o, pre) => `<h2>Asignar horario</h2>
  <div class="row"><div class="field"><label>Personal</label><select id="f-user">${o.staff.map((u) => `<option value="${u.id}" ${pre.userId === u.id ? 'selected' : ''}>${esc(u.name)}</option>`).join('')}</select></div>
  <div class="field"><label>Punto</label><select id="f-point">${o.points.map((p) => `<option value="${p.id}" ${pre.pointId === p.id ? 'selected' : ''}>${esc(p.name)}</option>`).join('')}</select></div></div>
  <div class="field"><label>Dias</label><div class="chips" id="f-days">${DAYS.map((d, i) => `<span class="chip-toggle ${[0, 1, 2, 3, 4].includes(i) ? 'on' : ''}" data-day="${i}">${d}</span>`).join('')}</div>
    <div class="quick"><a href="#" data-q="weekdays">Lun-Vie</a><a href="#" data-q="all">Todos</a><a href="#" data-q="weekend">Fin de semana</a></div></div>
  <div class="row"><div class="field"><label>Desde</label><input type="time" id="f-start" value="07:00"></div>
  <div class="field"><label>Hasta</label><input type="time" id="f-end" value="13:00"></div></div>
  <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">Asignar</button></div>`;

export const confirmView = (title, text, label) => `<h2>${esc(title)}</h2><p>${text}</p>
  <div class="foot"><button class="btn ghost" id="cx">Volver</button><button class="btn danger" id="yes">${esc(label)}</button></div>`;
