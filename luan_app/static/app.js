'use strict';
/* Luan App front end — vanilla JS, talks only to /api. */
const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const icon = (n) => `<svg class="i"><use href="#i-${n}"/></svg>`;
const STATUS = {
  DONE: ['Xong', 'b-ok', '--ok'], REVIEW: ['Cần xem', 'b-warn', '--warn'], ERROR: ['Lỗi', 'b-err', '--err'],
  CANCELLED: ['Đã hủy', 'b-idle', '--tx-3'], QUEUED: ['Đang chờ', 'b-idle', '--tx-3'], PREPARING: ['Chuẩn bị', 'b-run', '--run'],
  RUNNING: ['Đang chạy', 'b-run', '--run'], FINISHING: ['Đóng gói', 'b-run', '--run'],
};
const STAGES = ['L0', 'L1', 'L2', 'L3'];
const state = {me: null, board: null, etag: null, view: 'board', inspect: null, inspectSeq: 0, notifId: null, history: []};

/* ---------- helpers ---------- */
function cookie(name) {
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return m ? decodeURIComponent(m[1]) : '';
}
async function api(path, opts = {}) {
  const o = {method: 'GET', headers: {}, ...opts};
  if (o.json !== undefined) { o.body = JSON.stringify(o.json); o.headers['Content-Type'] = 'application/json'; delete o.json; }
  if (o.method !== 'GET') o.headers['X-Luan-CSRF'] = cookie('luan_csrf');
  const r = await fetch(path, o);
  if (r.status === 304) return {status: 304};
  const ct = r.headers.get('content-type') || '';
  const data = ct.includes('json') ? await r.json() : await r.text();
  if (!r.ok) throw {status: r.status, data};
  return {status: r.status, data, etag: r.headers.get('etag')};
}
const errText = (e) => (e && e.data && e.data.error) || 'Không kết nối được máy chủ.';
function badge(status) { const s = STATUS[status] || [status, 'b-idle']; return `<span class="badge ${s[1]}">${esc(s[0])}</span>`; }
const kindTag = (k) => `<span class="tag ${k === 'QA' ? 't-qa' : 't-run'}">${esc(k)}</span>`;
const hhmm = (iso) => (iso ? iso.slice(11, 16) : '');
const dmy = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)} ${iso.slice(11, 16)}` : '');
function ago(iso) {
  if (!iso) return '';
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 10) return 'vài giây trước';
  if (s < 60) return `${Math.round(s)} giây trước`;
  if (s < 3600) return `${Math.floor(s / 60)} phút trước`;
  return `${Math.floor(s / 3600)} giờ trước`;
}
function dur(from, to) {
  if (!from) return '';
  const s = Math.max(0, ((to ? new Date(to) : new Date()) - new Date(from)) / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = Math.floor(s % 60);
  return h ? `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}` : `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}
async function copyText(text) {
  try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); return true; } } catch (e) { /* fall back */ }
  const ta = document.createElement('textarea');
  ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
  document.body.appendChild(ta); ta.select();
  let ok = false; try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
  ta.remove(); return ok;
}
function toast(text, kind = 'run', onClick) {
  const el = document.createElement('div');
  el.className = 'toast';
  const color = {DONE: '--ok', REVIEW: '--warn', ERROR: '--err', CANCELLED: '--tx-3', ok: '--ok', err: '--err', run: '--run'}[kind] || '--run';
  el.innerHTML = `<i class="dot" style="background:var(${color})"></i><span>${esc(text)}</span>`;
  el.onclick = () => { el.remove(); if (onClick) onClick(); };
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), 6000);
}

/* ---------- modal ---------- */
function modal({title, text = '', input = null, okLabel = 'OK', cancelLabel = 'Không', danger = false, password = false, noCancel = false}) {
  return new Promise((resolve) => {
    const root = $('#modal-root');
    root.innerHTML = `<div class="scrim"></div><div class="modal-wrap"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="m-title">
      <h3 id="m-title">${esc(title)}</h3>${text ? `<p>${esc(text)}</p>` : ''}
      ${input !== null ? `<input class="inp" id="m-input" ${password ? 'type="password"' : ''} value="${esc(input)}" autocomplete="off">` : ''}
      <div class="err" id="m-err"></div>
      <div class="btns">${noCancel ? '' : `<button class="btn btn-sec" id="m-no">${esc(cancelLabel)}</button>`}
      <button class="btn ${danger ? 'btn-danger' : 'btn-pri'}" id="m-ok">${esc(okLabel)}</button></div></div></div>`;
    const inp = root.querySelector('#m-input');
    const done = (v) => { root.innerHTML = ''; resolve(v); };
    const ok = () => done(inp ? inp.value : true);
    root.querySelector('#m-ok').onclick = ok;
    const no = root.querySelector('#m-no');
    if (no) no.onclick = () => done(null);
    root.querySelector('.modal').onkeydown = (e) => { if (e.key === 'Enter') ok(); if (e.key === 'Escape' && !noCancel) done(null); };
    (inp || root.querySelector('#m-ok')).focus();
    root.setError = (m) => { root.querySelector('#m-err').textContent = m; };
  });
}
async function askName(required) {
  let msg = '';
  for (;;) {
    const p = modal({title: 'Bạn là ai?', text: 'Nhập tên để mọi người biết ai đang chạy job. Trình duyệt sẽ nhớ tên này.',
                     input: state.me && state.me.user ? state.me.user.name : '', okLabel: 'Lưu tên', noCancel: required});
    if (msg) setTimeout(() => $('#modal-root').setError && $('#modal-root').setError(msg), 0);
    const name = await p;
    if (name === null) return false;
    try { await api('/api/me', {method: 'POST', json: {name}}); await loadMe(); return true; } catch (e) { msg = errText(e); }
  }
}
async function adminLogin() {
  if (!state.me.has_admin_password) {
    if (!state.me.is_local) { await modal({title: 'Chưa có mật khẩu Admin', text: 'Mật khẩu Admin chỉ đặt được lần đầu trên máy chạy app.', okLabel: 'Đã hiểu', noCancel: true}); return; }
    const pw = await modal({title: 'Đặt mật khẩu Admin', text: 'Tối thiểu 6 ký tự. Chỉ người giữ mật khẩu này được QA, duyệt và cài đặt.', input: '', password: true, okLabel: 'Đặt mật khẩu'});
    if (pw === null) return;
    try { await api('/api/admin/setup', {method: 'POST', json: {password: pw}}); } catch (e) { toast(errText(e), 'err'); return; }
  } else {
    const pw = await modal({title: 'Đăng nhập Admin', input: '', password: true, okLabel: 'Đăng nhập', cancelLabel: 'Hủy'});
    if (pw === null) return;
    try { await api('/api/admin/login', {method: 'POST', json: {password: pw}}); } catch (e) { toast(errText(e), 'err'); return; }
  }
  await loadMe(); state.etag = null; poll(true); render();
}

/* ---------- me + theme ---------- */
async function loadMe() {
  state.me = (await api('/api/me')).data;
  const u = state.me.user, admin = state.me.is_admin;
  const name = u ? u.name : (admin ? 'Admin' : 'Khách');
  $('#me-name').textContent = name;
  $('#me-av').textContent = name.split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase();
  $('#me-role').hidden = !admin;
  $('#nav-review').hidden = !admin;
  $('#nav-settings').hidden = !admin;
  $('#btn-qa').hidden = !admin;
  $('#h-user').hidden = !admin;
  $('#h-csv').hidden = !admin;
  $('#history-sub').textContent = admin ? 'Tất cả job của mọi người.' : 'Các job bạn đã chạy.';
}
function setTheme(t) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem('luan-theme', t); } catch (e) { /* private mode */ }
  document.querySelectorAll('#theme button').forEach((b) => b.classList.toggle('on', b.dataset.t === t));
}

/* ---------- router ---------- */
function route() {
  let v = (location.hash.replace(/^#\//, '') || 'board').split('?')[0];
  if (!['board', 'history', 'review', 'settings', 'me'].includes(v)) v = 'board';
  if ((v === 'review' || v === 'settings') && !(state.me && state.me.is_admin)) v = 'board';
  state.view = v;
  closeDrawer();
  document.querySelectorAll('main > section').forEach((s) => { s.hidden = s.dataset.view !== v; });
  document.querySelectorAll('#nav a').forEach((a) => a.classList.toggle('on', a.dataset.view === v));
  render();
}
function render() {
  if (state.view === 'board') renderBoard();
  else if (state.view === 'history') loadHistory();
  else if (state.view === 'review') loadReview();
  else if (state.view === 'settings') loadSettings();
  else if (state.view === 'me') renderMe();
}

/* ---------- board ---------- */
let pollTimer = null;
async function poll(force) {
  clearTimeout(pollTimer);
  try {
    const headers = !force && state.etag ? {'If-None-Match': state.etag} : {};
    const r = await api('/api/board', {headers});
    if (r.status !== 304) {
      state.board = r.data; state.etag = r.etag; renderChrome();
      if (state.view === 'board') renderBoard();
      else if (state.view === 'history' && !document.activeElement.closest('.filters')) loadHistory();
    }
  } catch (e) {
    if (e.status === 401 && (await askName(true))) { state.etag = null; return poll(true); }
  }
  pollTimer = setTimeout(poll, document.hidden ? 10000 : 2000);
}
function renderChrome() {
  const b = state.board; if (!b) return;
  const s = b.slots;
  $('#slots').innerHTML = Array.from({length: s.total}, (_, i) => `<i class="${i < s.used ? 'b' : ''}"></i>`).join('') + `<span>${s.used}/${s.total} suất</span>`;
  const rc = $('#review-count');
  rc.hidden = !b.review_pending; rc.textContent = b.review_pending;
}
function stepsHtml(row, runStatus) {
  const idx = row.status === 'PASS' && row.stage === 'L3' ? 4 : Math.max(0, STAGES.indexOf(row.stage));
  const live = ['RUNNING', 'PREPARING'].includes(runStatus);
  return '<div class="steps">' + STAGES.map((_, i) => {
    if (i < idx) return '<span class="d"></span>';
    if (i === idx) return `<span class="${row.flags ? 'w' : (live ? 'a' : '')}"></span>`;
    return '<span></span>';
  }).join('') + '</div>';
}
function codeBadge(row, runStatus) {
  if (row.status === 'PASS') return '<span class="badge b-ok"><i class="dot" style="background:var(--ok)"></i>PASS</span>';
  if (row.status === 'PREVIEW') return `<span class="badge b-warn"><i class="dot" style="background:var(--warn)"></i>PREVIEW${row.flags ? ` · ${row.flags} FLAG` : ''}</span>`;
  if (row.status === 'FAIL') return '<span class="badge b-err"><i class="dot" style="background:var(--err)"></i>FAIL</span>';
  if (row.flags) return `<span class="badge b-warn"><i class="dot" style="background:var(--warn)"></i>${row.flags} FLAG</span>`;
  const label = ['RUNNING', 'PREPARING'].includes(runStatus) ? `${esc(row.stage || 'L0')} · đang làm` : esc(row.stage || '');
  return `<span class="badge b-run"><i class="dot" style="background:var(--run)"></i>${label}</span>`;
}
function runCard(r) {
  const rows = r.codes_status || [];
  const table = rows.length ? `<table><thead><tr><th style="width:130px">Mã</th><th>Tiến độ</th><th style="width:150px">Trạng thái</th></tr></thead><tbody>
      ${rows.map((c) => `<tr><td class="code">${esc(c.code)}</td><td>${stepsHtml(c, r.status)}</td><td>${codeBadge(c, r.status)}</td></tr>`).join('')}</tbody></table>`
    : `<div class="empty">${r.status === 'PREPARING' ? 'Đang chuẩn bị suất chạy…' : 'Đang đọc nguồn, chưa có danh sách mã…'}</div>`;
  const nCodes = r.codes ? `${r.codes.length} mã` : 'tất cả mã';
  return `<article class="job" data-id="${r.id}">
    <div class="job-h"><span class="jid">${esc(r.job)}</span>${kindTag(r.kind)}
      <span class="meta">${esc(r.user || 'Admin')}<span class="sep">·</span><span class="mono" data-since="${esc(r.started_at || '')}">${dur(r.started_at)}</span><span class="sep dur">·</span><span class="dur">${nCodes}</span><span class="sep">·</span>suất ${esc(r.slot || '')}</span>
      <div class="act"><button class="ib" data-act="open" aria-label="Mở chi tiết" title="Chi tiết">${icon('ext')}</button>
      ${r.can_cancel ? `<button class="ib" data-act="cancel" aria-label="Hủy job" title="Hủy job">${icon('x')}</button>` : ''}</div></div>
    <div class="path" title="${esc(r.path)}">${esc(r.path)}</div>${table}
    <div class="live"><i class="pulse"></i><span class="txt">${esc(r.activity || STATUS[r.status][0] + '…')}</span><span class="tm" data-ago="${esc(r.activity_at || '')}">${ago(r.activity_at)}</span></div>
  </article>`;
}
const keyed = {};
function patchList(container, items, html, emptyHtml) {
  const el = $(container);
  if (!items.length) { el.innerHTML = emptyHtml; keyed[container] = {}; return; }
  const prev = keyed[container] || {};
  const next = {};
  const frag = document.createDocumentFragment();
  for (const it of items) {
    const sig = JSON.stringify(it);
    let node = prev[it.id] && prev[it.id].sig === sig ? prev[it.id].node : null;
    if (!node) { const t = document.createElement('template'); t.innerHTML = html(it).trim(); node = t.content.firstChild; }
    next[it.id] = {sig, node};
    frag.appendChild(node);
  }
  el.replaceChildren(frag);
  keyed[container] = next;
}
function renderBoard() {
  const b = state.board; if (!b) return;
  const banners = [];
  if (b.paused_until) banners.push(`<div class="banner warn">${icon('pause')}<span class="sp">Hết hạn mức Claude — hàng đợi tạm dừng tới <b>${hhmm(b.paused_until)}</b>.</span>${b.me.is_admin ? '<button class="btn btn-sec" data-act="resume">Chạy tiếp ngay</button>' : ''}</div>`);
  if (b.me.is_admin && b.claude && !b.claude.ok) banners.push(`<div class="banner err">${icon('alert')}<span class="sp">Không gọi được Claude CLI trên máy này. Kiểm tra <span class="mono">claude auth login</span>.</span></div>`);
  if (b.me.is_admin && b.utilization != null) banners.push(`<div class="banner">${icon('clock')}<span class="sp">Hạn mức Claude 5 giờ đã dùng <b>${Math.round(b.utilization * 100)}%</b>.</span></div>`);
  $('#board-banners').innerHTML = banners.join('');
  const st = b.stats;
  $('#stats').innerHTML = [[st.running, 'Đang chạy', '--run'], [st.queued, 'Đang chờ', '--tx-3'], [st.done_today, 'Xong hôm nay', '--ok'], [st.review_today + st.error_today, 'Cần xem / lỗi', '--warn']]
    .map(([n, l, c]) => `<div class="stat"><b>${n}</b><span><i class="dot" style="background:var(${c})"></i>${l}</span></div>`).join('');
  $('#running-n').textContent = b.running.length;
  $('#queue-n').textContent = b.queue.length;
  $('#today-n').textContent = b.today.length;
  patchList('#running', b.running, runCard, '<div class="list"><div class="empty">Không có job nào đang chạy.</div></div>');
  patchList('#queue', b.queue.map((r, i) => ({...r, pos: i + 1})), (r) => `<div class="li" data-id="${r.id}"><span class="pos">#${r.pos}</span><div class="main"><div class="t1">${esc(r.job)}</div><div class="t2">${esc(r.user || 'Admin')} · ${esc(r.kind)} · chờ từ ${hhmm(r.queued_at)}</div></div>${r.can_cancel ? `<button class="ib" data-act="cancel" aria-label="Bỏ khỏi hàng đợi">${icon('x')}</button>` : ''}</div>`, '<div class="empty">Hàng đợi trống.</div>');
  patchList('#today', b.today, (r) => `<div class="li" data-id="${r.id}"><div class="main"><div class="t1">${esc(r.job)} ${r.kind === 'QA' ? '<span class="tag t-qa">QA</span>' : ''}</div><div class="t2">${esc(r.summary || '')}</div></div>${badge(r.status)}</div>`, '<div class="empty">Chưa có job nào xong hôm nay.</div>');
}
function tickClocks() {
  document.querySelectorAll('[data-since]').forEach((el) => { if (el.dataset.since) el.textContent = dur(el.dataset.since); });
  document.querySelectorAll('[data-ago]').forEach((el) => { el.textContent = ago(el.dataset.ago); });
}

/* ---------- submit ---------- */
let inspectTimer = null;
function onPathInput() {
  clearTimeout(inspectTimer);
  state.inspect = null; renderPicker();
  setHint();
  if ($('#path').value.trim()) inspectTimer = setTimeout(doInspect, 450);
}
function setHint(text, cls) {
  const h = $('#path-hint');
  h.className = 'hint' + (cls ? ' ' + cls : '');
  h.innerHTML = text || 'Dán đường dẫn thư mục job có PDF, DXF DATA và phiếu 依頼. DXF giao vào <span class="mono">AI_L\\</span> trong thư mục đó.';
}
async function doInspect() {
  const path = $('#path').value.trim();
  const seq = ++state.inspectSeq;
  try {
    const r = await api('/api/sources/inspect', {method: 'POST', json: {path, kind: 'RUN'}});
    if (seq !== state.inspectSeq) return;
    state.inspect = r.data;
    renderPicker();
    const w = r.data.warnings.length ? r.data.warnings.join(' ') : '';
    const last = r.data.last_run ? ` Đã chạy lần trước lúc ${dmy(r.data.last_run.ended_at)} (${(STATUS[r.data.last_run.status] || [''])[0]}).` : '';
    setHint(esc(`Job ${r.data.job}${r.data.urgent ? ' · GẤP: giao từng mã' : ''}. ${w}${last}`), w ? 'warn' : '');
  } catch (e) {
    if (seq !== state.inspectSeq) return;
    if (e.status === 400 && $('#path').value.trim()) {
      const isDxf = /\.dxf$/i.test(path);
      setHint(esc(isDxf && state.me.is_admin ? 'File .dxf: bấm QA để kiểm tra.' : errText(e)), isDxf && state.me.is_admin ? '' : 'err');
    }
  }
}
function renderPicker() {
  const p = $('#picker'), info = state.inspect;
  if (!info || !info.codes.length) { p.hidden = true; p.innerHTML = ''; updateRunLabel(); return; }
  p.hidden = false;
  p.innerHTML = `<div class="picker-h"><b>${esc(info.job)}</b><span>${info.codes.length} mã trong phiếu</span><span class="sp"></span>
    <button class="btn btn-ghost" data-pick="all">Chọn tất cả</button><button class="btn btn-ghost" data-pick="none">Bỏ chọn</button></div>
    <div class="picker-l">${info.codes.map((c) => `<label class="pick"><input type="checkbox" value="${esc(c.code)}" checked><span class="c">${esc(c.code)}</span><span class="m">${esc(c.material)}${c.t ? ' · t' + esc(c.t) : ''}</span><span class="s">${esc(c.size)}</span></label>`).join('')}</div>`;
  updateRunLabel();
}
function selectedCodes() {
  const boxes = [...document.querySelectorAll('#picker input[type=checkbox]')];
  if (!boxes.length) return null;
  const on = boxes.filter((b) => b.checked).map((b) => b.value);
  return on.length === boxes.length ? null : on;
}
function updateRunLabel() {
  const boxes = [...document.querySelectorAll('#picker input[type=checkbox]')];
  const n = boxes.filter((b) => b.checked).length;
  $('#btn-run-label').textContent = boxes.length ? (n === boxes.length ? `Chạy ${n} mã` : `Chạy ${n}/${boxes.length} mã`) : 'Chạy job';
}
async function submit(kind, confirm = false) {
  const path = $('#path').value.trim();
  if (!path) { setHint('Dán đường dẫn thư mục job trước.', 'err'); $('#path').focus(); return; }
  const codes = kind === 'RUN' || state.inspect ? selectedCodes() : null;
  if (codes && !codes.length) { setHint('Chọn ít nhất một mã.', 'err'); return; }
  try {
    await api('/api/runs', {method: 'POST', json: {path, kind, codes, confirm_rerun: confirm}});
    toast(`Đã đưa ${state.inspect ? state.inspect.job : 'job'} vào hàng đợi.`, 'ok');
    $('#path').value = ''; state.inspect = null; renderPicker(); setHint();
    state.etag = null; poll(true);
  } catch (e) {
    if (e.status === 409 && e.data.error === 'need_confirm') {
      const lr = e.data.last_run;
      if (await modal({title: 'Chạy lại job này?', text: `Job này đã chạy lúc ${dmy(lr.ended_at)} (${(STATUS[lr.status] || [''])[0]}). Bản giao mới sẽ thành _v2, _v3, không ghi đè.`, okLabel: 'Chạy lại'})) submit(kind, true);
    } else setHint(esc(errText(e)), 'err');
  }
}
async function cancelRun(r) {
  const who = r.user || 'Admin';
  if (!(await modal({title: 'Hủy job?', text: `Hủy job ${r.job} của ${who}? Phần đã làm vẫn được lưu.`, okLabel: 'Hủy job', cancelLabel: 'Không', danger: true}))) return;
  try { await api(`/api/runs/${r.id}/cancel`, {method: 'POST'}); toast(`Đang hủy ${r.job}…`); state.etag = null; poll(true); } catch (e) { toast(errText(e), 'err'); }
}
async function rerunRun(r) {
  try { await api(`/api/runs/${r.id}/rerun`, {method: 'POST'}); toast(`Đã đưa ${r.job} vào hàng đợi.`, 'ok'); closeDrawer(); state.etag = null; poll(true); } catch (e) { toast(errText(e), 'err'); }
}
function findRun(id) {
  const b = state.board || {running: [], queue: [], today: []};
  return [...b.running, ...b.queue, ...b.today, ...state.history].find((r) => r.id === id);
}

/* ---------- drawer ---------- */
function closeDrawer() { $('#drawer-root').innerHTML = ''; }
async function openRun(id) {
  let r;
  try { r = (await api(`/api/runs/${id}`)).data; } catch (e) { toast(errText(e), 'err'); return; }
  const admin = state.me.is_admin;
  const local = state.me.is_local;
  const rows = r.codes_status || [];
  const flags = rows.flatMap((c) => c.flag_texts.map((f) => [c.code, f]));
  const delivered = r.delivered || [];
  $('#drawer-root').innerHTML = `<div class="scrim" data-act="close"></div><aside class="drawer" role="dialog" aria-modal="true" aria-label="Chi tiết job">
    <div class="drawer-h"><span class="jid">${esc(r.job)}</span>${kindTag(r.kind)}${badge(r.status)}<div class="act"><button class="ib" data-act="close" aria-label="Đóng">${icon('x')}</button></div></div>
    <div class="drawer-b">
      ${r.summary ? `<section><p>${esc(r.summary)}</p></section>` : ''}
      ${r.error ? `<section><h2>Lỗi</h2><div class="errbox">${esc(r.error)}</div></section>` : ''}
      ${r.warnings && r.warnings.length ? `<section><div class="warnbox">${r.warnings.map(esc).join('<br>')}</div></section>` : ''}
      <section><dl class="kv">
        <dt>Thư mục</dt><dd class="mono">${esc(r.path)} <button class="ib" data-copy="${esc(r.path)}" aria-label="Copy đường dẫn" style="display:inline-grid;vertical-align:middle">${icon('copy')}</button></dd>
        <dt>Người chạy</dt><dd>${esc(r.user || 'Admin')}</dd>
        <dt>Mã</dt><dd>${r.codes ? esc(r.codes.join(', ')) : 'tất cả mã trong phiếu'}</dd>
        <dt>Thời gian</dt><dd>${dmy(r.queued_at)} → ${r.ended_at ? dmy(r.ended_at) : '…'}${r.started_at ? ` (${dur(r.started_at, r.ended_at)})` : ''}</dd>
        ${r.commit ? `<dt>Bản repo</dt><dd class="mono">${esc(r.commit.slice(0, 8))}</dd>` : ''}
        ${r.cancelled_by ? `<dt>Hủy bởi</dt><dd>${esc(r.cancelled_by)}</dd>` : ''}
        ${r.rerun_of ? `<dt>Chạy lại của</dt><dd>#${esc(r.rerun_of)}</dd>` : ''}
      </dl></section>
      ${rows.length ? `<section><h2>Mã</h2><div class="inline-tbl"><table><thead><tr><th>Mã</th><th>Bước</th><th>Trạng thái</th></tr></thead><tbody>${rows.map((c) => `<tr><td class="code">${esc(c.code)}</td><td class="mono">${esc(c.stage || '')}</td><td>${codeBadge(c, r.status)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${flags.length ? `<section><h2>FLAG <span class="n">${flags.length}</span></h2><div class="inline-tbl"><table><tbody>${flags.map(([c, f]) => `<tr><td class="code" style="width:120px">${esc(c)}</td><td>${esc(f)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${delivered.length ? `<section><h2>DXF đã giao</h2><div class="inline-tbl"><table><tbody>${delivered.map((f) => `<tr><td class="mono" style="word-break:break-all">${esc(f)}</td><td style="width:40px"><button class="ib" data-copy="${esc(f)}" aria-label="Copy đường dẫn DXF">${icon('copy')}</button></td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${r.report_md ? `<section><h2>Báo cáo</h2><div class="report">${esc(r.report_md)}</div></section>` : ''}
      <section style="display:flex;gap:8px;flex-wrap:wrap">
        ${r.can_cancel ? '<button class="btn btn-danger" data-act="cancel">Hủy job</button>' : ''}
        ${r.can_rerun ? `<button class="btn btn-sec" data-act="rerun">${icon('redo')}Chạy lại</button>` : ''}
        ${admin && local ? `<button class="btn btn-sec" data-act="folder">${icon('folder')}Mở thư mục AI_L</button>` : ''}
        ${admin ? `<a class="btn btn-sec" href="/api/runs/${r.id}/transcript" target="_blank" rel="noopener">${icon('file')}Transcript</a>
          <a class="btn btn-sec" href="/api/runs/${r.id}/bundle.zip">${icon('download')}Xuất gói lỗi</a>` : ''}
      </section>
    </div></aside>`;
  const root = $('#drawer-root');
  root.onclick = async (e) => {
    const t = e.target.closest('[data-act],[data-copy]'); if (!t) return;
    if (t.dataset.copy) { toast((await copyText(t.dataset.copy)) ? 'Đã copy.' : 'Không copy được.', 'ok'); return; }
    const a = t.dataset.act;
    if (a === 'close') closeDrawer();
    else if (a === 'cancel') { await cancelRun(r); closeDrawer(); }
    else if (a === 'rerun') rerunRun(r);
    else if (a === 'folder') { try { await api('/api/open-folder', {method: 'POST', json: {run_id: r.id}}); } catch (err) { toast(errText(err), 'err'); } }
  };
  root.querySelector('.drawer').focus();
}

/* ---------- history ---------- */
let historyTimer = null;
async function loadHistory() {
  const q = new URLSearchParams();
  const v = (id) => $(id).value.trim();
  if (v('#h-q')) q.set('q', v('#h-q'));
  if (v('#h-status')) q.set('status', v('#h-status'));
  if (v('#h-kind')) q.set('kind', v('#h-kind'));
  if (v('#h-user')) q.set('user', v('#h-user'));
  if (v('#h-from')) q.set('from', v('#h-from') + 'T00:00:00');
  if (v('#h-to')) q.set('to', v('#h-to') + 'T23:59:59');
  try { state.history = (await api('/api/runs?' + q)).data.runs; } catch (e) { $('#history').innerHTML = `<div class="empty">${esc(errText(e))}</div>`; return; }
  const rows = state.history;
  $('#history').innerHTML = rows.length ? `<table><thead><tr><th>Job</th><th>Loại</th><th>Người chạy</th><th>Bắt đầu</th><th>Thời gian</th><th>Trạng thái</th><th>Tóm tắt</th><th></th></tr></thead><tbody>
    ${rows.map((r) => `<tr data-id="${r.id}"><td class="code">${esc(r.job)}</td><td>${kindTag(r.kind)}</td><td>${esc(r.user || 'Admin')}</td><td class="mono">${dmy(r.started_at || r.queued_at)}</td><td class="mono">${r.started_at ? dur(r.started_at, r.ended_at) : ''}</td><td>${badge(r.status)}${r.repo_touched ? ' <span class="badge b-err" title="Job đã sửa file repo">repo</span>' : ''}</td><td class="sum">${esc(r.summary || '')}</td>
    <td>${r.can_rerun ? `<button class="ib" data-act="rerun" aria-label="Chạy lại" title="Chạy lại">${icon('redo')}</button>` : ''}</td></tr>`).join('')}</tbody></table>`
    : '<div class="empty">Không có job nào khớp bộ lọc.</div>';
}
function historyQuery() { clearTimeout(historyTimer); historyTimer = setTimeout(loadHistory, 300); }

/* ---------- review ---------- */
let rvFilter = 'open', rvAttachId = null;
async function loadReview() {
  let items;
  try { items = (await api('/api/review-items')).data.items; } catch (e) { $('#review').innerHTML = `<div class="empty">${esc(errText(e))}</div>`; return; }
  const shown = items.filter((it) => (rvFilter === 'open' ? ['PENDING', 'COPIED'].includes(it.status) : !rvFilter || it.status === rvFilter));
  const typeTag = (t) => (t === 'NEED_SAMPLE_DXF' ? '<span class="badge b-qa">Cần mẫu DXF</span>' : '<span class="badge b-run">Bài học mới</span>');
  const stTag = {PENDING: '', COPIED: '<span class="badge b-idle">Đã chép</span>', DONE: '<span class="badge b-ok">Đã xử lý</span>', DISMISSED: '<span class="badge b-idle">Bỏ qua</span>'};
  $('#review').innerHTML = shown.length ? shown.map((it) => `<article class="rv" data-id="${it.id}">
    <div class="rv-h">${typeTag(it.type)}<span class="t">${esc(it.title)}</span>${stTag[it.status] || ''}</div>
    <div class="f">${esc(it.job || '')} · ${esc(it.code || '?')} · ${esc(it.card || '')} · ${dmy(it.created_at)}</div>
    ${it.detail ? `<div class="d" data-act="expand">${esc(it.detail)}</div>` : ''}
    ${it.evidence ? `<div class="f">Bằng chứng: ${esc(it.evidence)}</div>` : ''}
    <div class="f" title="${esc(it.path || '')}">${esc(it.path || '')}</div>
    ${it.attachment ? `<div class="f">${icon('paperclip')} ${esc(it.attachment)}</div>` : ''}
    <div class="btns"><button class="btn btn-pri" data-act="copy">${icon('copy')}Chép để duyệt</button>
      <button class="btn btn-sec" data-act="attach">${icon('paperclip')}Đính kèm mẫu DXF</button>
      ${it.status !== 'DONE' ? '<button class="btn btn-sec" data-act="done">Đã xử lý</button>' : ''}
      ${it.status !== 'DISMISSED' ? '<button class="btn btn-ghost" data-act="dismiss">Bỏ qua</button>' : ''}</div>
  </article>`).join('') : '<div class="list"><div class="empty">Không có mục nào.</div></div>';
  $('#review').onclick = async (e) => {
    const t = e.target.closest('[data-act]'); if (!t) return;
    const card = t.closest('.rv'); const it = items.find((x) => x.id === Number(card.dataset.id));
    const a = t.dataset.act;
    if (a === 'expand') { t.classList.toggle('open'); return; }
    if (a === 'copy') {
      const ok = await copyText(it.copy_text);
      toast(ok ? 'Đã chép. Dán vào Claude Code để duyệt.' : 'Không copy được.', ok ? 'ok' : 'err');
      if (ok && it.status === 'PENDING') await setReview(it.id, 'COPIED');
    } else if (a === 'attach') { rvAttachId = it.id; $('#rv-file').click(); }
    else if (a === 'done') await setReview(it.id, 'DONE');
    else if (a === 'dismiss') await setReview(it.id, 'DISMISSED');
  };
}
async function setReview(id, status) {
  try { await api(`/api/review-items/${id}`, {method: 'PATCH', json: {status}}); state.etag = null; poll(true); loadReview(); } catch (e) { toast(errText(e), 'err'); }
}
async function uploadAttachment() {
  const f = $('#rv-file').files[0]; if (!f || !rvAttachId) return;
  const fd = new FormData(); fd.append('file', f);
  try { await api(`/api/review-items/${rvAttachId}/attachment`, {method: 'POST', body: fd}); toast('Đã đính kèm mẫu DXF.', 'ok'); loadReview(); } catch (e) { toast(errText(e), 'err'); }
  $('#rv-file').value = '';
}

/* ---------- settings ---------- */
async function loadSettings() {
  let s;
  try { s = (await api('/api/settings')).data; } catch (e) { $('#settings').innerHTML = `<div class="empty">${esc(errText(e))}</div>`; return; }
  const b = state.board || {};
  $('#settings').innerHTML = `<form class="form" id="set-form"><h3>Chạy job</h3>
    <div class="row"><label for="s-slots">Số job chạy cùng lúc<small>1–6. Nhiều hơn thì tốn hạn mức và RAM nhanh hơn.</small></label><input class="inp" id="s-slots" type="number" min="1" max="6" value="${esc(s.slots)}" style="width:100px"></div>
    <div class="row"><label for="s-timeout">Thời gian tối đa mỗi job<small>Phút. Quá thì tự hủy, báo lỗi.</small></label><input class="inp" id="s-timeout" type="number" min="5" max="1440" value="${esc(s.timeout_min)}" style="width:100px"></div>
    <div class="row"><label for="s-roots">Thư mục gốc được phép<small>Mỗi dòng một đường dẫn. Job phải nằm trong một thư mục này.</small></label><textarea class="inp" id="s-roots" rows="4">${esc((s.allowed_roots || []).join('\n'))}</textarea></div>
    <div class="row"><label for="s-model">Model Claude<small>Để trống = model mặc định của tài khoản.</small></label><input class="inp" id="s-model" value="${esc(s.model || '')}" placeholder="opus / sonnet / để trống"></div>
    <div class="row"><label for="s-ref">Bản repo cho job<small>Mặc định origin/main (lấy bản mới nhất trước mỗi job).</small></label><input class="inp mono" id="s-ref" value="${esc(s.git_ref || 'origin/main')}"></div>
    <div class="btns"><button class="btn btn-pri" type="submit">Lưu cài đặt</button></div></form>
    <div class="form"><h3>Hàng đợi</h3><p class="sub" style="margin:0 0 12px">${b.paused_until ? `Đang tạm dừng tới ${hhmm(b.paused_until)} vì hết hạn mức Claude.` : 'Hàng đợi đang chạy bình thường.'}</p>
      <div class="btns" style="justify-content:flex-start"><button class="btn btn-sec" id="s-resume" ${b.paused_until ? '' : 'hidden'}>Chạy tiếp ngay</button></div>
      ${b.claude ? `<p class="hint">Claude CLI: ${b.claude.ok ? esc(b.claude.version || 'OK') : 'không gọi được'}</p>` : ''}</div>
    <form class="form" id="pw-form"><h3>Đổi mật khẩu Admin</h3>
      <div class="row"><label for="s-pw">Mật khẩu mới<small>Tối thiểu 6 ký tự.</small></label><input class="inp" id="s-pw" type="password" autocomplete="new-password"></div>
      <div class="btns"><button class="btn btn-sec" type="submit">Đổi mật khẩu</button></div></form>`;
  $('#set-form').onsubmit = async (e) => {
    e.preventDefault();
    const body = {slots: Number($('#s-slots').value), timeout_min: Number($('#s-timeout').value), allowed_roots: $('#s-roots').value.split('\n'),
                  model: $('#s-model').value, git_ref: $('#s-ref').value};
    try { await api('/api/settings', {method: 'PUT', json: body}); toast('Đã lưu cài đặt.', 'ok'); state.etag = null; poll(true); loadSettings(); } catch (err) { toast(errText(err), 'err'); }
  };
  $('#pw-form').onsubmit = async (e) => {
    e.preventDefault();
    try { await api('/api/admin/password', {method: 'POST', json: {password: $('#s-pw').value}}); toast('Đã đổi mật khẩu.', 'ok'); $('#s-pw').value = ''; } catch (err) { toast(errText(err), 'err'); }
  };
  $('#s-resume').onclick = resumeQueue;
}
async function resumeQueue() {
  try { await api('/api/queue/resume', {method: 'POST'}); toast('Hàng đợi chạy tiếp.', 'ok'); state.etag = null; poll(true); } catch (e) { toast(errText(e), 'err'); }
}

/* ---------- me ---------- */
function renderMe() {
  const t = document.documentElement.dataset.theme || 'system';
  const admin = state.me.is_admin;
  $('#mepage').innerHTML = `<div class="form"><h3>Bạn</h3>
    <div class="row"><label>Tên hiển thị</label><div><span style="font-weight:500">${esc(state.me.user ? state.me.user.name : 'Chưa có tên')}</span> <button class="btn btn-ghost" id="me-rename">Đổi tên</button></div></div>
    <div class="row"><label>Giao diện</label><div class="seg" id="me-theme"><button data-t="light" class="${t === 'light' ? 'on' : ''}">Sáng</button><button data-t="dark" class="${t === 'dark' ? 'on' : ''}">Tối</button><button data-t="system" class="${t === 'system' ? 'on' : ''}">Theo hệ thống</button></div></div>
    <div class="row"><label>Quyền Admin</label><div>${admin ? '<span class="badge b-ok">Đang đăng nhập</span> <button class="btn btn-ghost" id="me-logout">Đăng xuất Admin</button>' : `<button class="btn btn-sec" id="me-login">${icon('lock')}Đăng nhập Admin</button>`}</div></div></div>`;
  $('#me-rename').onclick = () => askName(false).then(renderMe);
  $('#me-theme').onclick = (e) => { const b = e.target.closest('button'); if (b) { setTheme(b.dataset.t); renderMe(); } };
  if (admin) $('#me-logout').onclick = async () => { await api('/api/admin/logout', {method: 'POST'}); await loadMe(); state.etag = null; poll(true); renderMe(); };
  else $('#me-login').onclick = () => adminLogin().then(renderMe);
}

/* ---------- notifications ---------- */
async function pollNotifications() {
  try {
    const r = await api('/api/me/notifications' + (state.notifId != null ? `?since=${state.notifId}` : ''));
    if (state.notifId != null) for (const n of r.data.items) toast(n.text, n.kind, () => openRun(n.run_id));
    state.notifId = r.data.last_id;
  } catch (e) { /* not named yet */ }
  setTimeout(pollNotifications, document.hidden ? 15000 : 5000);
}

/* ---------- wiring ---------- */
function wire() {
  setTheme(document.documentElement.dataset.theme || 'system');
  $('#theme').onclick = (e) => { const b = e.target.closest('button'); if (b) setTheme(b.dataset.t); };
  window.addEventListener('hashchange', route);
  $('#path').addEventListener('input', onPathInput);
  $('#path').addEventListener('keydown', (e) => { if (e.key === 'Enter') submit('RUN'); });
  $('#btn-run').onclick = () => submit('RUN');
  $('#btn-qa').onclick = () => submit('QA');
  $('#picker').addEventListener('click', (e) => {
    const b = e.target.closest('[data-pick]');
    if (b) document.querySelectorAll('#picker input[type=checkbox]').forEach((x) => { x.checked = b.dataset.pick === 'all'; });
    updateRunLabel();
  });
  $('#picker').addEventListener('change', updateRunLabel);
  const boardClick = (e) => {
    const t = e.target.closest('[data-act],[data-id]'); if (!t) return;
    const holder = t.closest('[data-id]'); const id = holder ? Number(holder.dataset.id) : null;
    const act = t.dataset.act;
    if (act === 'resume') return resumeQueue();
    const r = id ? findRun(id) : null;
    if (act === 'cancel' && r) return cancelRun(r);
    if (id) openRun(id);
  };
  $('#view-board').addEventListener('click', (e) => { if (e.target.closest('.cmd,#picker')) return; boardClick(e); });
  $('#history').addEventListener('click', (e) => {
    const tr = e.target.closest('tr[data-id]'); if (!tr) return;
    const r = findRun(Number(tr.dataset.id));
    if (e.target.closest('[data-act="rerun"]') && r) rerunRun(r); else openRun(Number(tr.dataset.id));
  });
  ['#h-q', '#h-user'].forEach((s) => $(s).addEventListener('input', historyQuery));
  ['#h-status', '#h-kind', '#h-from', '#h-to'].forEach((s) => $(s).addEventListener('change', loadHistory));
  $('#h-csv').onclick = () => { location.href = '/api/runs.csv?' + new URLSearchParams({q: $('#h-q').value, status: $('#h-status').value, kind: $('#h-kind').value}); };
  $('#rv-filter').onclick = (e) => {
    const b = e.target.closest('button'); if (!b) return;
    rvFilter = b.dataset.s;
    document.querySelectorAll('#rv-filter button').forEach((x) => x.classList.toggle('on', x === b));
    loadReview();
  };
  $('#rv-file').addEventListener('change', uploadAttachment);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && $('#drawer-root').innerHTML && !$('#modal-root').innerHTML) closeDrawer(); });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
  setInterval(tickClocks, 1000);
}
async function main() {
  wire();
  try { await loadMe(); } catch (e) { setHint('Không kết nối được máy chủ Luan App.', 'err'); return; }
  if (!state.me.user && !state.me.is_admin) await askName(true);
  route();
  poll(true);
  pollNotifications();
}
main();
