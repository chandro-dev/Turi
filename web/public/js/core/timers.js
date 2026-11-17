/* Actualizacion de pantallas. El router limpia todo al navegar.
   poll(fn, ms): ejecuta fn ya, cada vez que el servidor avisa de un cambio (SSE) y, como respaldo, por sondeo.
   Con tiempo real disponible el sondeo se hace mucho mas espaciado. */
import { liveSupported, onLive } from './live.js';

let timers = [];
let unsubs = [];

export const clearTimers = () => {
  timers.forEach(clearInterval);
  unsubs.forEach((u) => u());
  timers = [];
  unsubs = [];
};

export const poll = (fn, ms) => {
  fn();
  unsubs.push(onLive(fn));
  timers.push(setInterval(fn, liveSupported ? Math.max(ms * 6, 15000) : ms));
};

/** Registra un intervalo sin ejecutar fn de inmediato ni suscribirlo a cambios (relojes, reintentos). */
export const every = (fn, ms) => { timers.push(setInterval(fn, ms)); };
