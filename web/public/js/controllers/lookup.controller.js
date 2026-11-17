/* CONTROLADOR: consulta publica del turno (codigo o documento). */
import { $ } from '../core/dom.js';
import { every } from '../core/timers.js';
import { repo } from '../models/repository.js';
import { lookupShell, notFoundView, ticketView } from '../views/lookup.view.js';

export function lookupController() {
  $('#app').innerHTML = lookupShell();
  let q = '';
  const load = async () => {
    if (!q) return;
    try { $('#res').innerHTML = ticketView(await repo.lookup(q)); }
    catch (e) { $('#res').innerHTML = notFoundView(e.message); }
  };
  $('#lf').onsubmit = (e) => { e.preventDefault(); q = $('#q').value.trim(); load(); };
  every(load, 5000);
}
