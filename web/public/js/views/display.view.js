/* VISTA: pantalla de espera (TV de sala). Solo muestra codigos, nunca datos personales. */
import { esc } from '../core/dom.js';
import { BRAND } from './components.js';

export const displayShell = () => `<div class="tv">
  <div class="tv-head">${BRAND}<div class="tv-clock"><span id="clock"></span><small id="dt"></small></div></div>
  <div class="tv-grid">
    <section><h2>Llamando ahora</h2><div class="calls" id="calls"></div></section>
    <section class="tv-next"><h2>Proximos turnos</h2><div id="next"></div></section>
  </div>
  <div class="tv-foot"><a href="#/login">Ingresar al sistema</a></div></div>`;

export const callsView = (calls, fresh) => (calls.length
  ? calls.slice(0, 5).map((c, i) => `
    <div class="call ${i === 0 ? 'first' : ''} ${i === 0 && fresh ? 'fresh' : ''}" style="--c:${c.color}"><div class="c">${esc(c.code)}</div><div class="p">${esc(c.point)}</div>
    <div class="s"><i></i>${c.status === 'IN_SERVICE' ? 'En atencion' : 'Pase por favor'}${c.preferential ? ' · ★ Preferencial' : ''}</div></div>`).join('')
  : '<div class="tv-empty">Aun no hay turnos llamados</div>');

/** Proximos turnos por punto: el primero se destaca como "Siguiente". */
export const nextView = (points) => points.map((p) => `
  <div class="npt ${p.active ? '' : 'off'}">
    <div class="t"><span>${esc(p.name)}</span><small>${p.active ? `${p.waiting} en fila` : 'en pausa'}</small></div>
    ${p.active && p.upcoming.length
      ? `<div class="chipsrow">${p.upcoming.map((u, i) => `<span class="tchip ${i === 0 ? 'first' : ''}" style="--c:${u.color}">${esc(u.code)}${u.preferential ? '<em>★</em>' : ''}</span>`).join('')}</div>`
      : `<div class="none">${p.active ? 'Sin turnos en espera' : 'Punto no disponible'}</div>`}
  </div>`).join('');
