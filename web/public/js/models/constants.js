/* MODELO: catalogos y constantes de dominio del cliente. */
export const STATUS = {
  WAITING: 'En espera', CALLED: 'Llamado', IN_SERVICE: 'En atencion', DONE: 'Atendido',
  CANCELLED: 'Cancelado', NO_SHOW: 'No se presento',
};
export const STATUS_COLOR = {
  WAITING: '#0ea5e9', CALLED: '#f59e0b', IN_SERVICE: '#16a34a', DONE: '#94a3b8', CANCELLED: '#e11d48', NO_SHOW: '#8b5cf6',
};
export const ACTIVE_STATUSES = ['WAITING', 'CALLED', 'IN_SERVICE', 'NO_SHOW'];
export const ROLE = { RECEPCION: 'Recepcion', MEDICO: 'Atencion', SUPERVISOR: 'Supervision' };
export const HOME = { RECEPCION: '#/recepcion', MEDICO: '#/medico', SUPERVISOR: '#/supervisor' };
