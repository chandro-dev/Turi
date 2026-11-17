/* MODELO: acceso a datos. Un metodo por operacion de la API; los controladores no conocen URLs. */
import { api } from './api.js';

const post = (path, body) => api(path, { method: 'POST', body });

export const repo = {
  // sesion
  login: (username, password) => post('/auth/login', { username, password }),
  me: () => api('/auth/me'),
  // catalogos
  services: () => api('/services'),
  points: () => api('/points'),
  // recepcion
  turns: (includeClosed = false) => api(`/turns${includeClosed ? '?include_closed=true' : ''}`),
  suggest: (body) => post('/turns/suggest', body),
  createTurn: (body) => post('/turns', body),
  patchTurn: (id, body) => api(`/turns/${id}`, { method: 'PATCH', body }),
  cancelTurn: (id) => post(`/turns/${id}/cancel`),
  reassignTurn: (id, pointId) => post(`/turns/${id}/reassign`, { point_id: pointId }),
  // atencion
  doctorPanel: () => api('/doctor/panel'),
  doctorAction: (path) => post(path),
  setActive: (active) => post('/doctor/active', { active }),
  // supervision
  stats: () => api('/stats'),
  simulate: (count) => post('/demo/simulate', { count }),
  modelReport: () => api('/model/report'),
  modelPredict: (body) => post('/model/predict', body),
  // publico
  display: () => api('/public/display'),
  lookup: (q) => api('/public/lookup?q=' + encodeURIComponent(q)),
};
