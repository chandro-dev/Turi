/* CONTROLADOR: indicadores del supervisor. */
import { $, guard, toast } from '../core/dom.js';
import { poll } from '../core/timers.js';
import { repo } from '../models/repository.js';
import { statsView, supervisorShell } from '../views/supervisor.view.js';
import { mountShell } from './shell.js';

export function supervisorController() {
  mountShell(supervisorShell(), '#/supervisor');
  const load = guard(async () => { $('#sv').innerHTML = statsView(await repo.stats()); });

  $('#sim').onclick = guard(async () => {
    const r = await repo.simulate(8);
    toast(`${r.created} pacientes simulados`, 'ok');
    load();
  });
  poll(load, 5000);
}
