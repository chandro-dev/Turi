/* VISTA: componentes reutilizables (funciones puras que devuelven HTML). */
import { esc } from '../core/dom.js';
import { ic } from '../core/icons.js';
import { STATUS } from '../models/constants.js';

export const BRAND = `<div class="brand"><div class="brand-mark"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"><path d="M5 7h14M12 7v12"/></svg></div><span>Turi</span></div>`;

export const statusBadge = (s) => `<span class="badge b-${s}">${STATUS[s] || s}</span>`;

export const prioBadge = (t) => {
  if (t.priority_class === 'PREFERENCIAL') {
    return `<span class="badge b-pref" title="${esc(t.priority_reasons.join(', '))}">${ic('star', 'sm')} Preferencial</span>`;
  }
  if (t.priority_class === 'BAJA') return '<span class="badge b-low">Reincorporado</span>';
  return '';
};

export const emptyState = (icon, title, text) =>
  `<div class="empty"><div class="ico">${ic(icon)}</div><b>${title}</b><br>${text}</div>`;
