/* Formateo de tiempos y textos. */
const round = (m, d) => { const f = 10 ** d; return Math.round(m * f) / f; };

/** Minutos legibles: "45 min"; a partir de 60 min pasa a horas ("1 h", "1 h 15 min"). */
export function fmtMin(m, decimals = 0) {
  if (m == null || Number.isNaN(m)) return '-';
  const v = round(m, decimals);
  if (v < 60) return `${v} min`;
  let h = Math.floor(v / 60);
  let r = Math.round(v - h * 60);
  if (r === 60) { h += 1; r = 0; }
  return r ? `${h} h ${r} min` : `${h} h`;
}

/** Version partida para cifras grandes: ["25", "min"] o ["1 h 15", "min"] / ["2", "h"]. */
export function minParts(m) {
  if (m == null) return ['-', ''];
  const v = Math.round(m);
  if (v < 60) return [String(v), 'min'];
  const h = Math.floor(v / 60);
  const r = v - h * 60;
  return r ? [`${h} h ${r}`, 'min'] : [String(h), 'h'];
}

export const mins = (m) => (m == null ? '-' : m < 1 ? 'ya' : fmtMin(m));
export const dur = (m) => (m == null ? '-' : fmtMin(m, m < 10 ? 1 : 0));
export const timeOf = (iso) => (iso ? new Date(iso).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }) : '-');
export const greeting = () => {
  const h = new Date().getHours();
  return h < 12 ? 'Buenos dias' : h < 19 ? 'Buenas tardes' : 'Buenas noches';
};
export const dateStr = () => new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });
