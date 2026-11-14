/* Turi - MVP frontend (vanilla JS, sin build) */
(() => {
  'use strict';

  // ------------------------------------------------------------ utils
  const $ = (sel, el = document) => el.querySelector(sel);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const store = {
    get token() { try { return localStorage.getItem('turi_token'); } catch { return null; } },
    set token(v) { try { v ? localStorage.setItem('turi_token', v) : localStorage.removeItem('turi_token'); } catch { /* ignore */ } },
  };
  let user = null;
  let timers = [];
  const clearTimers = () => { timers.forEach(clearInterval); timers = []; };
  const poll = (fn, ms) => { fn(); timers.push(setInterval(fn, ms)); };

  const STATUS = {
    WAITING: 'En espera', CALLED: 'Llamado', IN_SERVICE: 'En atencion', DONE: 'Atendido',
    CANCELLED: 'Cancelado', NO_SHOW: 'No se presento',
  };
  const STATUS_COLOR = { WAITING: '#0ea5e9', CALLED: '#f59e0b', IN_SERVICE: '#16a34a', DONE: '#94a3b8', CANCELLED: '#e11d48', NO_SHOW: '#8b5cf6' };
  const ROLE = { RECEPCION: 'Recepcion', MEDICO: 'Atencion', SUPERVISOR: 'Supervision' };

  const ICONS = {
    clipboard: '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11v6M9 14h6"/>',
    steth: '<path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6 6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3"/><path d="M8 15v1a6 6 0 0 0 6 6 6 6 0 0 0 6-6v-4"/><circle cx="20" cy="10" r="2"/>',
    chart: '<path d="M3 3v18h18"/><path d="M7 15v3M12 10v8M17 6v12"/>',
    monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
    spark: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 17v4M17 19h4"/>',
    star: '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
    check: '<path d="m5 12 5 5L20 7"/>',
    bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
    activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    flask: '<path d="M9 3h6M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2.2h12.4a1.5 1.5 0 0 0 1.3-2.2L14 9V3"/><path d="M7.5 15h9"/>',
    pill: '<path d="m10.5 20.5-7-7a4.95 4.95 0 0 1 7-7l7 7a4.95 4.95 0 0 1-7 7z"/><path d="m8.5 8.5 7 7"/>',
    smile: '<circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    play: '<path d="m6 4 14 8-14 8z"/>',
    pause: '<path d="M8 5v14M16 5v14"/>',
    coffee: '<path d="M17 8h1a4 4 0 0 1 0 8h-1M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4z"/><path d="M6 2v3M10 2v3M14 2v3"/>',
    undo: '<path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-15-6.7L3 13"/>',
    swap: '<path d="m16 3 4 4-4 4M20 7H4M8 21l-4-4 4-4M4 17h16"/>',
    edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    ticket: '<path d="M3 9a2 2 0 0 0 0 6v3a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-3a2 2 0 0 1 0-6V6a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1z"/><path d="M13 5v14" stroke-dasharray="2 3"/>',
    alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    trend: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
  };
  const ic = (n, cls = '') => `<svg class="i ${cls}" viewBox="0 0 24 24">${ICONS[n] || ''}</svg>`;
  const SERVICE_ICON = { CG: 'steth', LAB: 'flask', FAR: 'pill', ODO: 'smile' };
  const initials = (n) => n.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');

  async function api(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (store.token) headers.Authorization = 'Bearer ' + store.token;
    let res;
    try {
      res = await fetch('/api' + path, { ...opts, headers, body: opts.body ? JSON.stringify(opts.body) : undefined });
    } catch {
      throw new Error('Sin conexion con el servidor');
    }
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (res.status === 401 && store.token) { logout(); }
      const d = data.detail;
      throw new Error(typeof d === 'string' ? d : Array.isArray(d) ? 'Revisa los datos ingresados' : 'Error inesperado');
    }
    return data;
  }

  function toast(msg, kind = '') {
    const el = document.createElement('div');
    el.className = 'toast ' + kind;
    el.textContent = msg;
    $('#toasts').appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }
  const guard = (fn) => async (...a) => { try { return await fn(...a); } catch (e) { toast(e.message, 'error'); } };

  function modal(html, onMount, cls = '') {
    const root = $('#modal-root');
    root.innerHTML = `<div class="overlay"><div class="modal ${cls}">${html}</div></div>`;
    const close = () => { root.innerHTML = ''; };
    $('.overlay', root).addEventListener('mousedown', (e) => { if (e.target.classList.contains('overlay')) close(); });
    onMount && onMount(root, close);
    return close;
  }

  const mins = (m) => (m == null ? '-' : m < 1 ? 'ya' : `${m} min`);
  const timeOf = (iso) => (iso ? new Date(iso).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }) : '-');
  const prioBadge = (t) => {
    if (t.priority_class === 'PREFERENCIAL') return `<span class="badge b-pref" title="${esc(t.priority_reasons.join(', '))}">${ic('star', 'sm')} Preferencial</span>`;
    if (t.priority_class === 'BAJA') return '<span class="badge b-low">Reincorporado</span>';
    return '';
  };
  const statusBadge = (s) => `<span class="badge b-${s}">${STATUS[s] || s}</span>`;
  const BRAND = `<div class="brand"><div class="brand-mark"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"><path d="M5 7h14M12 7v12"/></svg></div><span>Turi</span></div>`;
  const greeting = () => { const h = new Date().getHours(); return h < 12 ? 'Buenos dias' : h < 19 ? 'Buenas tardes' : 'Buenas noches'; };
  const dateStr = () => new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });

  // ------------------------------------------------------------ auth / shell
  function logout() {
    store.token = null; user = null; clearTimers();
    location.hash = '#/login';
  }

  const NAV = {
    RECEPCION: [['#/recepcion', 'Recepcion', 'clipboard'], ['#/consulta', 'Consulta paciente', 'search'], ['#/pantalla', 'Pantalla de turnos', 'monitor']],
    MEDICO: [['#/medico', 'Mi consultorio', 'steth'], ['#/pantalla', 'Pantalla de turnos', 'monitor']],
    SUPERVISOR: [['#/supervisor', 'Indicadores', 'chart'], ['#/recepcion', 'Fila general', 'clipboard'], ['#/consulta', 'Consulta paciente', 'search'], ['#/pantalla', 'Pantalla de turnos', 'monitor']],
  };
  const HOME = { RECEPCION: '#/recepcion', MEDICO: '#/medico', SUPERVISOR: '#/supervisor' };

  function shell(content, active) {
    const links = NAV[user.role].map(([h, l, i]) => `<a href="${h}" class="${h === active ? 'active' : ''}" title="${l}">${ic(i)}<span>${l}</span></a>`).join('');
    $('#app').innerHTML = `
      <div class="app">
        <aside class="side">${BRAND}
          <nav class="nav"><div class="nav-label">Menu</div>${links}</nav>
          <div class="side-user"><div class="avatar sm" style="--av:linear-gradient(135deg,#14b8a6,#4f46e5)">${esc(initials(user.name))}</div>
            <div class="who"><b>${esc(user.name)}</b><span>${ROLE[user.role]}${user.point ? ' · ' + esc(user.point.name) : ''}</span></div>
            <button class="icon-btn" id="logout" title="Cerrar sesion">${ic('logout', 'sm')}</button></div>
        </aside>
        <main class="main"><div class="page" id="page">${content}</div></main>
      </div>`;
    $('#logout').onclick = logout;
    return $('#page');
  }
  const head = (title, sub, right = '') => `<div class="page-head"><div><div class="eyebrow">${esc(dateStr())}</div><h1>${title}</h1><div class="sub">${sub}</div></div>${right}</div>`;

  // ------------------------------------------------------------ login
  function viewLogin() {
    const demos = [
      ['recepcion', 'recepcion123', 'Recepcion', 'Registra y asigna', 'clipboard'],
      ['medico1', 'medico123', 'Consultorio 1', 'Llama y atiende', 'steth'],
      ['medico2', 'medico123', 'Consultorio 2', 'Llama y atiende', 'steth'],
      ['supervisor', 'supervisor123', 'Supervision', 'Indicadores', 'chart'],
    ];
    $('#app').innerHTML = `
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
          <div class="demo-title">Acceso rapido demo</div>
          <div class="demo-users">${demos.map((d, i) => `<button type="button" data-i="${i}"><div class="avatar sm" style="--av:linear-gradient(135deg,#14b8a6,#0ea5e9)">${ic(d[4], 'sm')}</div><div><b>${d[2]}</b><span>${d[3]}</span></div></button>`).join('')}</div>
          <div class="public-links"><a href="#/pantalla">${ic('monitor', 'sm')} Pantalla</a><a href="#/consulta">${ic('search', 'sm')} Consultar turno</a></div>
        </div></section>
      </div>`;
    const submit = async (u, p) => {
      $('#go').disabled = true; $('#err').textContent = '';
      try {
        const r = await api('/auth/login', { method: 'POST', body: { username: u, password: p } });
        store.token = r.token; user = r.user;
        location.hash = HOME[user.role];
      } catch (e) { $('#err').textContent = e.message; } finally { const b = $('#go'); if (b) b.disabled = false; }
    };
    $('#f').onsubmit = (e) => { e.preventDefault(); submit($('#u').value, $('#p').value); };
    document.querySelectorAll('.demo-users button').forEach((b) => {
      b.onclick = () => { const d = demos[+b.dataset.i]; submit(d[0], d[1]); };
    });
  }

  // ------------------------------------------------------------ reception
  function viewReception() {
    const canEdit = user.role === 'RECEPCION';
    const st = { services: [], points: [], service: null, point: null, flags: { pregnant: false, disability: false }, turns: [], filter: 'all', seq: 0 };
    shell(`
      ${head(canEdit ? `${greeting()}, ${esc(user.name.split(' ')[0])}` : 'Fila general', canEdit ? 'Registra la llegada y deja que la IA sugiera el mejor punto.' : 'Vista de solo lectura de todos los turnos activos.')}
      <div class="grid-2" ${canEdit ? '' : 'style="grid-template-columns:1fr"'}>
        <section class="card ${canEdit ? '' : 'hide'}" id="form-card">
          <div class="card-head"><h2><span class="ic">${ic('plus')}</span>Nuevo ingreso</h2></div>
          <form id="nf" autocomplete="off">
            <div class="step"><i>1</i>Datos del paciente<span class="line"></span></div>
            <div class="row">
              <div class="field"><label>Documento</label><input type="text" id="doc" inputmode="numeric" placeholder="1.065.000.000" required></div>
              <div class="field" style="max-width:110px"><label>Edad</label><input type="number" id="age" min="0" max="120" required></div>
            </div>
            <div class="field"><label>Nombre completo</label><input type="text" id="name" required></div>
            <div class="field"><label>Telefono (opcional)</label><input type="text" id="phone"></div>
            <div class="field"><label>Condiciones de prioridad</label>
              <div class="chips">
                <span class="chip-toggle" data-flag="pregnant">${ic('star', 'sm')} Gestante</span>
                <span class="chip-toggle" data-flag="disability">${ic('star', 'sm')} Discapacidad</span>
              </div>
            </div>
            <div class="step" style="margin-top:22px"><i>2</i>Servicio<span class="line"></span></div>
            <div class="service-tiles" id="tiles" style="margin-bottom:20px"></div>
            <div id="sugg"></div>
            <button class="btn big" style="width:100%" id="submit" disabled>${ic('ticket')} Generar turno</button>
          </form>
        </section>
        <section class="card">
          <div class="card-head"><h2><span class="ic">${ic('users')}</span>Fila en tiempo real</h2><div class="tabs" id="tabs"></div></div>
          <div id="queue"></div>
        </section>
      </div>`, '#/recepcion');

    const formData = () => ({
      doc_number: $('#doc').value.trim(), patient_name: $('#name').value.trim(), phone: $('#phone').value.trim() || null,
      age: parseInt($('#age').value, 10), pregnant: st.flags.pregnant, disability: st.flags.disability,
    });
    const formReady = () => { const d = formData(); return d.doc_number.length >= 3 && d.patient_name.length >= 2 && Number.isInteger(d.age) && d.age >= 0 && st.service; };

    function renderTiles() {
      $('#tiles').innerHTML = st.services.map((s) => `
        <button type="button" class="tile ${st.service === s.code ? 'on' : ''}" data-c="${s.code}" style="--tile:${s.color}">
          <div class="tic">${ic(SERVICE_ICON[s.code] || 'activity')}</div>
          <div><b>${esc(s.name)}</b><small>~${s.prior_minutes} min por paciente</small></div></button>`).join('');
      document.querySelectorAll('.tile').forEach((b) => { b.onclick = () => { st.service = b.dataset.c; st.point = null; renderTiles(); refreshSuggestion(); }; });
    }

    let debounce;
    function refreshSuggestion() {
      clearTimeout(debounce);
      $('#submit').disabled = true;
      if (!st.service || !Number.isInteger(parseInt($('#age').value, 10))) { $('#sugg').innerHTML = st.service ? '<div class="notice info">Ingresa la edad para calcular la prioridad y sugerir un punto.</div>' : ''; return; }
      debounce = setTimeout(guard(async () => {
        const seq = ++st.seq;
        const d = formData();
        const r = await api('/turns/suggest', { method: 'POST', body: { service_code: st.service, age: d.age || 0, pregnant: d.pregnant, disability: d.disability } });
        if (seq !== st.seq) return;
        st.sugg = r;
        if (!st.point || !r.options.find((o) => o.point_id === st.point)) st.point = r.options[0]?.point_id ?? null;
        renderSuggestion();
      }), 250);
    }

    function renderSuggestion() {
      const r = st.sugg;
      let html = '';
      if (r.priority_class === 'PREFERENCIAL') html += `<div class="notice">${ic('star')} Atencion preferencial: ${esc(r.priority_reasons.join(' · '))}</div>`;
      if (!r.options.length) html += `<div class="notice">${ic('alert')} No hay puntos disponibles para este servicio.</div>`;
      else {
        const max = Math.max(1, ...r.options.map((o) => o.est_wait_min));
        html += `<div class="ai-box"><div class="ai-title">${ic('spark')} Sugerencia de IA<small>${r.model === 'respaldo-basico' ? 'estimacion basica' : 'aprende de cada atencion'}</small></div>
          <div class="options">${r.options.map((o) => `
          <div class="opt ${o.point_id === st.point ? 'on' : ''}" data-p="${o.point_id}">
            <div class="nm"><b>${esc(o.name)}</b> ${o.recommended ? `<span class="badge b-ai">${ic('spark', 'sm')} Recomendado</span>` : ''}</div>
            <div class="eta"><b>${Math.round(o.est_wait_min)}</b><small>min</small></div>
            <div class="meta">${esc(o.reason)}</div>
            <div class="meter"><i style="width:${Math.max(6, (o.est_wait_min / max) * 100)}%"></i></div>
          </div>`).join('')}</div></div>`;
      }
      $('#sugg').innerHTML = html;
      document.querySelectorAll('.opt').forEach((o) => { o.onclick = () => { st.point = +o.dataset.p; renderSuggestion(); }; });
      $('#submit').disabled = !(formReady() && st.point);
    }

    if (canEdit) {
      document.querySelectorAll('.chip-toggle').forEach((c) => {
        c.onclick = () => { const f = c.dataset.flag; st.flags[f] = !st.flags[f]; c.classList.toggle('on', st.flags[f]); refreshSuggestion(); };
      });
      ['doc', 'name'].forEach((id) => { $('#' + id).oninput = () => { if (st.sugg) renderSuggestion(); }; });
      $('#age').oninput = refreshSuggestion;
      $('#nf').onsubmit = guard(async (e) => {
        e.preventDefault();
        if (!formReady() || !st.point) return;
        $('#submit').disabled = true;
        try {
          const t = await api('/turns', { method: 'POST', body: { ...formData(), service_code: st.service, point_id: st.point } });
          showTicket(t);
          $('#nf').reset(); st.flags = { pregnant: false, disability: false }; st.service = null; st.point = null; st.sugg = null;
          document.querySelectorAll('.chip-toggle').forEach((c) => c.classList.remove('on'));
          renderTiles(); $('#sugg').innerHTML = '';
          loadQueue();
        } catch (err) { $('#submit').disabled = false; throw err; }
      });
    }

    function showTicket(t) {
      modal(`
        <div class="top">
          <div style="font-weight:800;letter-spacing:.18em;font-size:13px;opacity:.85">TURNO ASIGNADO</div>
          <div class="big-code">${esc(t.code)}</div>
          <div style="font-size:19px;font-weight:700">${esc(t.patient_name)}</div>
          <div style="opacity:.85">${esc(t.service.name)}${t.priority_class === 'PREFERENCIAL' ? ' · ★ Preferencial' : ''}</div>
        </div>
        <div class="bottom">
          <div class="line">
            <div><b>${esc(t.point.name)}</b><small>Punto</small></div>
            <div><b>#${t.position ?? '-'}</b><small>En la fila</small></div>
            <div><b>${mins(t.eta_min)}</b><small>Espera aprox.</small></div>
          </div>
          <button class="btn big" id="ok" style="width:100%">Listo, siguiente paciente</button>
        </div>`,
      (root, close) => { $('#ok', root).onclick = close; $('#ok', root).focus(); }, 'ticket-modal');
    }

    // ---- queue
    const reassign = (t) => {
      const opts = st.points.filter((p) => p.services.includes(t.service.code));
      const requeue = t.status === 'NO_SHOW';
      modal(`<h2>${requeue ? 'Reincorporar' : 'Reasignar'} ${esc(t.code)}</h2>
        <p class="muted" style="margin-bottom:14px">${requeue ? 'El paciente vuelve a la fila con prioridad baja.' : 'Elige el nuevo punto de atencion.'}</p>
        <div class="options">${opts.map((p) => `<div class="opt ${p.id === t.point.id ? 'on' : ''}" data-p="${p.id}">
          <div class="nm"><b>${esc(p.name)}</b></div><div class="eta"><b>${p.waiting}</b><small>en fila</small></div>
          <div class="meta">${p.active ? 'Disponible' : 'En pausa'}</div></div>`).join('')}</div>
        <div class="foot"><button class="btn ghost" id="cx">Cancelar</button></div>`,
      (root, close) => {
        $('#cx', root).onclick = close;
        root.querySelectorAll('.opt').forEach((o) => { o.onclick = guard(async () => {
          await api(`/turns/${t.id}/reassign`, { method: 'POST', body: { point_id: +o.dataset.p } });
          close(); toast(requeue ? 'Paciente reincorporado' : 'Turno reasignado', 'ok'); loadQueue();
        }); });
      });
    };
    const edit = (t) => {
      const fl = { pregnant: t.pregnant, disability: t.disability };
      modal(`<h2>Editar ${esc(t.code)}</h2>
        <div class="field"><label>Nombre</label><input type="text" id="en" value="${esc(t.patient_name)}"></div>
        <div class="row"><div class="field"><label>Documento</label><input type="text" id="ed" value="${esc(t.doc_number)}"></div>
        <div class="field"><label>Edad</label><input type="number" id="ea" value="${t.age}" min="0" max="120"></div></div>
        <div class="field"><label>Telefono</label><input type="text" id="ep" value="${esc(t.phone || '')}"></div>
        <div class="chips"><span class="chip-toggle ${fl.pregnant ? 'on' : ''}" data-f="pregnant">Gestante</span>
        <span class="chip-toggle ${fl.disability ? 'on' : ''}" data-f="disability">Discapacidad</span></div>
        <div class="foot"><button class="btn ghost" id="cx">Cancelar</button><button class="btn" id="sv">Guardar</button></div>`,
      (root, close) => {
        root.querySelectorAll('.chip-toggle').forEach((c) => { c.onclick = () => { fl[c.dataset.f] = !fl[c.dataset.f]; c.classList.toggle('on', fl[c.dataset.f]); }; });
        $('#cx', root).onclick = close;
        $('#sv', root).onclick = guard(async () => {
          await api(`/turns/${t.id}`, { method: 'PATCH', body: { patient_name: $('#en', root).value, doc_number: $('#ed', root).value, age: +$('#ea', root).value, phone: $('#ep', root).value, ...fl } });
          close(); toast('Turno actualizado', 'ok'); loadQueue();
        });
      });
    };
    const cancel = (t) => modal(`<h2>Cancelar ${esc(t.code)}</h2><p>Se retirara a <b>${esc(t.patient_name)}</b> de la fila. Esta accion no se puede deshacer.</p>
      <div class="foot"><button class="btn ghost" id="cx">Volver</button><button class="btn danger" id="yes">Cancelar turno</button></div>`,
    (root, close) => {
      $('#cx', root).onclick = close;
      $('#yes', root).onclick = guard(async () => { await api(`/turns/${t.id}/cancel`, { method: 'POST' }); close(); toast('Turno cancelado'); loadQueue(); });
    });

    function renderQueue() {
      const tabs = [{ id: 'all', name: 'Todos' }, ...st.points.map((p) => ({ id: String(p.id), name: p.name }))];
      $('#tabs').innerHTML = tabs.map((t) => `<button class="tab ${st.filter === t.id ? 'on' : ''}" data-f="${t.id}">${esc(t.name)}</button>`).join('');
      document.querySelectorAll('.tab').forEach((b) => { b.onclick = () => { st.filter = b.dataset.f; renderQueue(); }; });
      const rank = { IN_SERVICE: 0, CALLED: 1, WAITING: 2, NO_SHOW: 3 };
      const list = st.turns
        .filter((t) => st.filter === 'all' || String(t.point.id) === st.filter)
        .sort((a, b) => rank[a.status] - rank[b.status] || (a.position ?? 99) - (b.position ?? 99));
      if (!list.length) { $('#queue').innerHTML = `<div class="empty"><div class="ico">${ic('coffee')}</div><b>Sin turnos activos</b><br>Todo al dia por ahora.</div>`; return; }
      $('#queue').innerHTML = `<div class="tlist">${list.map((t) => `
        <div class="titem ${t.status === 'IN_SERVICE' ? 'live' : t.priority_class === 'PREFERENCIAL' ? 'hot' : ''}" data-id="${t.id}" style="--sc:${t.service.color}">
          <div class="avatar sm" style="--av:${t.service.color}">${esc(initials(t.patient_name))}</div>
          <div class="code">${esc(t.code)}</div>
          <div class="who"><b>${esc(t.patient_name)}</b><span>${esc(t.service.name)} · ${esc(t.point.name)}</span>
            <div class="tags">${statusBadge(t.status)} ${prioBadge(t)}</div></div>
          <div class="pos">${t.status === 'WAITING' ? `<b>#${t.position}</b><small>${t.eta_min < 1 ? 'siguiente' : '~' + mins(t.eta_min)}</small>` : `<small>${t.status === 'NO_SHOW' ? 'por reingresar' : 'desde ' + timeOf(t.called_at)}</small>`}</div>
          ${canEdit && ['WAITING', 'NO_SHOW', 'CALLED'].includes(t.status) ? `<div class="acts">
            ${t.status === 'NO_SHOW' ? `<button class="btn sm amber" data-a="reassign">${ic('undo', 'sm')} Reincorporar</button>` : ''}
            ${t.status === 'WAITING' ? `<button class="btn sm soft" data-a="reassign">${ic('swap', 'sm')} Reasignar</button><button class="btn sm ghost" data-a="edit">${ic('edit', 'sm')} Editar</button>` : ''}
            <button class="btn sm danger" data-a="cancel">${ic('x', 'sm')} Cancelar</button>
          </div>` : ''}
        </div>`).join('')}</div>`;
      document.querySelectorAll('#queue [data-a]').forEach((b) => {
        const t = st.turns.find((x) => x.id === +b.closest('.titem').dataset.id);
        b.onclick = () => ({ reassign, edit, cancel }[b.dataset.a](t));
      });
    }

    const loadQueue = guard(async () => {
      [st.turns, st.points] = await Promise.all([api('/turns'), api('/points')]);
      renderQueue();
    });

    guard(async () => { st.services = await api('/services'); renderTiles(); })();
    poll(loadQueue, 4000);
  }

  // ------------------------------------------------------------ doctor
  function viewDoctor() {
    shell('<div id="doc"></div>', '#/medico');
    let busy = false;
    const act = (path) => guard(async () => {
      if (busy) return; busy = true;
      try { await api(path, { method: 'POST' }); await load(); } finally { busy = false; }
    });

    function render(d) {
      const cur = d.current;
      let stage;
      if (cur) {
        const calling = cur.status === 'CALLED';
        stage = `<div class="hero">
          <div class="eyebrow">${calling ? 'LLAMANDO AL PACIENTE' : 'EN ATENCION'}</div>
          <div class="big-code ${calling ? 'ring' : ''}">${esc(cur.code)}</div>
          <div class="pname">${esc(cur.patient_name)}</div>
          <div class="psub">${esc(cur.service.name)} · ${cur.age} anos · Doc. ${esc(cur.doc_number)}</div>
          <div class="tags">${cur.priority_class === 'PREFERENCIAL' ? cur.priority_reasons.map((r) => `<span class="badge nodot">${ic('star', 'sm')} ${esc(r)}</span>`).join('') : ''}${cur.priority_class === 'BAJA' ? '<span class="badge nodot">Reincorporado</span>' : ''}</div>
          <div class="actions">
            ${calling ? `
              <button class="btn big white" data-p="/doctor/turns/${cur.id}/start">${ic('play')} Iniciar atencion</button>
              <button class="btn big glass" data-p="/doctor/turns/${cur.id}/recall">${ic('bell')} Llamar de nuevo</button>
              <button class="btn big glass red" data-p="/doctor/turns/${cur.id}/no-show">${ic('x')} No se presento</button>` : `
              <button class="btn big white" data-p="/doctor/turns/${cur.id}/finish">${ic('check')} Finalizar atencion</button>`}
          </div></div>`;
      } else {
        stage = `<div class="hero ${d.point.active ? 'idle' : 'paused'}">
          <div class="eyebrow">${d.point.active ? 'LISTO PARA ATENDER' : 'PUNTO EN PAUSA'}</div>
          <div class="count" style="margin:16px 0 4px">${d.queue.length}</div>
          <div class="pname">${d.queue.length === 1 ? 'paciente en espera' : 'pacientes en espera'}</div>
          ${d.queue[0] ? `<div class="psub">Siguiente: <b>${esc(d.queue[0].code)}</b> · ${esc(d.queue[0].patient_name)} ${d.queue[0].priority_class === 'PREFERENCIAL' ? '★' : ''}</div>` : '<div class="psub">Nadie esperando por ahora</div>'}
          <div class="actions"><button class="btn big white" data-p="/doctor/call-next" ${d.queue.length ? '' : 'disabled'}>${ic('bell')} Llamar siguiente</button></div></div>`;
      }
      const maxEta = Math.max(1, ...d.queue.map((t) => t.eta_min || 0));
      $('#doc').innerHTML = `
        ${head(esc(d.point.name), `${esc(d.point.services.join(', '))}`, `<label class="switch"><input type="checkbox" id="act" ${d.point.active ? 'checked' : ''}><i></i><span>${d.point.active ? 'Disponible' : 'En pausa'}</span></label>`)}
        <div class="grid-2" style="grid-template-columns:1.25fr 1fr">
          <section>${stage}
            <div class="mini-stats"><div><b>${d.done_today}</b><span>Atendidos hoy</span></div><div><b>${d.queue.length}</b><span>En espera</span></div><div><b>${d.no_shows.length}</b><span>No presentados</span></div></div>
          </section>
          <section class="card">
            <div class="card-head"><h2><span class="ic">${ic('users')}</span>Proximos pacientes</h2></div>
            ${d.queue.length ? `<div class="tlist">${d.queue.slice(0, 8).map((t) => `
              <div class="titem ${t.priority_class === 'PREFERENCIAL' ? 'hot' : ''}" style="--sc:${t.service.color};grid-template-columns:auto 1fr auto">
                <div class="code">${esc(t.code)}</div><div class="who"><b>${esc(t.patient_name)}</b><span>${esc(t.service.name)}</span>${t.priority_class === 'PREFERENCIAL' ? `<div class="tags">${prioBadge(t)}</div>` : ''}</div><div class="pos"><b>#${t.position}</b><small>${t.eta_min < 1 ? 'siguiente' : '~' + mins(t.eta_min)}</small></div></div>`).join('')}</div>`
              : `<div class="empty"><div class="ico">${ic('coffee')}</div><b>Fila vacia</b><br>Buen momento para un cafe.</div>`}
            ${d.no_shows.length ? `<div class="notice info" style="margin:16px 0 0">No se presentaron: ${d.no_shows.map((t) => esc(t.code)).join(', ')}. Recepcion puede reincorporarlos.</div>` : ''}
          </section>
        </div>`;
      document.querySelectorAll('[data-p]').forEach((b) => { b.onclick = act(b.dataset.p); });
      $('#act').onchange = guard(async (e) => { await api('/doctor/active', { method: 'POST', body: { active: e.target.checked } }); toast(e.target.checked ? 'Estas disponible' : 'Punto en pausa: no recibira nuevos turnos'); load(); });
    }
    const load = guard(async () => { render(await api('/doctor/panel')); });
    poll(() => { if (!busy) load(); }, 4000);
  }

  // ------------------------------------------------------------ supervisor
  function viewSupervisor() {
    shell(`${head('Indicadores del dia', 'Panorama en tiempo real de la operacion.', `<button class="btn" id="sim">${ic('plus')} Simular llegadas</button>`)}<div id="sv"></div>`, '#/supervisor');
    $('#sim').onclick = guard(async () => {
      const r = await api('/demo/simulate', { method: 'POST', body: { count: 8 } });
      toast(`${r.created} pacientes simulados`, 'ok'); load();
    });
    const render = (s) => {
      const max = Math.max(1, ...s.hourly.map((h) => h.count));
      const by = s.by_status;
      const order = ['WAITING', 'CALLED', 'IN_SERVICE', 'DONE', 'NO_SHOW', 'CANCELLED'];
      let acc = 0;
      const stops = s.total ? order.map((k) => { const a = acc; acc += ((by[k] || 0) / s.total) * 100; return `${STATUS_COLOR[k]} ${a}% ${acc}%`; }).join(',') : '#e6eef5 0 100%';
      const pw = s.priority.avg_wait_min, nw = s.priority.avg_wait_normal_min;
      const wmax = Math.max(1, pw || 0, nw || 0);
      const kpi = (icon, color, label, val, unit, note) => `<div class="kpi" style="--kc:${color}"><div class="kic">${ic(icon)}</div><small>${label}</small><b>${val}${unit ? ` <em>${unit}</em>` : ''}</b><span>${note}</span></div>`;
      $('#sv').innerHTML = `
        <div class="kpis">
          ${kpi('ticket', '#0d9488', 'Turnos hoy', s.total, '', `${by.DONE || 0} atendidos`)}
          ${kpi('users', '#0ea5e9', 'En espera', by.WAITING || 0, '', `${(by.CALLED || 0) + (by.IN_SERVICE || 0)} en atencion`)}
          ${kpi('clock', '#f59e0b', 'Espera promedio', s.avg_wait_min ?? '-', 'min', 'hasta ser llamado')}
          ${kpi('activity', '#4f46e5', 'Atencion promedio', s.avg_service_min ?? '-', 'min', 'duracion real')}
          ${kpi('star', '#d97706', 'Preferenciales', s.priority.total, '', 'adulto mayor, gestante, disc.')}
          ${kpi('alert', '#8b5cf6', 'No se presentaron', s.no_shows_total, '', `${s.reassigned} reasignados`)}
        </div>
        <div class="grid-2 stretch" style="grid-template-columns:1.5fr 1fr;margin-bottom:24px">
          <section class="card"><div class="card-head"><h2><span class="ic">${ic('steth')}</span>Puntos de atencion</h2></div>
            <div class="pcards">${s.per_point.map((p) => {
              const tot = p.waiting + p.in_attention + p.done || 1; const pct = Math.min(100, (p.waiting / 6) * 100);
              const state = !p.active ? '<span class="badge b-low">En pausa</span>' : p.in_attention ? '<span class="badge b-IN_SERVICE">Atendiendo</span>' : '<span class="badge b-WAITING">Libre</span>';
              return `<div class="pcard"><div class="top"><b>${esc(p.name)}</b>${state}</div>
                <div class="num">${p.waiting}</div><small>en espera</small>
                <div class="load"><i style="width:${pct}%;background:${pct > 70 ? '#e11d48' : pct > 40 ? '#f59e0b' : '#14b8a6'}"></i></div>
                <small>${p.done} atendidos · prom. ${p.avg_service_min ?? '-'} min</small></div>`;
            }).join('')}</div></section>
          <section class="card"><div class="card-head"><h2><span class="ic">${ic('chart')}</span>Estado de turnos</h2></div>
            <div class="donut-wrap"><div class="donut" data-total="${s.total}" style="background:conic-gradient(${stops})"></div>
            <div class="legend">${order.map((k) => `<div><span class="dot" style="--c:${STATUS_COLOR[k]}"></span>${STATUS[k]}<b>${by[k] || 0}</b></div>`).join('')}</div></div>
          </section>
        </div>
        <div class="grid-2 stretch" style="grid-template-columns:1.5fr 1fr">
          <section class="card"><div class="card-head"><h2><span class="ic">${ic('clock')}</span>Llegadas por hora</h2></div>
            <div class="bars-wrap"><div class="bars">${s.hourly.map((h) => `<div class="bar ${h.count ? 'has' : ''}" style="height:${Math.max(3, (h.count / max) * 100)}%">${h.count ? `<em>${h.count}</em>` : ''}<span>${h.hour}h</span></div>`).join('')}</div></div>
          </section>
          <section class="card"><div class="card-head"><h2><span class="ic">${ic('star')}</span>Prioridad vs. espera</h2></div>
            <div class="vs">
              <div class="r"><span>Preferencial</span><div class="hbar"><i style="width:${((pw || 0) / wmax) * 100}%;background:#f59e0b"></i></div><b>${pw ?? '-'}m</b></div>
              <div class="r"><span>Normal</span><div class="hbar"><i style="width:${((nw || 0) / wmax) * 100}%;background:#0ea5e9"></i></div><b>${nw ?? '-'}m</b></div>
            </div>
            <div class="legend" style="margin-top:20px">${Object.entries(s.priority.reasons).map(([k, v]) => `<div>${ic('star', 'sm')}${esc(k)}<b>${v}</b></div>`).join('') || '<span class="muted">Sin casos prioritarios</span>'}</div>
          </section>
        </div>
        <section class="card" style="margin-top:24px"><div class="card-head"><h2><span class="ic">${ic('trend')}</span>Por servicio</h2></div>
          <div class="vs">${s.per_service.map((x) => `<div class="r" style="grid-template-columns:150px 1fr 70px"><span><span class="dot" style="--c:${x.color}"></span> ${esc(x.name)}</span><div class="hbar"><i style="width:${x.total ? (x.done / x.total) * 100 : 0}%;background:${x.color}"></i></div><b>${x.done}/${x.total}</b></div>`).join('')}</div>
        </section>`;
    };
    const load = guard(async () => render(await api('/stats')));
    poll(load, 5000);
  }

  // ------------------------------------------------------------ display (public)
  function viewDisplay() {
    clearTimers();
    $('#app').innerHTML = `<div class="tv">
      <div class="tv-head">${BRAND}<div class="tv-clock"><span id="clock"></span><small id="dt"></small></div></div>
      <div class="tv-grid"><section><h2>Llamando ahora</h2><div class="calls" id="calls"></div></section>
      <section class="tv-points"><h2>Puntos de atencion</h2><div id="pts"></div></section></div>
      <div class="tv-foot"><a href="#/login">Ingresar al sistema</a></div></div>`;
    const tick = () => { $('#clock').textContent = new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }); $('#dt').textContent = dateStr(); };
    tick(); timers.push(setInterval(tick, 10000));
    let seen = null;
    const load = async () => {
      let d; try { d = await api('/public/display'); } catch { return; }
      const first = seen === null;
      const newest = d.calls.length ? d.calls[0].code + d.calls[0].called_at : '';
      const fresh = !first && newest && !seen.has(newest);
      seen = seen || new Set(); seen.add(newest);
      $('#calls').innerHTML = d.calls.length ? d.calls.slice(0, 7).map((c, i) => `
        <div class="call ${i === 0 ? 'first' : ''} ${i === 0 && fresh ? 'fresh' : ''}" style="--c:${c.color}"><div class="c">${esc(c.code)}</div><div class="p">${esc(c.point)}</div>
        <div class="s"><i></i>${c.status === 'IN_SERVICE' ? 'En atencion' : 'Pase por favor'}${c.preferential ? ' · ★ Preferencial' : ''}</div></div>`).join('')
        : '<div class="tv-empty">Aun no hay turnos llamados</div>';
      const mx = Math.max(1, ...d.points.map((p) => p.waiting));
      $('#pts').innerHTML = d.points.map((p) => `<div class="pt ${p.active ? '' : 'off'}"><div class="t"><span>${esc(p.name)}</span><b>${p.active ? p.waiting : '—'}<small>${p.active ? 'en fila' : 'pausa'}</small></b></div><div class="bar2"><i style="width:${p.active ? (p.waiting / mx) * 100 : 0}%"></i></div></div>`).join('');
    };
    load(); timers.push(setInterval(load, 3000));
  }

  // ------------------------------------------------------------ patient lookup (public)
  function viewLookup() {
    clearTimers();
    $('#app').innerHTML = `<div class="lookup-bg"><div class="lookup">${BRAND}
      <div class="card"><h2 style="margin-bottom:6px">Consulta tu turno</h2>
        <p class="muted" style="margin-bottom:16px">Escribe el codigo de tu turno (ej. CG-004) o tu documento.</p>
        <form id="lf" style="display:flex;gap:10px"><input type="search" id="q" placeholder="Codigo o documento" required autofocus><button class="btn">${ic('search')}</button></form>
      </div><div id="res" style="margin-top:20px"></div>
      <p style="text-align:center;margin-top:24px"><a href="#/login" style="color:#fff;font-weight:600;opacity:.9">Ingreso del personal</a></p></div></div>`;
    let q = '';
    const steps = ['Espera', 'Llamado', 'Atencion', 'Finalizado'];
    const load = async () => {
      if (!q) return;
      try {
        const t = await api('/public/lookup?q=' + encodeURIComponent(q));
        const waiting = t.status === 'WAITING';
        const idx = { WAITING: 0, CALLED: 1, IN_SERVICE: 2, DONE: 3 }[t.status];
        const msg = { CALLED: `¡Es tu turno! Dirigete a ${t.point.name}`, IN_SERVICE: 'Estas siendo atendido', DONE: 'Tu atencion finalizo. ¡Gracias!', CANCELLED: 'Este turno fue cancelado', NO_SHOW: 'No te presentaste al llamado. Acude a recepcion para reincorporarte' }[t.status];
        $('#res').innerHTML = `<div class="card ticket">
          <div>${statusBadge(t.status)} ${prioBadge(t)}</div>
          <div class="big-code">${esc(t.code)}</div>
          <div style="font-weight:800;font-size:19px">${esc(t.patient_name)}</div><div class="muted">${esc(t.service.name)}</div>
          ${idx !== undefined ? `<div class="track">${steps.map((s, i) => `<div class="${i < idx ? 'done' : i === idx ? 'now' : ''}"><i></i>${s}</div>`).join('')}</div>` : ''}
          ${waiting ? `<div class="line"><div><b>#${t.position}</b><small>Tu posicion</small></div><div><b>${mins(t.eta_min)}</b><small>Espera aprox.</small></div><div><b>${esc(t.point.name)}</b><small>Punto</small></div></div>` : `<div class="notice" style="margin:22px 0 0;justify-content:center">${msg}</div>`}
        </div>`;
      } catch (e) { $('#res').innerHTML = `<div class="card empty"><div class="ico">${ic('search')}</div>${esc(e.message)}</div>`; }
    };
    $('#lf').onsubmit = (e) => { e.preventDefault(); q = $('#q').value.trim(); load(); };
    timers.push(setInterval(load, 5000));
  }

  // ------------------------------------------------------------ router
  const PUBLIC = { '#/login': viewLogin, '#/pantalla': viewDisplay, '#/consulta': viewLookup };
  const PRIVATE = {
    '#/recepcion': [['RECEPCION', 'SUPERVISOR'], viewReception],
    '#/medico': [['MEDICO'], viewDoctor],
    '#/supervisor': [['SUPERVISOR'], viewSupervisor],
  };

  async function route() {
    clearTimers();
    $('#modal-root').innerHTML = '';
    const h = location.hash || '#/';
    if (store.token && !user) {
      try { user = await api('/auth/me'); } catch { store.token = null; }
    }
    if (PUBLIC[h]) {
      if (h === '#/login' && user) { location.hash = HOME[user.role]; return; }
      return PUBLIC[h]();
    }
    if (!user) { location.hash = '#/login'; return; }
    const r = PRIVATE[h];
    if (!r || !r[0].includes(user.role)) { location.hash = HOME[user.role]; return; }
    r[1]();
  }

  window.addEventListener('hashchange', route);
  route();
})();
