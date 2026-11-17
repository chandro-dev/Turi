/* Arranque: router por hash + control de acceso por rol. */
import { $ } from './core/dom.js';
import { connectLive } from './core/live.js';
import { clearTimers } from './core/timers.js';
import { HOME } from './models/constants.js';
import { setUnauthorizedHandler } from './models/api.js';
import { session } from './models/session.js';
import { loginController, logout, restoreSession } from './controllers/auth.controller.js';
import { displayController } from './controllers/display.controller.js';
import { doctorController } from './controllers/doctor.controller.js';
import { lookupController } from './controllers/lookup.controller.js';
import { modelController } from './controllers/model.controller.js';
import { resourcesController } from './controllers/resources.controller.js';
import { queueController } from './controllers/queue.controller.js';
import { receptionController } from './controllers/reception.controller.js';
import { supervisorController } from './controllers/supervisor.controller.js';

const PUBLIC = { '#/login': loginController, '#/pantalla': displayController, '#/consulta': lookupController };
const PRIVATE = {
  '#/recepcion': [['RECEPCION'], receptionController],
  '#/medico': [['MEDICO'], doctorController],
  '#/supervisor': [['SUPERVISOR'], supervisorController],
  '#/fila': [['SUPERVISOR'], queueController],
  '#/modelo': [['SUPERVISOR'], modelController],
  '#/recursos': [['SUPERVISOR'], resourcesController],
};

async function route() {
  clearTimers();
  $('#modal-root').innerHTML = '';
  const h = location.hash || '#/';
  const user = await restoreSession();

  if (PUBLIC[h]) {
    if (h === '#/login' && user) { location.hash = HOME[user.role]; return; }
    PUBLIC[h]();
    return;
  }
  if (!user) { location.hash = '#/login'; return; }
  const entry = PRIVATE[h];
  if (!entry || !entry[0].includes(user.role)) { location.hash = HOME[user.role]; return; }
  entry[1]();
}

connectLive();
setUnauthorizedHandler(logout);
window.addEventListener('hashchange', route);
route();
