/* CONTROLADOR: pantalla de espera (publica). Sondea cada 3 s y resalta el llamado mas reciente. */
import { $ } from '../core/dom.js';
import { dateStr } from '../core/format.js';
import { every, poll } from '../core/timers.js';
import { repo } from '../models/repository.js';
import { callsView, displayShell, nextView } from '../views/display.view.js';

export function displayController() {
  $('#app').innerHTML = displayShell();
  const tick = () => {
    $('#clock').textContent = new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
    $('#dt').textContent = dateStr();
  };
  tick();
  every(tick, 10000);

  let seen = null;
  const load = async () => {
    let d;
    try { d = await repo.display(); } catch { return; }
    const newest = d.calls.length ? d.calls[0].code + d.calls[0].called_at : '';
    const fresh = seen !== null && !!newest && !seen.has(newest);
    seen = seen || new Set();
    seen.add(newest);
    $('#calls').innerHTML = callsView(d.calls, fresh);
    $('#next').innerHTML = nextView(d.points);
  };
  poll(load, 3000);
}
