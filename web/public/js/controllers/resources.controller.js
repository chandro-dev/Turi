/* CONTROLADOR: consultorios, laboratorios, personal y horarios (supervisor). */
import { $, $$, guard, modal, toast } from '../core/dom.js';
import { poll } from '../core/timers.js';
import { repo } from '../models/repository.js';
import {
  confirmView, overviewView, passwordFormView, pointFormView, resourcesShell, shiftFormView, staffFormView,
} from '../views/resources.view.js';
import { mountShell } from './shell.js';

export function resourcesController() {
  mountShell(resourcesShell(), '#/recursos');
  let data = null;

  const load = guard(async () => {
    data = await repo.adminOverview();
    $('#res').innerHTML = overviewView(data);
    bind();
  });
  const done = (msg) => (close) => { close(); toast(msg, 'ok'); load(); };

  // ---------------------------------------------------------- formularios
  const pointForm = (p) => modal(pointFormView(data.services, p), (root, close) => {
    $$('#f-services .chip-toggle', root).forEach((c) => { c.onclick = () => c.classList.toggle('on'); });
    $('#cx', root).onclick = close;
    $('#sv', root).onclick = guard(async () => {
      const body = {
        name: $('#f-name', root).value,
        service_codes: $$('#f-services .chip-toggle.on', root).map((c) => c.dataset.code),
      };
      if (p) await repo.patchPoint(p.id, body); else await repo.createPoint(body);
      done(p ? 'Punto actualizado' : 'Punto creado')(close);
    });
  });

  const staffForm = () => modal(staffFormView(), (root, close) => {
    $('#cx', root).onclick = close;
    $('#sv', root).onclick = guard(async () => {
      await repo.createStaff({ name: $('#f-name', root).value, username: $('#f-user', root).value, password: $('#f-pass', root).value });
      done('Personal registrado. Ahora asignale un horario')(close);
    });
  });

  const passwordForm = (u) => modal(passwordFormView(u), (root, close) => {
    $('#cx', root).onclick = close;
    $('#sv', root).onclick = guard(async () => {
      await repo.patchStaff(u.id, { password: $('#f-pass', root).value });
      done('Clave actualizada')(close);
    });
  });

  const shiftForm = (pre = {}) => {
    if (!data.staff.length) { toast('Primero registra al personal', 'error'); return; }
    if (!data.points.length) { toast('Primero crea un punto', 'error'); return; }
    modal(shiftFormView(data, pre), (root, close) => {
      const chips = $$('#f-days .chip-toggle', root);
      chips.forEach((c) => { c.onclick = () => c.classList.toggle('on'); });
      const setDays = (list) => chips.forEach((c) => c.classList.toggle('on', list.includes(+c.dataset.day)));
      const Q = { weekdays: [0, 1, 2, 3, 4], all: [0, 1, 2, 3, 4, 5, 6], weekend: [5, 6] };
      $$('.quick a', root).forEach((a) => { a.onclick = (e) => { e.preventDefault(); setDays(Q[a.dataset.q]); }; });
      $('#cx', root).onclick = close;
      $('#sv', root).onclick = guard(async () => {
        await repo.createShift({
          user_id: +$('#f-user', root).value, point_id: +$('#f-point', root).value,
          weekdays: chips.filter((c) => c.classList.contains('on')).map((c) => +c.dataset.day),
          start: $('#f-start', root).value, end: $('#f-end', root).value,
        });
        done('Horario asignado')(close);
      });
    });
  };

  const confirm = (title, text, label, action, okMsg) => modal(confirmView(title, text, label), (root, close) => {
    $('#cx', root).onclick = close;
    $('#yes', root).onclick = guard(async () => { await action(); done(okMsg)(close); });
  });

  // ---------------------------------------------------------- enlaces de la pantalla
  function bind() {
    const point = (id) => data.points.find((p) => p.id === +id);
    const staff = (id) => data.staff.find((u) => u.id === +id);
    $$('[data-edit-point]').forEach((b) => { b.onclick = () => pointForm(point(b.dataset.editPoint)); });
    $$('[data-shift-point]').forEach((b) => { b.onclick = () => shiftForm({ pointId: +b.dataset.shiftPoint }); });
    $$('[data-shift-user]').forEach((b) => { b.onclick = () => shiftForm({ userId: +b.dataset.shiftUser }); });
    $$('[data-pw]').forEach((b) => { b.onclick = () => passwordForm(staff(b.dataset.pw)); });
    $$('[data-toggle-point]').forEach((b) => {
      b.onclick = guard(async () => {
        const p = point(b.dataset.togglePoint);
        await repo.patchPoint(p.id, { enabled: !p.enabled });
        toast(p.enabled ? `${p.name} cerrado` : `${p.name} abierto`, 'ok');
        load();
      });
    });
    $$('[data-del-point]').forEach((b) => {
      const p = point(b.dataset.delPoint);
      b.onclick = () => confirm(`Eliminar ${p.name}`, 'Se elimina el punto y sus horarios. Solo es posible si nunca atendio turnos; si ya tiene historial, ciérralo en su lugar.', 'Eliminar', () => repo.deletePoint(p.id), 'Punto eliminado');
    });
    $$('[data-del-staff]').forEach((b) => {
      const u = staff(b.dataset.delStaff);
      b.onclick = () => confirm(`Eliminar a ${u.name}`, 'Se elimina su usuario y todos sus horarios.', 'Eliminar', () => repo.deleteStaff(u.id), 'Personal eliminado');
    });
    $$('[data-del-shift]').forEach((b) => {
      b.onclick = guard(async () => { await repo.deleteShift(+b.dataset.delShift); toast('Horario quitado', 'ok'); load(); });
    });
  }

  $('#new-point').onclick = () => data && pointForm(null);
  $('#new-staff').onclick = staffForm;
  $('#new-shift').onclick = () => data && shiftForm();
  poll(load, 15000);
}
