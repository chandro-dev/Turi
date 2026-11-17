/* VISTA: estructura comun (barra lateral + contenido). */
import { esc } from '../core/dom.js';
import { dateStr } from '../core/format.js';
import { ic, initials } from '../core/icons.js';
import { ROLE } from '../models/constants.js';
import { BRAND } from './components.js';

const NAV = {
  RECEPCION: [['#/recepcion', 'Recepcion', 'clipboard'], ['#/consulta', 'Consulta paciente', 'search'], ['#/pantalla', 'Pantalla de turnos', 'monitor']],
  MEDICO: [['#/medico', 'Mi consultorio', 'steth'], ['#/pantalla', 'Pantalla de turnos', 'monitor']],
  SUPERVISOR: [['#/supervisor', 'Indicadores', 'chart'], ['#/fila', 'Fila general', 'list'], ['#/consulta', 'Consulta paciente', 'search'], ['#/pantalla', 'Pantalla de turnos', 'monitor']],
};

export function shellView(user, content, active) {
  const links = NAV[user.role]
    .map(([h, l, i]) => `<a href="${h}" class="${h === active ? 'active' : ''}" title="${l}">${ic(i)}<span>${l}</span></a>`)
    .join('');
  return `
    <div class="app">
      <aside class="side">${BRAND}
        <nav class="nav"><div class="nav-label">Menu</div>${links}</nav>
        <div class="side-user"><div class="avatar sm" style="--av:linear-gradient(135deg,#14b8a6,#4f46e5)">${esc(initials(user.name))}</div>
          <div class="who"><b>${esc(user.name)}</b><span>${ROLE[user.role]}${user.point ? ' · ' + esc(user.point.name) : ''}</span></div>
          <button class="icon-btn" id="logout" title="Cerrar sesion">${ic('logout', 'sm')}</button></div>
      </aside>
      <main class="main"><div class="page" id="page">${content}</div></main>
    </div>`;
}

export const headView = (title, sub, right = '') =>
  `<div class="page-head"><div><div class="eyebrow">${esc(dateStr())}</div><h1>${title}</h1><div class="sub">${sub}</div></div>${right}</div>`;
