/* Formateo de tiempos y textos. */
export const mins = (m) => (m == null ? '-' : m < 1 ? 'ya' : `${m} min`);
export const dur = (m) => (m == null ? '-' : `${m < 10 ? m.toFixed(1) : Math.round(m)} min`);
export const timeOf = (iso) => (iso ? new Date(iso).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }) : '-');
export const greeting = () => {
  const h = new Date().getHours();
  return h < 12 ? 'Buenos dias' : h < 19 ? 'Buenas tardes' : 'Buenas noches';
};
export const dateStr = () => new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });
