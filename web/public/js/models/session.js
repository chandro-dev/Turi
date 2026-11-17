/* MODELO: sesion del usuario (token + datos) persistida en localStorage. */
const KEY = 'turi_token';
let user = null;

export const session = {
  get token() { try { return localStorage.getItem(KEY); } catch { return null; } },
  set token(v) { try { v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY); } catch { /* sin storage */ } },
  get user() { return user; },
  set user(u) { user = u; },
  clear() { this.token = null; user = null; },
};
