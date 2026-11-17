/* Tiempo real: el servidor avisa (SSE) cada vez que cambian los datos y las pantallas se refrescan al instante.
   Si la conexion cae, el navegador reconecta solo y el sondeo lento de respaldo (timers.js) cubre el hueco. */
export const liveSupported = typeof EventSource !== 'undefined';

let source = null;
let wasDown = false;
let timer = null;
const subs = new Set();

function fire() {
  clearTimeout(timer);
  timer = setTimeout(() => subs.forEach((fn) => { try { fn(); } catch { /* una vista no debe romper a las demas */ } }), 250);
}

export function connectLive() {
  if (!liveSupported || source) return;
  source = new EventSource('/api/events');
  source.onopen = () => { if (wasDown) { wasDown = false; fire(); } };  // al reconectar, ponerse al dia
  source.onmessage = (e) => { if (e.data !== 'hello') fire(); };
  source.onerror = () => { wasDown = true; };
}

/** Suscribe fn a los cambios del servidor. Devuelve la funcion para cancelar. */
export function onLive(fn) {
  subs.add(fn);
  return () => subs.delete(fn);
}
