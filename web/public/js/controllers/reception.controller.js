/* CONTROLADOR: recepcion. Coordina formulario, sugerencia de IA y fila activa. */
import { $, $$, guard, modal, toast } from '../core/dom.js';
import { poll } from '../core/timers.js';
import { pregnancyAllowed, PREGNANCY_HINT } from '../models/rules.js';
import { repo } from '../models/repository.js';
import { session } from '../models/session.js';
import {
  ageNoticeView, cancelModalView, editModalView, queueRowsView, reassignModalView, receptionView,
  suggestionView, tabsView, ticketModalView, tilesView,
} from '../views/reception.view.js';
import { mountShell } from './shell.js';

export function receptionController() {
  const st = {
    services: [], points: [], turns: [], filter: 'all',
    service: null, point: null, sugg: null, seq: 0,
    flags: { pregnant: false, disability: false },
  };
  mountShell(receptionView(session.user), '#/recepcion');

  // ---------------------------------------------------------- formulario
  const age = () => parseInt($('#age').value, 10);
  const formData = () => ({
    doc_number: $('#doc').value.trim(), patient_name: $('#name').value.trim(), phone: $('#phone').value.trim() || null,
    age: age(), pregnant: st.flags.pregnant, disability: st.flags.disability,
  });
  const formReady = () => {
    const d = formData();
    return d.doc_number.length >= 3 && d.patient_name.length >= 2 && Number.isInteger(d.age) && d.age >= 0
      && (!d.pregnant || pregnancyAllowed(d.age)) && !!st.service;
  };

  /** Bloquea "Gestante" cuando la edad esta fuera de rango y desmarca si ya estaba activa. */
  function syncPregnancyRule() {
    const a = age();
    const outOfRange = Number.isInteger(a) && !pregnancyAllowed(a);
    const chip = $('#chip-pregnant');
    chip.classList.toggle('disabled', outOfRange);
    if (outOfRange && st.flags.pregnant) { st.flags.pregnant = false; chip.classList.remove('on'); }
    const hint = $('#preg-hint');
    hint.textContent = PREGNANCY_HINT;
    hint.classList.toggle('hide', !outOfRange);
  }

  function renderTiles() {
    $('#tiles').innerHTML = tilesView(st.services, st.service);
    $$('.tile').forEach((b) => { b.onclick = () => { st.service = b.dataset.c; st.point = null; renderTiles(); refreshSuggestion(); }; });
  }

  let debounce;
  function refreshSuggestion() {
    clearTimeout(debounce);
    $('#submit').disabled = true;
    if (!st.service || !Number.isInteger(age())) { $('#sugg').innerHTML = ageNoticeView(st.service); return; }
    debounce = setTimeout(guard(async () => {
      const seq = ++st.seq;
      const d = formData();
      const r = await repo.suggest({ service_code: st.service, age: d.age, pregnant: d.pregnant, disability: d.disability });
      if (seq !== st.seq) return;
      st.sugg = r;
      if (!st.point || !r.options.find((o) => o.point_id === st.point)) st.point = r.options[0]?.point_id ?? null;
      renderSuggestion();
    }), 250);
  }

  function renderSuggestion() {
    $('#sugg').innerHTML = suggestionView(st.sugg, st.point);
    $$('#sugg .opt').forEach((o) => { o.onclick = () => { st.point = +o.dataset.p; renderSuggestion(); }; });
    $('#submit').disabled = !(formReady() && st.point);
  }

  function resetForm() {
    $('#nf').reset();
    st.flags = { pregnant: false, disability: false };
    st.service = null; st.point = null; st.sugg = null;
    $$('.chip-toggle').forEach((c) => c.classList.remove('on', 'disabled'));
    $('#preg-hint').classList.add('hide');
    renderTiles();
    $('#sugg').innerHTML = '';
  }

  $$('#nf .chip-toggle').forEach((c) => {
    c.onclick = () => {
      if (c.classList.contains('disabled')) { toast(PREGNANCY_HINT, 'error'); return; }
      const f = c.dataset.flag;
      st.flags[f] = !st.flags[f];
      c.classList.toggle('on', st.flags[f]);
      refreshSuggestion();
    };
  });
  ['doc', 'name'].forEach((id) => { $('#' + id).oninput = () => { if (st.sugg) renderSuggestion(); }; });
  $('#age').oninput = () => { syncPregnancyRule(); refreshSuggestion(); };

  $('#nf').onsubmit = guard(async (e) => {
    e.preventDefault();
    if (!formReady() || !st.point) return;
    $('#submit').disabled = true;
    try {
      const t = await repo.createTurn({ ...formData(), service_code: st.service, point_id: st.point });
      showTicket(t);
      resetForm();
      loadQueue();
    } catch (err) {
      $('#submit').disabled = false;
      throw err;
    }
  });

  function showTicket(t) {
    modal(ticketModalView(t), (root, close) => { $('#ok', root).onclick = close; $('#ok', root).focus(); }, 'ticket-modal');
  }

  // ---------------------------------------------------------- acciones sobre la fila
  const reassign = (t) => {
    const options = st.points.filter((p) => p.services.includes(t.service.code) && !['closed', 'off_hours'].includes(p.status));
    const requeue = t.status === 'NO_SHOW';
    modal(reassignModalView(t, options), (root, close) => {
      $('#cx', root).onclick = close;
      $$('.opt', root).forEach((o) => {
        o.onclick = guard(async () => {
          await repo.reassignTurn(t.id, +o.dataset.p);
          close();
          toast(requeue ? 'Paciente reincorporado' : 'Turno reasignado', 'ok');
          loadQueue();
        });
      });
    });
  };

  const edit = (t) => {
    const fl = { pregnant: t.pregnant, disability: t.disability };
    modal(editModalView(t), (root, close) => {
      const preg = $('[data-f="pregnant"]', root);
      const hint = $('#e-hint', root);
      const sync = () => {
        const a = parseInt($('#ea', root).value, 10);
        const bad = Number.isInteger(a) && !pregnancyAllowed(a);
        preg.classList.toggle('disabled', bad);
        if (bad && fl.pregnant) { fl.pregnant = false; preg.classList.remove('on'); }
        hint.textContent = PREGNANCY_HINT;
        hint.classList.toggle('hide', !bad);
      };
      sync();
      $('#ea', root).oninput = sync;
      $$('.chip-toggle', root).forEach((c) => {
        c.onclick = () => {
          if (c.classList.contains('disabled')) return;
          fl[c.dataset.f] = !fl[c.dataset.f];
          c.classList.toggle('on', fl[c.dataset.f]);
        };
      });
      $('#cx', root).onclick = close;
      $('#sv', root).onclick = guard(async () => {
        await repo.patchTurn(t.id, {
          patient_name: $('#en', root).value, doc_number: $('#ed', root).value, age: +$('#ea', root).value,
          phone: $('#ep', root).value, ...fl,
        });
        close();
        toast('Turno actualizado', 'ok');
        loadQueue();
      });
    });
  };

  const cancel = (t) => modal(cancelModalView(t), (root, close) => {
    $('#cx', root).onclick = close;
    $('#yes', root).onclick = guard(async () => { await repo.cancelTurn(t.id); close(); toast('Turno cancelado'); loadQueue(); });
  });
  const ACTIONS = { reassign, edit, cancel };

  function renderQueue() {
    $('#tabs').innerHTML = tabsView(st.points, st.filter);
    $$('.tab').forEach((b) => { b.onclick = () => { st.filter = b.dataset.f; renderQueue(); }; });
    const rank = { IN_SERVICE: 0, CALLED: 1, WAITING: 2, NO_SHOW: 3 };
    const list = st.turns
      .filter((t) => st.filter === 'all' || String(t.point.id) === st.filter)
      .sort((a, b) => rank[a.status] - rank[b.status] || (a.position ?? 99) - (b.position ?? 99));
    $('#queue').innerHTML = queueRowsView(list);
    $$('#queue [data-a]').forEach((b) => {
      const t = st.turns.find((x) => x.id === +b.closest('.titem').dataset.id);
      b.onclick = () => ACTIONS[b.dataset.a](t);
    });
  }

  const loadQueue = guard(async () => {
    [st.turns, st.points] = await Promise.all([repo.turns(), repo.points()]);
    renderQueue();
  });

  guard(async () => { st.services = await repo.services(); renderTiles(); })();
  poll(loadQueue, 4000);
}
