/* CONTROLADOR: punto de atencion (llamar, iniciar, no presentado, finalizar). */
import { $, $$, guard, toast } from '../core/dom.js';
import { poll } from '../core/timers.js';
import { repo } from '../models/repository.js';
import { doctorView, offShiftView } from '../views/doctor.view.js';
import { mountShell } from './shell.js';

export function doctorController() {
  mountShell('<div id="doc"></div>', '#/medico');
  let busy = false;

  const act = (path) => guard(async () => {
    if (busy) return;
    busy = true;
    try { await repo.doctorAction(path); await load(); } finally { busy = false; }
  });

  function render(d) {
    if (d.off_shift) { $('#doc').innerHTML = offShiftView(d); return; }
    $('#doc').innerHTML = doctorView(d);
    $$('[data-p]').forEach((b) => { b.onclick = act(b.dataset.p); });
    $('#act').onchange = guard(async (e) => {
      await repo.setActive(e.target.checked);
      toast(e.target.checked ? 'Estas disponible' : 'Punto en pausa: no recibira nuevos turnos');
      load();
    });
  }

  const load = guard(async () => render(await repo.doctorPanel()));
  poll(() => { if (!busy) load(); }, 4000);
}
