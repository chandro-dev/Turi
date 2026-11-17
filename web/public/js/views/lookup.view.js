/* VISTA: consulta publica del turno por parte del paciente. */
import { esc } from '../core/dom.js';
import { mins } from '../core/format.js';
import { ic } from '../core/icons.js';
import { BRAND, prioBadge, statusBadge } from './components.js';

export const lookupShell = () => `<div class="lookup-bg"><div class="lookup">${BRAND}
  <div class="card"><h2 style="margin-bottom:6px">Consulta tu turno</h2>
    <p class="muted" style="margin-bottom:16px">Escribe el codigo de tu turno (ej. CG-004) o tu documento.</p>
    <form id="lf" style="display:flex;gap:10px"><input type="search" id="q" placeholder="Codigo o documento" required autofocus><button class="btn">${ic('search')}</button></form>
  </div><div id="res" style="margin-top:20px"></div>
  <p style="text-align:center;margin-top:24px"><a href="#/login" style="color:#fff;font-weight:600;opacity:.9">Ingreso del personal</a></p></div></div>`;

const STEPS = ['Espera', 'Llamado', 'Atencion', 'Finalizado'];
const STEP_INDEX = { WAITING: 0, CALLED: 1, IN_SERVICE: 2, DONE: 3 };

const MESSAGES = (t) => ({
  CALLED: `¡Es tu turno! Dirigete a ${t.point.name}`,
  IN_SERVICE: 'Estas siendo atendido',
  DONE: 'Tu atencion finalizo. ¡Gracias!',
  CANCELLED: 'Este turno fue cancelado',
  NO_SHOW: 'No te presentaste al llamado. Acude a recepcion para reincorporarte',
}[t.status]);

export const ticketView = (t) => {
  const idx = STEP_INDEX[t.status];
  return `<div class="card ticket">
    <div>${statusBadge(t.status)} ${prioBadge(t)}</div>
    <div class="big-code">${esc(t.code)}</div>
    <div style="font-weight:800;font-size:19px">${esc(t.patient_name)}</div><div class="muted">${esc(t.service.name)}</div>
    ${idx !== undefined ? `<div class="track">${STEPS.map((s, i) => `<div class="${i < idx ? 'done' : i === idx ? 'now' : ''}"><i></i>${s}</div>`).join('')}</div>` : ''}
    ${t.status === 'WAITING'
      ? `<div class="line"><div><b>#${t.position}</b><small>Tu posicion</small></div><div><b>${mins(t.eta_min)}</b><small>Espera aprox.</small></div><div><b>${esc(t.point.name)}</b><small>Punto</small></div></div>`
      : `<div class="notice" style="margin:22px 0 0;justify-content:center">${MESSAGES(t)}</div>`}
  </div>`;
};

export const notFoundView = (message) =>
  `<div class="card empty"><div class="ico">${ic('search')}</div>${esc(message)}</div>`;
