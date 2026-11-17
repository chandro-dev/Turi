/* CONTROLADOR auxiliar: pinta la estructura comun y devuelve el contenedor de la pagina. */
import { $ } from '../core/dom.js';
import { session } from '../models/session.js';
import { shellView } from '../views/layout.js';
import { logout } from './auth.controller.js';

export function mountShell(content, active) {
  $('#app').innerHTML = shellView(session.user, content, active);
  $('#logout').onclick = logout;
  return $('#page');
}
