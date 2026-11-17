/* CONTROLADOR: prueba del modelo de IA (supervisor). */
import { $, $$, guard, toast } from '../core/dom.js';
import { poll } from '../core/timers.js';
import { repo } from '../models/repository.js';
import { answerView, modelShell, reportView } from '../views/model.view.js';
import { mountShell } from './shell.js';

export async function modelController() {
  const services = await repo.services();
  if (location.hash !== '#/modelo') return;  // el usuario ya navego a otra pantalla
  mountShell(modelShell(services), '#/modelo');
  let preferential = false;

  const load = guard(async () => {
    $('#mreport').innerHTML = reportView(await repo.modelReport());
    const rt = $('#retrain');
    if (rt) {
      rt.onclick = guard(async () => {
        rt.disabled = true;
        const r = await repo.modelRetrain();
        toast(r.trained ? `scikit-learn reentrenado con ${r.samples} atenciones` : `No se pudo entrenar: ${r.reason || 'faltan datos'}`, r.trained ? 'ok' : 'error');
        load();
      });
    }
  });
  $('#refresh').onclick = load;
  poll(load, 10000);

  $$('#pf .chip-toggle').forEach((c) => {
    c.onclick = () => {
      preferential = c.dataset.pref === '1';
      $$('#pf .chip-toggle').forEach((x) => x.classList.toggle('on', x === c));
    };
  });

  $('#pf').onsubmit = guard(async (e) => {
    e.preventDefault();
    const btn = $('#ask');
    btn.disabled = true;
    try {
      const a = await repo.modelPredict({ service_code: $('#p-service').value, preferential });
      $('#panswer').innerHTML = answerView(a);
    } finally {
      btn.disabled = false;
    }
  });
}
