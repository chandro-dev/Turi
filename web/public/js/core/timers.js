/* Temporizadores de sondeo ligados a la pantalla activa: el router los limpia al navegar. */
let timers = [];

export const clearTimers = () => { timers.forEach(clearInterval); timers = []; };

/** Ejecuta fn ya y luego cada ms milisegundos. */
export const poll = (fn, ms) => { fn(); timers.push(setInterval(fn, ms)); };

/** Registra un intervalo sin ejecutar fn de inmediato. */
export const every = (fn, ms) => { timers.push(setInterval(fn, ms)); };
