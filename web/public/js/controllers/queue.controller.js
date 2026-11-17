/* CONTROLADOR: fila general del supervisor. Carga turnos activos Y cerrados (atendidos, cancelados). */
import { $, $$, guard } from '../core/dom.js';
import { poll } from '../core/timers.js';
import { ACTIVE_STATUSES } from '../models/constants.js';
import { repo } from '../models/repository.js';
import { chipsView, queueListView, queueShell, STATUS_FILTERS, summaryView } from '../views/queue.view.js';
import { mountShell } from './shell.js';

const avg = (xs) => (xs.length ? Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 10) / 10 : null);

export function queueController() {
  const st = { turns: [], points: [], status: 'ALL', point: 'all' };
  mountShell(queueShell(), '#/fila');

  const matchStatus = (t) => {
    if (st.status === 'ALL') return true;
    if (st.status === 'ACTIVE') return ACTIVE_STATUSES.includes(t.status) && t.status !== 'NO_SHOW';
    return t.status === st.status;
  };
  const rank = { IN_SERVICE: 0, CALLED: 1, WAITING: 2, NO_SHOW: 3, DONE: 4, CANCELLED: 5 };

  function render() {
    const done = st.turns.filter((t) => t.status === 'DONE');
    $('#qsum').innerHTML = summaryView({
      total: st.turns.length,
      done: done.length,
      active: st.turns.filter((t) => ['WAITING', 'CALLED', 'IN_SERVICE'].includes(t.status)).length,
      avgService: avg(done.map((t) => t.duration_min).filter((x) => x != null)),
      avgWait: avg(st.turns.map((t) => t.wait_min).filter((x) => x != null)),
    });

    const counts = (f) => st.turns.filter((t) => {
      if (f === 'ALL') return true;
      if (f === 'ACTIVE') return ['WAITING', 'CALLED', 'IN_SERVICE'].includes(t.status);
      return t.status === f;
    }).length;
    $('#qstatus').innerHTML = chipsView(STATUS_FILTERS.map(([id, name]) => [id, name, counts(id)]), st.status);
    $('#qpoints').innerHTML = chipsView([['all', 'Todos los puntos'], ...st.points.map((p) => [String(p.id), p.name])], st.point);

    const list = st.turns
      .filter(matchStatus)
      .filter((t) => st.point === 'all' || String(t.point.id) === st.point)
      .sort((a, b) => rank[a.status] - rank[b.status]
        || (a.status === 'DONE' || a.status === 'CANCELLED'
          ? new Date(b.finished_at || 0) - new Date(a.finished_at || 0)
          : (a.position ?? 99) - (b.position ?? 99)));
    $('#qlist').innerHTML = queueListView(list);

    $$('#qstatus .tab').forEach((b) => { b.onclick = () => { st.status = b.dataset.f; render(); }; });
    $$('#qpoints .tab').forEach((b) => { b.onclick = () => { st.point = b.dataset.f; render(); }; });
  }

  const load = guard(async () => {
    [st.turns, st.points] = await Promise.all([repo.turns(true), repo.points()]);
    render();
  });
  poll(load, 5000);
}
