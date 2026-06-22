const state = { data: {}, selectedDate: null, currentMonth: 0, currentYear: 0 };
let currentES = null;

const $ = id => document.getElementById(id);
const startInp = $('startDate'), endInp = $('endDate'), searchBtn = $('searchBtn');
const statusEl = $('status'), calendarWrap = $('calendarWrap');
const monthLabel = $('monthLabel'), calendarGrid = $('calendarGrid');
const prevBtn = $('prevMonth'), nextBtn = $('nextMonth');
const detailPanel = $('detailPanel'), detailDate = $('detailDate');
const detailStatus = $('detailStatus'), detailBody = $('detailBody');
const progressWrap = $('progressWrap'), progressFill = $('progressFill'), progressText = $('progressText');
const cacheBadge = $('cacheBadge'), lastScanTime = $('lastScanTime');

function today() { const d = new Date(); d.setHours(0,0,0,0); return d; }
function fmt(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dd}`;
}
function addDays(d, n) { const r = new Date(d); r.setDate(r.getDate()+n); return r; }

function initDates() {
  const t = today();
  const minDate = addDays(t, 1), maxDate = addDays(t, 30);
  startInp.min = fmt(minDate); startInp.max = fmt(maxDate);
  endInp.min = fmt(addDays(minDate,1)); endInp.max = fmt(maxDate);
  startInp.value = fmt(minDate);
  endInp.value = fmt(addDays(minDate, 7) > maxDate ? maxDate : addDays(minDate, 7));
}

function showStatus(type, msg) {
  statusEl.className = 'status ' + type;
  statusEl.textContent = msg;
  statusEl.style.display = 'block';
}
function hideStatus() { statusEl.style.display = 'none'; }

function showProgress(scanned, total) {
  progressWrap.classList.add('active');
  const pct = total > 0 ? Math.round((scanned / total) * 100) : 0;
  progressFill.style.width = pct + '%';
  progressText.textContent = `${scanned} / ${total} 天`;
}
function hideProgress() {
  progressWrap.classList.remove('active');
  progressFill.style.width = '0%';
}

function showCacheBadge(ts) {
  cacheBadge.style.display = 'flex';
  const since = new Date(ts);
  const now = new Date();
  const hoursAgo = Math.round((now - since) / 3600000);
  const localStr = since.toLocaleString('zh-TW', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
  const freshness = hoursAgo < 12
    ? `<span class="fresh">&#x1F7E2; ${hoursAgo} 小時前</span>`
    : `<span class="stale">&#x1F7E1; ${hoursAgo} 小時前</span>`;
  lastScanTime.innerHTML = `${localStr}（${freshness}）`;
}
function hideCacheBadge() { cacheBadge.style.display = 'none'; }

async function fetchRooms(date) {
  const r = await fetch(`/api/rooms?date=${date}`);
  if (!r.ok) throw new Error(`伺服器錯誤: ${r.status}`);
  const j = await r.json();
  return j.data;
}
async function fetchLatest() {
  const r = await fetch('/api/latest');
  if (!r.ok) return null;
  const j = await r.json();
  return j.data || null;
}
async function fetchLatestMeta() {
  const r = await fetch('/api/latest-meta');
  if (!r.ok) return null;
  const j = await r.json();
  return j.meta || null;
}

function renderCalendar(year, month) {
  state.currentYear = year; state.currentMonth = month;
  monthLabel.textContent = `${year} 年 ${month + 1} 月`;

  const cells = [];
  for (let i = 0; i < 7; i++) cells.push(calendarGrid.children[i]);
  calendarGrid.innerHTML = '';
  cells.forEach(c => calendarGrid.appendChild(c));

  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const startDow = first.getDay();
  const todayStr = fmt(today());

  for (let i = 0; i < startDow; i++) {
    const cell = document.createElement('div');
    cell.className = 'day-cell outside';
    calendarGrid.appendChild(cell);
  }

  for (let d = 1; d <= last.getDate(); d++) {
    const ds = fmt(new Date(year, month, d));
    const cell = document.createElement('div');
    cell.className = 'day-cell';
    cell.dataset.date = ds;
    if (ds === todayStr) cell.classList.add('today');

    const info = state.data[ds];
    const inRange = ds >= startInp.value && ds <= endInp.value;

    if (!inRange) {
      cell.classList.add('outside');
      cell.textContent = d;
    } else if (info === undefined) {
      cell.classList.add('pending');
      cell.innerHTML = `${d}<span class="badge">&#x25CC;</span>`;
    } else if (info.available) {
      cell.classList.add('available');
      cell.innerHTML = `${d}<span class="badge">● ${info.room_count||''}</span>`;
    } else {
      cell.classList.add('soldout');
      cell.innerHTML = `${d}<span class="badge">&#x2715;</span>`;
    }
    if (info && info.changes) {
      cell.classList.add('changed');
      cell.title = '🔄 房況有變動';
    }

    if (ds === state.selectedDate) cell.classList.add('selected');
    cell.addEventListener('click', () => onDateClick(ds));
    calendarGrid.appendChild(cell);
  }
}

function navigateMonth(delta) {
  state.currentMonth += delta;
  if (state.currentMonth > 11) { state.currentMonth = 0; state.currentYear++; }
  if (state.currentMonth < 0) { state.currentMonth = 11; state.currentYear--; }
  renderCalendar(state.currentYear, state.currentMonth);
}

async function onDateClick(ds) {
  if (!state.data[ds] || !state.data[ds].available) return;
  state.selectedDate = ds;
  renderCalendar(state.currentYear, state.currentMonth);

  detailPanel.classList.remove('active');
  detailBody.innerHTML = '<p style="color:var(--muted)">載入中…</p>';
  detailPanel.classList.add('active');

  try {
    const info = await fetchRooms(ds);
    const dd = new Date(ds);
    const weekdays = ['日','一','二','三','四','五','六'];
    detailDate.textContent = `${ds} (${weekdays[dd.getDay()]})`;
    const availCount = info.rooms.filter(r => r.available).length;
    detailStatus.textContent = availCount > 0 ? `✅ ${availCount} 間可訂` : '❌ 已售完';

    const changes = state.data[ds]?.changes || [];
    const changeMap = {};
    changes.forEach(c => { changeMap[c.name] = c; });

    detailBody.innerHTML = info.rooms.map(r => {
      const c = changeMap[r.name];
      let changeHtml = '';
      if (c) {
        changeHtml = c.from
          ? `<span class="change-tag taken">⬆ 被訂走</span>`
          : `<span class="change-tag freed">⬇ 釋出</span>`;
      }
      const nameHtml = r.url
        ? `<a class="rname-link" href="${r.url}" target="_blank" rel="noopener">${r.name}</a>`
        : `<span class="rname">${r.name}</span>`;
      return `
      <div class="room-row ${r.available ? 'avail' : 'sold'}">
        ${nameHtml}
        <span class="rstatus ${r.available ? 'avail' : 'sold'}">
          ${r.available ? '✅ 可訂' : '❌ 已售完'}
        </span>
        ${changeHtml}
      </div>
      `;
    }).join('');
  } catch(e) {
    detailBody.innerHTML = `<p style="color:var(--red)">⚠️ 讀取失敗: ${e.message}</p>`;
  }
}

function doSearchSSE(start, end) {
  if (currentES) { currentES.close(); currentES = null; }

  hideStatus();
  hideProgress();
  hideCacheBadge();
  searchBtn.disabled = true;
  searchBtn.textContent = '查詢中…';
  state.data = {};
  state.selectedDate = null;
  detailPanel.classList.remove('active');

  const startD = new Date(start);
  state.currentYear = startD.getFullYear();
  state.currentMonth = startD.getMonth();
  calendarWrap.style.display = 'block';
  renderCalendar(state.currentYear, state.currentMonth);

  const es = new EventSource(`/api/scan-stream?start=${start}&end=${end}`);
  currentES = es;
  let total = 0;
  let availCount = 0;

  es.addEventListener('meta', (e) => {
    total = JSON.parse(e.data).total;
    showProgress(0, total);
  });

  es.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    const { scanned, total: t, date, available } = data;
    total = t;
    state.data[date] = data;
    if (available) availCount++;

    showProgress(scanned, total);

    const cell = document.querySelector(`.day-cell[data-date="${date}"]`);
    if (cell) {
      cell.classList.remove('pending', 'streaming');
      if (available) {
        cell.classList.add('available');
        cell.innerHTML = `${new Date(date).getDate()}<span class="badge">● ${data.room_count||''}</span>`;
      } else {
        cell.classList.add('soldout');
        cell.innerHTML = `${new Date(date).getDate()}<span class="badge">&#x2715;</span>`;
      }
      cell.classList.add('streaming');
      setTimeout(() => cell.classList.remove('streaming'), 3000);
    }
  });

  es.addEventListener('done', (e) => {
    es.close();
    currentES = null;
    searchBtn.disabled = false;
    searchBtn.textContent = '🔍 查詢';

    const summary = total > 0
      ? (availCount === 0
          ? `📭 ${total} 天中皆無空房`
          : `✅ ${total} 天中有 ${availCount} 天有空房`)
      : '❌ 查詢無結果';
    showStatus('empty', summary);
    hideProgress();
  });

  es.onerror = () => {
    if (es === currentES) {
      es.close();
      currentES = null;
      searchBtn.disabled = false;
      searchBtn.textContent = '🔍 查詢';
      hideProgress();
      if (Object.keys(state.data).length === 0) {
        showStatus('error', '⚠️ 連線中斷，請重試');
      } else {
        showStatus('empty', `部分完成（${Object.keys(state.data).length} 天）`);
      }
    }
  };
}

async function loadCache() {
  const meta = await fetchLatestMeta();
  if (!meta) return;
  showCacheBadge(meta.scanned_at);

  const data = await fetchLatest();
  if (!data || data.length === 0) return;

  data.forEach(r => { state.data[r.date] = r; });

  const keys = Object.keys(state.data).sort();
  if (keys.length > 0) {
    const startD = new Date(keys[0]);
    state.currentYear = startD.getFullYear();
    state.currentMonth = startD.getMonth();
    startInp.value = keys[0];
    endInp.value = keys[keys.length - 1];
  } else {
    const t = today();
    state.currentYear = t.getFullYear();
    state.currentMonth = t.getMonth();
  }

  calendarWrap.style.display = 'block';
  renderCalendar(state.currentYear, state.currentMonth);

  const availCount = data.filter(r => r.available).length;
  showStatus('empty', `✅ 快取資料 — ${data.length} 天中有 ${availCount} 天有空房`);
}

function doSearch() {
  const start = startInp.value, end = endInp.value;
  if (!start || !end) { showStatus('error','請選擇日期範圍'); return; }
  if (start > end) { showStatus('error','開始日期不能晚於結束日期'); return; }
  doSearchSSE(start, end);
}

// ── 資料庫匯出 / 匯入 ──

const dbExportBtn = $('dbExportBtn');
const dbImportBtn = $('dbImportBtn');
const dbFileInput = $('dbFileInput');
const dbToolsStatus = $('dbToolsStatus');

function dbStatus(msg, type) {
  dbToolsStatus.textContent = msg;
  dbToolsStatus.className = 'db-tools-status' + (type ? ' ' + type : '');
}

dbExportBtn.addEventListener('click', () => {
  const a = document.createElement('a');
  a.href = '/api/db/export';
  a.download = '';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  dbStatus('已觸發下載', 'ok');
});

dbImportBtn.addEventListener('click', () => dbFileInput.click());

dbFileInput.addEventListener('change', async () => {
  const file = dbFileInput.files[0];
  if (!file) return;
  if (!file.name.endsWith('.db')) {
    dbStatus('請選擇 .db 檔案', 'err');
    dbFileInput.value = '';
    return;
  }
  dbStatus('上傳中…');
  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await fetch('/api/db/import', { method: 'POST', body: fd });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || j.message || '匯入失敗');
    dbStatus(`✅ 匯入成功（${j.rows} 筆），重新載入…`, 'ok');
    dbFileInput.value = '';
    setTimeout(() => location.reload(), 1200);
  } catch (e) {
    dbStatus(`❌ ${e.message}`, 'err');
    dbFileInput.value = '';
  }
});

initDates();
prevBtn.addEventListener('click', () => navigateMonth(-1));
nextBtn.addEventListener('click', () => navigateMonth(1));
searchBtn.addEventListener('click', doSearch);
startInp.addEventListener('change', () => {
  const min = addDays(new Date(startInp.value), 1);
  endInp.min = fmt(min);
  if (endInp.value < fmt(min)) endInp.value = fmt(min);
});

loadCache();
