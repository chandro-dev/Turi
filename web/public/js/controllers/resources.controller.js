/* CONTROLADOR: administracion (servicios, consultorios/laboratorios, usuarios y horarios). */
import { $, $$, guard, modal, toast } from '../core/dom.js';
import { poll } from '../core/timers.js';
import { repo } from '../models/repository.js';
import { session } from '../models/session.js';
import {
  confirmView, overviewView, passwordFormView, pointFormView, resourcesShell, serviceFormView, shiftFormView,
  userEditView, userFormView,
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
  const done = (msg, close) => { close(); toast(msg, 'ok'); load(); };

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
      done(p ? 'Punto actualizado' : 'Punto creado', close);
    });
  });

  const serviceForm = (s) => modal(serviceFormView(s), (root, close) => {
    $('#cx', root).onclick = close;
    $('#sv', root).onclick = guard(async () => {
      const body = { name: $('#f-name', root).value, prior_minutes: +$('#f-prior', root).value, color: $('#f-color', root).value };
      if (s) await repo.patchService(s.id, body);
      else await repo.createService({ ...body, code: $('#f-code', root).value });
      done(s ? 'Servicio actualizado' : 'Servicio creado. Ya puedes asignarlo a un punto', close);
    });
  });

  const userForm = () => modal(userFormView(), (root, close) => {
    $('#cx', root).onclick = close;
    $('#sv', root).onclick = guard(async () => {
      const role = $('#f-role', root).value;
      await repo.createUser({ name: $('#f-name', root).value, username: $('#f-user', root).value, password: $('#f-pass', root).value, role });
      done(role === 'MEDICO' ? 'Usuario creado. Ahora asignale un horario' : 'Usuario creado', close);
    });
  });

  const userEdit = (u) => modal(userEditView(u, u.id === session.user.id), (root, close) => {
    if (u.id === session.user.id) $('#f-role', root).disabled = true;
    $('#cx', root).onclick = close;
    $('#sv', root).onclick = guard(async () => {
      const body = { name: $('#f-name', root).value };
      if (u.id !== session.user.id) body.role = $('#f-role', root).value;
      await repo.patchUser(u.id, body);
      done('Usuario actualizado', close);
    });
  });

  const passwordForm = (u) => modal(passwordFormView(u), (root, close) => {
    $('#cx', root).onclick = close;
    $('#sv', root).onclick = guard(async () => {
      await repo.patchUser(u.id, { password: $('#f-pass', root).value });
      done('Clave actualizada', close);
    });
  });

  const shiftForm = (pre = {}) => {
    if (!data.users.some((u) => u.role === 'MEDICO' && u.active)) { toast('Primero registra personal de atencion', 'error'); return; }
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
        done('Horario asignado', close);
      });
    });
  };

  const confirm = (title, text, label, action, okMsg) => modal(confirmView(title, text, label), (root, close) => {
    $('#cx', root).onclick = close;
    $('#yes', root).onclick = guard(async () => { await action(); done(okMsg, close); });
  });

  // ---------------------------------------------------------- enlaces de la pantalla
  function bind() {
    const point = (id) => data.points.find((p) => p.id === +id);
    const user = (id) => data.users.find((u) => u.id === +id);
    const service = (id) => data.services.find((s) => s.id === +id);
    $$('[data-edit-point]').forEach((b) => { b.onclick = () => pointForm(point(b.dataset.editPoint)); });
    $$('[data-shift-point]').forEach((b) => { b.onclick = () => shiftForm({ pointId: +b.dataset.shiftPoint }); });
    $$('[data-shift-user]').forEach((b) => { b.onclick = () => shiftForm({ userId: +b.dataset.shiftUser }); });
    $$('[data-edit-service]').forEach((b) => { b.onclick = () => serviceForm(service(b.dataset.editService)); });
    $$('[data-edit-user]').forEach((b) => { b.onclick = () => userEdit(user(b.dataset.editUser)); });
    $$('[data-pw]').forEach((b) => { b.onclick = () => passwordForm(user(b.dataset.pw)); });
    $$('[data-toggle-point]').forEach((b) => {
      b.onclick = guard(async () => {
        const p = point(b.dataset.togglePoint);
        await repo.patchPoint(p.id, { enabled: !p.enabled });
        toast(p.enabled ? `${p.name} cerrado` : `${p.name} abierto`, 'ok');
        load();
      });
    });
    $$('[data-toggle-user]').forEach((b) => {
      b.onclick = guard(async () => {
        const u = user(b.dataset.toggleUser);
        await repo.patchUser(u.id, { active: !u.active });
        toast(u.active ? `${u.name} desactivado` : `${u.name} activado`, 'ok');
        load();
      });
    });
    $$('[data-del-point]').forEach((b) => {
      const p = point(b.dataset.delPoint);
      b.onclick = () => confirm(`Eliminar ${p.name}`, 'Se elimina el punto y sus horarios. Solo es posible si nunca atendio turnos; si ya tiene historial, ciérralo en su lugar.', 'Eliminar', () => repo.deletePoint(p.id), 'Punto eliminado');
    });
    $$('[data-del-service]').forEach((b) => {
      const s = service(b.dataset.delService);
      b.onclick = () => confirm(`Eliminar ${s.name}`, 'Solo es posible si el servicio nunca tuvo turnos y ningun punto lo atiende.', 'Eliminar', () => repo.deleteService(s.id), 'Servicio eliminado');
    });
    $$('[data-del-user]').forEach((b) => {
      const u = user(b.dataset.delUser);
      b.onclick = () => confirm(`Eliminar a ${u.name}`, 'Se elimina su usuario y todos sus horarios. Si solo quieres que no entre mas, desactivalo.', 'Eliminar', () => repo.deleteUser(u.id), 'Usuario eliminado');
    });
    $$('[data-del-shift]').forEach((b) => {
      b.onclick = guard(async () => { await repo.deleteShift(+b.dataset.delShift); toast('Horario quitado', 'ok'); load(); });
    });
  }

  $('#new-point').onclick = () => data && pointForm(null);
  $('#new-service').onclick = () => serviceForm(null);
  $('#new-user').onclick = userForm;
  $('#new-shift').onclick = () => data && shiftForm();
  poll(load, 15000);
}
