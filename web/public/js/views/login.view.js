/* VISTA: inicio de sesion. */
import { ic } from '../core/icons.js';
import { BRAND } from './components.js';

export const DEMOS = [
  ['recepcion', 'recepcion123', 'Recepcion', 'Registra y asigna', 'clipboard'],
  ['medico1', 'medico123', 'Consultorio 1', 'Llama y atiende', 'steth'],
  ['medico2', 'medico123', 'Consultorio 2', 'Llama y atiende', 'steth'],
  ['supervisor', 'supervisor123', 'Supervision', 'Indicadores', 'chart'],
];

export const loginView = (demo = true) => `
  <div class="login-wrap">
    <section class="login-art"><div class="blob a"></div><div class="blob b"></div><div class="blob c"></div>
      ${BRAND}
      <h1>Menos espera,<br><span>mejor atencion.</span></h1>
      <p>Turnos en salud con prioridad automatica y una IA que sugiere el punto de atencion mas rapido para cada paciente.</p>
      <div class="floaters">
        <div class="floater f1"><small>Turno</small><b>CG-014</b></div>
        <div class="floater f2"><small>Espera estimada</small><b>~6 min</b></div>
        <div class="floater f3"><small>Prioridad</small><b>★ Preferencial</b></div>
      </div>
    </section>
    <section class="login-form"><div class="login-box">
      <h2>Bienvenido</h2>
      <p class="muted" style="margin-bottom:22px">Ingresa con tu usuario del centro de salud.</p>
      <form id="f">
        <div class="field"><label>Usuario</label><input type="text" id="u" autocomplete="username" required autofocus></div>
        <div class="field"><label>Contrasena</label><input type="password" id="p" autocomplete="current-password" required></div>
        <button class="btn big" style="width:100%" id="go">Entrar</button>
        <p class="err" id="err"></p>
      </form>
      ${demo ? `<div class="demo-title">Acceso rapido demo</div>
      <div class="demo-users">${DEMOS.map((d, i) => `<button type="button" data-i="${i}"><div class="avatar sm" style="--av:linear-gradient(135deg,#14b8a6,#0ea5e9)">${ic(d[4], 'sm')}</div><div><b>${d[2]}</b><span>${d[3]}</span></div></button>`).join('')}</div>` : ''}
      <div class="public-links"><a href="#/pantalla">${ic('monitor', 'sm')} Pantalla</a><a href="#/consulta">${ic('search', 'sm')} Consultar turno</a></div>
    </div></section>
  </div>`;
