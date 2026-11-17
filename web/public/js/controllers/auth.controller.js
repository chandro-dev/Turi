/* CONTROLADOR: login, cierre de sesion y restauracion de sesion. */
import { $, $$ } from '../core/dom.js';
import { clearTimers } from '../core/timers.js';
import { HOME } from '../models/constants.js';
import { repo } from '../models/repository.js';
import { session } from '../models/session.js';
import { DEMOS, loginView } from '../views/login.view.js';

export function logout() {
  session.clear();
  clearTimers();
  location.hash = '#/login';
}

export async function restoreSession() {
  if (session.token && !session.user) {
    try { session.user = await repo.me(); } catch { session.clear(); }
  }
  return session.user;
}

export function loginController() {
  $('#app').innerHTML = loginView();
  const submit = async (username, password) => {
    $('#go').disabled = true;
    $('#err').textContent = '';
    try {
      const r = await repo.login(username, password);
      session.token = r.token;
      session.user = r.user;
      location.hash = HOME[r.user.role];
    } catch (e) {
      $('#err').textContent = e.message;
    } finally {
      const b = $('#go');
      if (b) b.disabled = false;
    }
  };
  $('#f').onsubmit = (e) => { e.preventDefault(); submit($('#u').value, $('#p').value); };
  $$('.demo-users button').forEach((b) => {
    b.onclick = () => { const d = DEMOS[+b.dataset.i]; submit(d[0], d[1]); };
  });
}
