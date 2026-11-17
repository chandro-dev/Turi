/* Utilidades de DOM compartidas por vistas y controladores. */
export const $ = (sel, el = document) => el.querySelector(sel);
export const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
));

export function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

/** Envuelve un handler async: cualquier error se muestra como toast. */
export const guard = (fn) => async (...args) => {
  try { return await fn(...args); } catch (e) { toast(e.message, 'error'); }
};

/** Abre un modal. onMount(root, close) enlaza los eventos del contenido. */
export function modal(html, onMount, cls = '') {
  const root = $('#modal-root');
  root.innerHTML = `<div class="overlay"><div class="modal ${cls}">${html}</div></div>`;
  const close = () => { root.innerHTML = ''; };
  $('.overlay', root).addEventListener('mousedown', (e) => { if (e.target.classList.contains('overlay')) close(); });
  if (onMount) onMount(root, close);
  return close;
}
export const closeModal = () => { $('#modal-root').innerHTML = ''; };
