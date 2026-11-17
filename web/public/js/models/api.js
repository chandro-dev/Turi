/* MODELO: cliente HTTP base. Adjunta el token y normaliza los errores a Error(message). */
import { session } from './session.js';

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

/** Extrae un mensaje legible de la respuesta de error de FastAPI. */
function errorMessage(data) {
  const d = data && data.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d.length) {
    const msg = d[0].msg || '';
    return msg.replace(/^Value error,\s*/, '') || 'Revisa los datos ingresados';
  }
  return 'Error inesperado';
}

export async function api(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (session.token) headers.Authorization = 'Bearer ' + session.token;
  let res;
  try {
    res = await fetch('/api' + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new Error('Sin conexion con el servidor');
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && session.token) onUnauthorized();
    throw new Error(errorMessage(data));
  }
  return data;
}
