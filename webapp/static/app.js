/* StockBot Web App — read-only reader for materialized Analyst Views.
 *
 * 這一層**只改資訊階層**：分組、排序、換標籤。它不產生任何新的 summary judgment、
 * 不做任何算術、不合併任何數字。畫面上每一個數與每一句理由都是 API 回來的那一格原文。
 *
 * 缺席一律以「值 + 為什麼沒有」呈現，永遠不留白、永遠不寫 0（missing != zero）。
 * 缺席語意的中文說明來自 /api/v1/meta 的字彙表——前端**不維護第二份對照表**。
 */
'use strict';

const API = '/api/v1';
const app = document.getElementById('app');
const footerWarning = document.getElementById('footer-warning');

let VOCAB = null;

/* ---------- 取數 ---------- */

async function getJSON(path) {
  const response = await fetch(path, { headers: { Accept: 'application/json' } });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const err = new Error('request failed');
    err.status = response.status;
    err.body = body;
    throw err;
  }
  return body;
}

/* ---------- 未收盤 K 棒（Phase 6 Step 6.7c） ---------- */

/* 取價端拿掉的盤中 K 棒、說不出收盤了沒的——有才印（daily 05:30 各市場都已收盤，平常是空的）。
   判定住 alpha.providers.close_series（追蹤表與計分表同一支）；字彙跟著 artifact 的 closing_bars.labels，前端不另存一份。 */
function closingBarsNote(budget) {
  const bars = (budget || {}).closing_bars || {};
  const dropped = bars.dropped_unfinished || [];
  const unknown = bars.close_unknown || [];
  if (!dropped.length && !unknown.length) return null;
  const note = el('p', 'warn', `未收盤 K 棒：拿掉 ${dropped.length} 檔${dropped.length ? '（' + dropped.join('、') + '）' : ''}`
    + `——那幾檔的現價是前一個收盤；收盤狀態未知 ${unknown.length} 檔${unknown.length ? '（' + unknown.join('、') + '，照用最後一根）' : ''}`);
  const labels = bars.labels || {};
  note.title = [labels.dropped_unfinished, labels.close_unknown].filter(Boolean).join('\n');
  return note;
}

/* ---------- APP 自己的程式新不新（Phase 6 Step 6.7b） ---------- */

/* 長駐的 APP 會一直跑啟動時載入的程式（Phase 5 實測：09-10 起跑的 APP 一路用 09-10 的程式，新頁面全回 404，
   畫面上沒有任何東西說「我是舊的」）。每次換頁問一次 /health：伺服器比對啟動時與現在的程式指紋（只做本機 stat）。
   ⚠ health 沒有 `code` 這一格＝伺服器比這份 app.js 舊（static 每次從磁碟讀，新畫面會先跑在舊伺服器上）——也要印。 */
async function checkCodeFreshness() {
  let banner = document.getElementById('code-banner');
  if (!banner) {
    banner = el('div', 'code-banner');
    banner.id = 'code-banner';
    banner.hidden = true;
    app.parentNode.insertBefore(banner, app);
  }
  let health;
  try {
    health = await getJSON(`${API}/health`);
  } catch (err) {
    return;  // 健康檢查讀不到：頁面本身的載入錯誤會說話，這裡不另印
  }
  const code = health && health.code;
  let text = null;
  if (!code) text = 'APP 跑的程式比這個畫面舊（健康檢查沒有程式指紋）——請重啟';
  else if (code.stale) text = `APP 跑的是 ${code.started_at} 的程式，之後程式有更新——請重啟`;
  banner.textContent = text || '';
  banner.title = (text && code)
    ? `啟動時 ${code.loaded.files} 個檔、最新改動 ${code.loaded.newest_at}｜現在 ${code.current.files} 個檔、最新改動 ${code.current.newest_at}（${code.scope}）`
    : '';
  banner.hidden = !text;
}

/* ---------- 格式化（只排版，不換算） ---------- */

/* 顯示精度：**只截尾，不換算**。minimumFractionDigits=0 讓 223.6035 印成「223.6」而不是
   補一個看起來更精確的「223.60」；GBp 這種便士級數字則保留到小數第三位。 */
function fmtNumber(value, digits) {
  if (typeof value !== 'number' || !isFinite(value)) return null;
  return value.toLocaleString('zh-Hant', {
    minimumFractionDigits: 0, maximumFractionDigits: digits,
  });
}

/** 價格／目標值：**不做任何幣別或單位換算**——GBp 就印 GBp（它與 GBP 差 100 倍）。 */
function fmtQuantity(value, unit) {
  const text = fmtNumber(value, decimalsFor(value));
  if (text === null) return null;
  return unit ? `${text} ${unit}` : text;
}

function decimalsFor(value) {
  const abs = Math.abs(value);
  if (abs >= 1000) return 0;
  if (abs >= 100) return 2;
  if (abs >= 1) return 3;
  return 4;
}

function fmtPercent(value) {
  if (typeof value !== 'number' || !isFinite(value)) return null;
  const text = (value * 100).toLocaleString('zh-Hant', {
    minimumFractionDigits: 1, maximumFractionDigits: 1,
  });
  return `${value > 0 ? '+' : ''}${text}%`;
}

function signClass(value) {
  if (typeof value !== 'number' || !isFinite(value)) return '';
  return value >= 0 ? 'pos' : 'neg';
}

/* 大數字的可讀寫法：10227652000 → 「102.3 億」。**只是排版**，與百分比的 ×100 同性質——
   不換幣別、不改語意，原值仍放在 title 屬性裡隨時查得到。 */
function fmtBig(n, unit) {
  if (typeof n !== 'number' || !isFinite(n)) return null;
  const abs = Math.abs(n);
  let text;
  if (abs >= 1e8) text = fmtNumber(n / 1e8, 1) + ' 億';
  else if (abs >= 1e4) text = fmtNumber(n / 1e4, 1) + ' 萬';
  else text = fmtNumber(n, decimalsFor(n));
  return unit ? `${text} ${unit}` : text;
}

/* 認不得的形狀：逐格 `鍵：值` 攤出來。醜，但**看得到**——這比一句「見下方展開」誠實。 */
function keyValueList(obj) {
  const box = el('div', 'row-reason');
  box.textContent = Object.keys(obj).map((key) => {
    const item = obj[key];
    if (item === null || item === undefined) return `${key}：—`;
    if (typeof item === 'number') return `${key}：${fmtBig(item)}`;
    if (typeof item === 'object') return `${key}：${JSON.stringify(item)}`;
    return `${key}：${item}`;
  }).join('　');
  return box;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

/* ---------- 字彙（全部來自 API） ---------- */

function absenceLabel(kind) {
  if (!kind) return null;
  const table = (VOCAB && VOCAB.absence_kinds) || {};
  return table[kind] || kind;
}

function isSettled(kind) {
  const list = (VOCAB && VOCAB.settled_absence_kinds) || [];
  return list.indexOf(kind) >= 0;
}

function absenceBadge(kind) {
  if (!kind) return null;
  // 短標籤來自 /api/v1/meta（`plain_absence_short`）——前端**不維護第二份對照表**：
  // 先前這裡是硬編碼的 ABSENCE_SHORT，那正是 L16 說的重造品，字彙一改它就開始偏離。
  const short = (VOCAB && VOCAB.plain_absence_short) || {};
  const badge = el('span', 'badge ' + (isSettled(kind) ? 'badge-settled' : 'badge-absence'),
                   short[kind] || kind);
  badge.title = absenceLabel(kind);
  return badge;
}

/* ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：opinion stance 那一組（stanceInfo／isOpinionless／viewStance／
   stanceBadge／stanceBanner）與 appendReturnBlock（隱含報酬那一格）退役。stance 是 FY+1 模型對估值假設
   derivation 的聚合，隱含報酬是估值鏈的終點——兩者都不在 read model 裡了。 */

/* ⚠ 2026-10-28：卡片上的 readiness 徽章（readinessBadge／readinessLabel）隨首頁 compact 拿掉——那是給機器看的狀態，
   個股頁的稽核區照樣印得出來（使用者：「首頁根本不用講這麼多」）。
   同日 truncate 隨「在等什麼」頁拿掉（唯一的使用者是那一頁的反證摘要）。 */

/* ---------- 清單 ---------- */

function numberBlock(label, valueText, subText, klass) {
  const box = el('div', 'num');
  box.appendChild(el('div', 'num-label', label));
  box.appendChild(el('div', 'num-value ' + (klass || ''), valueText));
  if (subText) box.appendChild(el('div', 'num-sub', subText));
  return box;
}

/* 首頁卡片（2026-10-28 使用者：「首頁根本不用講這麼多…compact 一點…有 30d 折線圖…10 字左右的介紹吧。不然我也不會點進去」）。
   只留四樣：名字＋代號｜一句做什麼｜狀態多久與哪天重看｜30 個交易日折線（有主題組的加印本檔與比組）。短評全文、readiness、
   缺席理由都在個股頁。每一格都是 materialize 端 `overview.card` 的原值；沒寫介紹就說「還沒寫介紹」，不留白（INV-3）。 */
function renderCard(row) {
  const card = el('a', 'card card-compact');
  card.href = '#/' + encodeURIComponent(row.ticker);
  const c = row.card || {};
  const body = el('div', 'card-body');
  const title = el('div', 'card-title');
  title.appendChild(el('span', 'card-name', c.short_name || row.company_label || row.ticker));
  title.appendChild(el('span', 'card-ticker', row.ticker));
  if (row.freshness && row.freshness.state === 'stale') {
    const b = el('span', 'badge badge-stale', 'stale');
    b.title = row.freshness.rule;
    title.appendChild(b);
  }
  body.appendChild(title);
  const tag = c.tagline || {};
  // 一句做什麼的來源分開標（L12）：研究寫的介紹照印；沒寫時退到押的層的中文名（前面加「押在」）；再沒有就說還沒寫
  const tagText = tag.source === 'ledger' ? tag.text : (tag.source === 'layer' ? `押在 ${tag.text}` : '還沒寫介紹');
  body.appendChild(el('div', 'card-tagline' + (tag.source === 'ledger' ? '' : ' absent'), tagText));
  body.appendChild(cardStateLine(row));
  card.appendChild(body);
  card.appendChild(cardSpark(c));
  return card;
}

/* 狀態那一行：候選狀態（照抄）· 這個狀態幾天（敘事連續宣告同一個狀態的天數；狀態不是敘事宣告的就不印）· 哪天重看。 */
function cardStateLine(row) {
  const c = row.card || {};
  const cand = row.candidate || {};
  const line = el('div', 'card-state');
  if (cand.label) line.appendChild(el('span', 'card-chip chip-' + (cand.list_group || 'none'), cand.label));
  // 敘事該重寫（候選列 rewrite[] 的筆數，materialize 端照數）：這張卡的狀態可能已經舊了（2026-10-28 候選板那一區搬來）
  if (typeof c.rewrite === 'number' && c.rewrite > 0) {
    line.appendChild(el('span', 'card-chip chip-rewrite', `敘事該重寫 ${c.rewrite}`));
  }
  if (typeof c.stall_days === 'number') {
    const days = el('span', 'card-days', c.stall_days === 0 ? '今天起' : `${c.stall_days} 天`);
    days.title = `這個狀態從 ${c.since || '—'} 起（敘事連續宣告同一個狀態的天數）`;
    line.appendChild(days);
  }
  if (c.watch && c.watch.until) {
    const label = c.watch.label || c.watch.until;            // 印法由 API 定（別年的印全日期）
    const when = el('span', 'card-when' + (c.watch.past ? ' past' : ''),
      c.watch.past ? `${label} 該重看了` : `${label} 重看`);
    when.title = `研究寫下的重看日 ${c.watch.until}`;
    line.appendChild(when);
  }
  return line;
}

/* 折線與漲跌。漲跌只印三題「已定價③：相對組 30 個交易日」已算好的數（沒有主題組的檔只畫線）——前端不另算報酬。 */
function cardSpark(c) {
  const box = el('div', 'card-spark');
  const pts = c.spark || [];
  if (pts.length >= 2) box.appendChild(sparkline(pts));
  else box.appendChild(el('span', 'card-nospark', '沒有收盤'));
  const m = c.move;
  if (m && typeof m.own === 'number') {
    const own = el('div', 'spark-own', signedPct(m.own));
    own.title = `${m.label || '30 個交易日'}：本檔 ${signedPct(m.own)}、主題等權組 ${signedPct(m.cohort)}（${m.as_of || ''}）`;
    box.appendChild(own);
    box.appendChild(el('div', 'spark-rel', `比組 ${signedPct(m.relative)}`));
  }
  return box;
}

function cardGrid(rows) {
  const cards = el('div', 'cards cards-compact');
  rows.forEach((row) => { if (row) cards.appendChild(renderCard(row)); });
  return cards;
}

/* 「接下來兩週會揭曉」：日期序由後端排好（時間序不是名次），前端照印。 */
function renderCalendar(cal) {
  if (!cal || !(cal.dates || []).length) return null;
  const box = el('section', 'calendar');
  box.appendChild(el('h2', 'group-head', `接下來 ${cal.days} 天會揭曉`));
  const strip = el('div', 'cal-strip');
  cal.dates.forEach((d) => {
    const day = el('div', 'cal-day' + (d.past ? ' past' : ''));
    day.appendChild(el('div', 'cal-date', d.past ? `${d.date.slice(5)} 已過` : d.date.slice(5)));
    const names = el('div', 'cal-names');
    (d.stocks || []).forEach((s, i) => {
      if (i) names.appendChild(document.createTextNode('、'));
      const a = el('a', null, s.name || s.ticker);
      a.href = '#/' + encodeURIComponent(s.ticker);
      a.title = `${s.ticker}${s.state ? '｜' + s.state : ''}`;
      names.appendChild(a);
    });
    day.appendChild(names);
    strip.appendChild(day);
  });
  box.appendChild(strip);
  if (cal.note) box.appendChild(el('p', 'note', cal.note));
  return box;
}

function viewToggle(mode) {
  const bar = el('div', 'view-toggle');
  [['state', '依狀態', '#/'], ['layer', '依層', '#/by-layer']].forEach((item) => {
    const a = el('a', 'toggle-btn' + (item[0] === mode ? ' on' : ''), item[1]);
    a.href = item[2];
    bar.appendChild(a);
  });
  return bar;
}

/* 收合的組（不要、無法量、還沒寫、非邊緣…）：照數、點開才畫卡片——攤開哪幾組由後端 `groups[].expanded` 說。 */
function collapsedGroup(group, rows) {
  const box = el('details', 'group-collapsed');
  box.appendChild(el('summary', null, `${group.label}（${rows.length}）`));
  let drawn = false;
  box.addEventListener('toggle', () => {
    if (box.open && !drawn) { box.appendChild(cardGrid(rows)); drawn = true; }
  });
  return box;
}

async function renderList(mode) {
  markNav('stocks');
  const data = await getJSON(`${API}/stocks`);
  app.textContent = '';
  footerWarning.textContent = data.correlation_warning || '';
  if (!data.stocks.length && !data.unavailable.length) {
    app.appendChild(el('p', 'empty',
      '還沒有任何 materialized 判讀。請在本機跑 `python -m webapp materialize <TICKER>`。'));
    return;
  }
  const cal = renderCalendar(data.calendar);
  if (cal) app.appendChild(cal);
  const byLayer = mode === 'layer' && data.by_layer;
  app.appendChild(viewToggle(byLayer ? 'layer' : 'state'));

  /* 分段呈現。組序、層序、組內順序都來自 /api/v1/stocks（後端已排好），前端不自己排、不自己命名。 */
  const groups = data.groups || [];
  const byTicker = {};
  data.stocks.forEach((row) => { byTicker[row.ticker] = row; });
  if (byLayer) {
    (byLayer.layers || []).forEach((layer) => {
      const head = el('h2', 'group-head', `${layer.label}（${layer.tickers.length}）`);
      if (layer.unit_label) head.appendChild(el('span', 'group-sub', layer.unit_label));
      app.appendChild(head);
      app.appendChild(cardGrid(layer.tickers.map((t) => byTicker[t])));
      if ((layer.others || []).length) {
        app.appendChild(el('p', 'note', '同一層另有：' + layer.others.map((o) => `${o.label} ${o.count}`).join('、')));
      }
    });
    if ((byLayer.unridden || []).length) {
      app.appendChild(el('h2', 'group-head', `還沒宣告押哪一層（${byLayer.unridden.length}）`));
      app.appendChild(cardGrid(byLayer.unridden.map((t) => byTicker[t])));
    }
    if (byLayer.note) app.appendChild(el('p', 'note', byLayer.note));
  }
  if (groups.length) {
    groups.forEach((group) => {
      const rows = data.stocks.filter((row) => row.group === group.key);
      if (!group.expanded) { if (rows.length) app.appendChild(collapsedGroup(group, rows)); return; }
      if (byLayer) return;                                  // 依層時攤開的組已按層畫過
      app.appendChild(el('h2', 'group-head', `${group.label}（${rows.length}）`));
      if (group.warning) app.appendChild(el('p', 'warn', '▲ ' + group.warning));
      // 攤開的組 0 也印（AGENTS：可開為零就零，不得為了非空放寬條件——讓它非空的路是研究）
      app.appendChild(rows.length ? cardGrid(rows) : el('p', 'note', '現在 0 檔。'));
    });
    if (byLayer) groups.filter((g) => g.warning).forEach((g) => app.appendChild(el('p', 'warn', '▲ ' + g.warning)));
    if (data.group_note) app.appendChild(mdParagraph(data.group_note));   // 句子帶 **強調**（2026-10-28：原樣印出星號）
    /* 各組檔數（0 也印）＋最老滯留——2026-10-28 候選板併進首頁，那一頁最上面那一行搬到這裡（常駐計數器，L14）。
       判定暫停的組印「未驗」不印數（候選板原本的寫法：0 與「沒驗」是兩件事，L12）。 */
    app.appendChild(el('p', 'note group-counts', '各組檔數：' + groups.map((g) =>
      `${g.label} ${g.warning ? '未驗' : g.count}`
      + (typeof g.oldest_stall_days === 'number' ? `（最老 ${g.oldest_stall_days} 天）` : '')).join('｜')));
  } else {
    app.appendChild(cardGrid(data.stocks));
  }

  /* 常駐計數器。**它必須自己出現**——寫在文件裡的檢查點六天內就被同一個形狀繞過兩次（L14）。
     2026-10-28：首頁 compact 後搬到頁尾一行（照樣每次都印）。 */
  const counters = data.view_counters;
  if (counters) {
    const bar = el('div', 'counter-bar');
    bar.appendChild(el('strong', null, counters.headline || ''));
    if (counters.note) bar.appendChild(el('span', 'note', counters.note));
    app.appendChild(bar);
  }

  if (data.unavailable.length) {
    const box = el('div', 'error');
    box.appendChild(el('h2', null, '讀不到的 artifact'));
    box.appendChild(el('p', 'note',
      '「讀不到」與「這檔沒有研究結論」是兩件事——後者會正常顯示成 blocked。'));
    const list = el('ul', 'notes');
    data.unavailable.forEach((row) => list.appendChild(el('li', null, `${row.ticker}：${row.reason}`)));
    box.appendChild(list);
    app.appendChild(box);
  }
}

/* ---------- 明細 ---------- */

function lineMap(panel) {
  const map = {};
  (panel.lines || []).forEach((line) => { map[line.key] = line; });
  return map;
}

function valueText(datum) {
  const value = datum.value;
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') {
    if (datum.unit === 'ratio') return fmtPercent(value);
    if (datum.unit === 'multiple') return (fmtNumber(value, 1) || '') + 'x';
    return fmtNumber(value, decimalsFor(value));
  }
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'string') return value;
  return null;   // 結構化的值交給各自的 renderer，不在這裡壓成一行 JSON
}

/* 展開裡不再套展開：`group` 是「有標題、但直接看得到內容」的區塊。
   判準一句話——**使用者已經點開「完整細節」了，他要的就是內容**。 */
function group(title, buildBody) {
  const box = el('div', 'group');
  box.appendChild(el('div', 'group-title', title));
  box.appendChild(buildBody());
  return box;
}

function drill(title, buildBody) {
  const node = document.createElement('details');
  node.appendChild(el('summary', null, title));
  node.appendChild(buildBody());
  return node;
}

/* ⚠ 2026-10-28：kv（標籤＋說明一列）隨結構表頁拿掉——唯一的使用者是那一頁的「這份表的視角」。 */

function listOf(items) {
  const list = el('ul', 'notes');
  items.forEach((t) => list.appendChild(el('li', null, t)));
  return list;
}

/* ⚠ 2026-10-08：「完整細節」的五個面板（`renderHeadline`／`renderBet`／`renderFundamental`／`renderResearch`／
   `renderReadiness`／`renderFreshness`）隨那個大展開拿掉（使用者：「給機器看的不用顯示出來」）——現價在頁首、賭注是首屏「押什麼」、
   催化劑在「接下來看什麼」；共識原始數字、五軸分數、readiness 判準原文、digest 與新鮮度身分留在 artifact 與 API。 */

/* ---------- 白話別名：全部來自 /api/v1/meta，前端不維護第二份（L16） ---------- */

function plainPanel(key, fallback) {
  const table = (VOCAB && VOCAB.plain_panel_titles) || {};
  return table[key] || { title: fallback || key, hint: '' };
}

function plainLine(key, fallback) {
  const table = (VOCAB && VOCAB.plain_line_labels) || {};
  return table[key] || fallback || key;
}

/* ---------- 單檔判讀 ----------
   2026-09-08 使用者回饋：「太多展開、太多字、全部是內部術語，基本上看不懂」；2026-10-08：「舊有的資訊非必要的就拿掉，
   除非是給我看的；給機器看的不用顯示出來」。現在一頁＝頁首＋十三塊（`briefCard`），塊底下一個展開放論證與數字。
   ⚠ 刪的是版面不是內容：給查核用的每一格都還在 artifact 與 `/api/v1/stocks/<T>`。
   ⚠ 2026-10-08 拿掉的：「稽核」（結論卡、卡在哪、市場預測原始數字、填得滿表）與「完整細節」（現價每一格、賭注、
   市場預測、研究現況與五軸、判讀狀態、新鮮度、不是什麼）兩個大展開，以及頁尾「基本數字／憑什麼這樣想／讀圖／錯了怎麼知道」
   四張卡——人讀的部分搬進對應的塊（現價→頁首、這條鏈怎麼走→需求傳導、讀圖→技術鏈、反證與風險→錯了怎麼知道、
   時間表與催化劑→接下來看什麼、三題的數字→各自那一塊的「數字與出處」）。 */

/* 歸零旗標（D2，2026-09-18）：四盞燈只畫顏色與一句話——算出顏色的數字在「會不會死」那一塊的「數字與出處」。
   ⚠ 顏色**照抄** `alpha.wipeout` 的判定；本畫面不從 inputs 重判一次色，也不把四盞合成一個分數。
   ⚠ 灰燈與綠燈在畫面上必須一眼分得出來：灰＝這一項沒量到，不是「查過都沒事」。 */
const WIPEOUT_COLOURS = { red: { mark: '🔴', word: '紅' }, amber: { mark: '🟡', word: '黃' },
                          green: { mark: '🟢', word: '綠' } };

/** 股價走勢（脈絡不是訊號——AGENTS「量測、訊號、脈絡三分」；2026-10-08 起放在「怎麼被定價」那一塊、參考尺之後）。 */
function priceFigure(payload) {
  const series = payload.price_series || [];
  const price = (payload.overview && payload.overview.price) || {};
  const wrap = el('div', 'chart-wrap');
  wrap.appendChild(lineChart(series, {
    ariaLabel: `${payload.ticker} 收盤價`,
    emptyNote: '沒有取到這檔的收盤序列——沒有折線不是價格為 0。',
  }));
  const note = (VOCAB && VOCAB.price_series_note) || '';
  // 字彙裡的 `**…**` 是粗體標記——照 markdown 印（2026-10-08 實測：當成純文字會把兩個星號原樣露出來）
  wrap.appendChild(mdParagraph((series.length ? `收盤價：${series[0].session_date} 起 ${series.length} 個交易日` +
    (price.quote_unit ? `（${price.quote_unit}）。` : '。') : '') + note, 'chart-legend'));
  // 2026-10-07：「表格版：每一個交易日的收盤」拿掉（使用者：「不需要給我看的…拿掉」）——十字線 tooltip 讀得到每一天的值。
  return wrap;
}

/* 財務三題的數字（Phase 3 Step 3.7）：每一行＝值＋來源＋日期＋口徑＋規則，或缺席分型的中文。
   **照抄** three_questions 面板（read model 的同一格）；這裡只挑顯示格式（百分位、倍數、百分比、燈色），不算、不比、
   **沒有門檻**——幾分算已定價由寫敘事的人判斷。 */
const TQ_VALUE_FORMAT = {
  own_history_pctile: (v) => `第 ${fmtNumber(v, 1)} 百分位（自己跟自己比）`,
  cohort_median: (v) => `${fmtNumber(v, 2)} 倍`,
  rel_return_30d: (v) => fmtPercent(v),
  rel_return_90d: (v) => fmtPercent(v),
};

function tqValueText(datum) {
  const v = datum.value;
  if (v === null || v === undefined) return null;
  if (typeof v === 'string' && WIPEOUT_COLOURS[v]) return `${WIPEOUT_COLOURS[v].mark} ${WIPEOUT_COLOURS[v].word}`;
  const fmt = TQ_VALUE_FORMAT[(datum.dependencies || {}).row_key];
  if (fmt && typeof v === 'number') return fmt(v);
  if (typeof v === 'number') return fmtNumber(v, 2);
  if (Array.isArray(v)) return `${v.length} 期（逐期列在下面）`;
  if (typeof v === 'object') return '';
  return String(v);
}

/* 序列的一點（3.7 R1）：`alpha/three_questions.py` 產三種形狀——EDGAR 季／年
   `{period_end, value, filed, yoy, derived}`、台股月營收 `{data_month, revenue_twd_thousand, yoy, available_on}`、
   分部占比 `{as_of, revenue_mix}`。已知的鍵給白話，**認不得的鍵照印**（不得濾掉，INV-3）；`derived`（例：FY−9M 推算）
   照印出處——推算值與申報值不得同形（L18）。 */
const TQ_POINT_KEYS = {
  period_end: (v) => v, data_month: (v) => v, as_of: (v) => v,
  value: (v) => fmtBig(v), revenue_twd_thousand: (v) => `${fmtBig(v)}（千元）`,
  yoy: (v) => (typeof v === 'number' ? '年增 ' + fmtPercent(v) : null),
  filed: (v) => (v ? '申報 ' + v : null), available_on: (v) => (v ? '可用日 ' + v : null),
  derived: (v) => (v ? '推算：' + v : null),
  // 占比只對 0–1 的數字 ×100；其餘（例：total_ntd_thousand 金額、fiscal_period 字串、巢狀出處）照原形印（3.7 覆核）。
  revenue_mix: (v) => (v && typeof v === 'object'
    ? Object.keys(v).map((k) => {
      const x = v[k];
      if (typeof x === 'number') return `${k} ${x >= 0 && x <= 1 ? fmtRatioPct(x, 1) : fmtBig(x)}`;
      if (x && typeof x === 'object') return `${k} ${JSON.stringify(x)}`;
      return `${k} ${x}`;
    }).join('、') : null),
};

function tqPoint(point) {
  const li = el('li');
  if (!point || typeof point !== 'object') {
    li.textContent = String(point);
    return li;
  }
  const bits = [];
  Object.keys(TQ_POINT_KEYS).forEach((key) => {
    if (point[key] === null || point[key] === undefined) return;
    const text = TQ_POINT_KEYS[key](point[key]);
    if (text) bits.push(text);
  });
  li.appendChild(document.createTextNode(bits.join('｜')));
  const rest = {};
  Object.keys(point).forEach((key) => {
    if (!(key in TQ_POINT_KEYS) && point[key] !== null && point[key] !== undefined) rest[key] = point[key];
  });
  if (Object.keys(rest).length) li.appendChild(keyValueList(rest));
  return li;
}

/* 算出一格的輸入（`dependencies.detail`）印成人話（2026-10-08 使用者：「給機器看的不用顯示」）：
   認得的鍵給中文名、數字照格式印；**認不得的鍵照原名印**（不濾掉，INV-3）；巢狀的明細（逐筆申報、募資文件清單）只印筆數——
   原文在 `/api/v1/stocks/<T>` 與 artifact；已經印在這一行「來源／日期」的鍵（source、as_of、status）不重複印。 */
const TQ_DETAIL_LABELS = {
  multiple_today: '今天的倍數', median: '三年中位', min: '三年最低', max: '三年最高', samples: '樣本數',
  window_start: '起', window_end: '迄', trading_days_in_window: '窗內交易日', coverage: '覆蓋率',
  theme: '組', n_members: '組內檔數', n_same_basis: '同口徑檔數', currency: '幣別',
  cash_and_equivalents: '現金', free_cash_flow_ttm: '自由現金流（近四季）', runway_months: '現金撐幾個月',
  total_debt: '總債', market_cap_usd: '市值（美元）', base_outstanding: '期初股數', base_date: '期初日',
  last_outstanding: '最新股數', last_date: '最新日', change: '股數變化', issued_total: '期間發行金額',
  days_since_last: '距上次發行（天）', offering_summary: '募資文件', context_summary: '其他文件',
};
const TQ_DETAIL_PERCENT = { change: true, coverage: true };
const TQ_DETAIL_SKIP = { source: true, as_of: true, status: true };

function detailList(detail) {
  const bits = [];
  Object.keys(detail).forEach((key) => {
    const item = detail[key];
    if (TQ_DETAIL_SKIP[key] || item === null || item === undefined || item === '') return;
    const label = TQ_DETAIL_LABELS[key] || key;
    if (typeof item === 'number') bits.push(`${label}：${TQ_DETAIL_PERCENT[key] ? fmtPercent(item) : fmtBig(item)}`);
    else if (Array.isArray(item)) bits.push(`${label}：${item.length} 筆明細`);
    else if (typeof item === 'object') bits.push(`${label}：${Object.keys(item).length} 項明細`);
    else bits.push(`${label}：${item}`);
  });
  return bits.length ? el('div', 'row-reason', bits.join('　')) : null;
}

/** 財務三題某一題的每一行（原稽核區「財務三題的數字」那一題；2026-10-08 起住在那一塊的「數字與出處」裡）：
 *  值＋來源＋日期＋口徑＋規則，或缺席分型的中文。**照抄** three_questions 面板，這裡只挑顯示格式，不算、不比、沒有門檻。
 *  整個面板沒有任何一行＝這次沒有三題的數字（說為什麼，不印成空）。 */
function tqNumbers(view, question) {
  const panel = view.three_questions;
  if (!panel) return null;
  const all = (panel.lines || []).filter((line) => line.role === 'three_question');
  if (!all.length) {
    const box = el('div', 'attention flags');
    const head = el('div', 'attention-head', '這次沒有三題的數字　');
    const badge = absenceBadge(panel.absence_kind);
    if (badge) head.appendChild(badge);
    box.appendChild(head);
    if (panel.reason) box.appendChild(el('div', 'attention-body', panel.reason));
    return box;
  }
  const lines = all.filter((line) => (line.datum.dependencies || {}).question === question);
  if (!lines.length) return null;
  const box = el('div', 'rows');
  lines.forEach((line) => {
    const d = line.datum;
    const deps = d.dependencies || {};
    const row = el('div', 'row');
    row.appendChild(el('div', 'row-label', line.display_label));
    const text = tqValueText(d);
    if (text === null) {
      row.classList.add('row-absent');
      const cell = el('div', 'row-value');
      const badge = absenceBadge(d.absence_kind);
      if (badge) cell.appendChild(badge); else cell.appendChild(document.createTextNode('—'));
      row.appendChild(cell);
      row.appendChild(el('div', 'row-reason', absenceLabel(d.absence_kind) || ''));
      if (d.reason) row.appendChild(el('div', 'row-reason', d.reason));
    } else {
      row.appendChild(el('div', 'row-value', text));
      const where = [deps.source ? '來源 ' + deps.source : null, d.as_of ? String(d.as_of).slice(0, 10) : null,
        deps.basis ? '口徑 ' + deps.basis : null].filter(Boolean).join('｜');
      if (where) row.appendChild(el('div', 'row-reason', where));
      if (Array.isArray(d.value)) {
        const list = el('ul', 'weak');
        d.value.forEach((point) => list.appendChild(tqPoint(point)));
        row.appendChild(list);
      } else if (typeof d.value === 'object') {
        const inner = detailList(d.value);
        if (inner) row.appendChild(inner);
      }
    }
    // 算出這一格的輸入（倍數、中位數、窗、口徑理由）——敘事引用的數字要在這裡核對得到（AGENTS：敘事那一句引用這裡的數字）。
    if (deps.detail && typeof deps.detail === 'object' && Object.keys(deps.detail).length) {
      const inner = detailList(deps.detail);
      if (inner) row.appendChild(inner);
    }
    if (d.method) row.appendChild(el('div', 'rule', '規則：' + d.method));
    box.appendChild(row);
  });
  (panel.notes || []).forEach((text) => box.appendChild(el('p', 'note', text)));
  return box;
}

/* ⚠ 2026-10-08：「市場預測什麼」卡（`versusMarketCard`：會計年度別共識、賣方目標價的原始數字）隨稽核區拿掉——
   人要看的兩個本益比住「怎麼被定價」的數字與出處（`marketMultiples`）；共識原始數字留在 artifact 與 API。
   2026-09-23 退役的「我們估／市場共識／我們比市場」四欄表與反推表（COMPARE_ROWS／reverseBridgeBlock）不得復活。 */

/* 投資人短評（2026-09-15）：首屏只有這一張——七句前因後果、一把尺、一顆燈。
   文字是研究 session 寫進 ledger 的判斷，數字由 materialize 端從既有 Datum 填入；本畫面只排版。 */
function briefCard(payload, view) {
  const panel = view.brief;
  const meta = plainPanel('brief', panel ? panel.title : '這檔在賭什麼');
  const node = el('section', 'panel callout brief-card');
  node.appendChild(el('h2', null, meta.title));
  const lines = panel ? lineMap(panel) : {};
  const light = lines.brief_status_light && lines.brief_status_light.datum;
  if (light && light.value && light.value.label) {
    const badge = el('span', 'badge badge-light light-' + (light.value.state || 'unknown'), light.value.label);
    node.appendChild(badge);
  }
  // ⚠ 2026-09-23（Phase 0 Step 0b.1）：「目標價到了」那個徽章退役（`target_reached` 隨目標價退役）。
  // AGENTS D3 的判準沒有退役——`realized` 只提醒、不觸發出場；它現在的家是心跳段 2 的候選狀態板。
  const available = Boolean(panel && panel.context && panel.context.available);
  // 個股頁 S5（2026-10-08）：首屏照 page_schema 的段與塊排。**每一頁都用這個版面**（2026-10-08 使用者「舊的非必要就拿掉」：
  // 沒有敘事的頁也照十三塊排——研究要寫的塊印「還沒寫」，機械的塊照樣有燈、有圖），不再有第二套舊版面。
  const screen = schemaFirstScreen(payload, view, available ? panel : null);
  // 頁首那一行狀態（schema B0：候選狀態、理由、在等什麼）放在十三塊之前。
  const line = candidateLine(view, Boolean(screen));
  if (line) node.appendChild(line);
  if (!available) {
    const box = el('div', 'attention flags');
    box.appendChild(el('div', 'attention-head', '還沒寫短評'));
    box.appendChild(el('div', 'attention-body', (panel && panel.reason) || meta.hint));
    node.appendChild(box);
  }
  if (screen) {
    node.appendChild(screen);
  } else if (available) {     // `.meta.json` 讀不到十三塊的合約（舊 server）：短評每一格照印，不猜它屬於哪一塊
    const story = el('div', 'story');
    (panel.lines || []).filter((row) => row.key.indexOf('brief:') === 0)
      .forEach((row) => story.appendChild(storyRow(row)));
    node.appendChild(story);
  }
  const rides = view.bet && lineMap(view.bet).rides;
  if (available && rides && Array.isArray(rides.datum.value) && rides.datum.value.length) {
    const glossary = unitGlossary();
    if (glossary) node.appendChild(drill('名詞：層、插槽、押在哪一格', () => glossary));
  }
  // ⚠ **2026-09-23（Phase 0 Step 0b.1）：首屏那把尺與「要翻倍需要什麼為真」計算框整塊退役。**（估值鏈與多年反向橋）
  // 走勢圖 2026-10-08 搬進「怎麼被定價」那一塊（它是脈絡不是訊號——AGENTS「量測、訊號、脈絡三分」）。
  return node;
}

/** 短評的一格（標籤＋句子；partial 的理由放 title）。舊版面與五題版面共用。 */
function storyRow(line) {
  const row = el('div', 'story-row');
  row.appendChild(el('div', 'story-label', plainLine(line.key, line.display_label)));
  const text = el('div', 'story-text', String(line.datum.value || ''));
  if (line.datum.status === 'partial' && line.datum.reason) text.title = line.datum.reason;
  row.appendChild(text);
  return row;
}

/** 首屏（個股頁 S5，2026-10-08；取代 Phase 7 Step 7.0e 的五題）：段的順序與每塊的讀法來源**只有 page_schema 那一份**
 * （`.meta.json` 的 `page_schema.first_screen`；app.js 不留第二份，L16）。每塊＝塊名（滑過看它問什麼）＋一句讀法
 * （v2 敘事的格、既有元件；都沒有就照印合約宣告的「還沒寫／還沒做」）＋這一塊的圖＋一個展開（給人讀的論證與數字）。
 * `panel` 是 null＝這一檔沒有短評：敘事的格印「還沒寫」，元件與圖照常。短評有、但沒帶齊合約放的每一格（舊格式）：
 * 每一格先照印在最前面，不猜它屬於哪一塊、也不丟（INV-3）。`.meta.json` 是舊的（沒有合約）——回 null。 */
function schemaFirstScreen(payload, view, panel) {
  const schema = VOCAB && VOCAB.page_schema;
  const screen = schema && schema.first_screen;
  if (!screen || !Array.isArray(screen.sections) || !screen.sections.length) return null;
  const lines = panel ? lineMap(panel) : {};
  const readings = screen.readings || {};
  const slots = [];
  Object.keys(readings).forEach((key) => (readings[key].slots || []).forEach((slot) => slots.push(slot)));
  const blocks = {};
  (schema.blocks || []).forEach((block) => { blocks[block.key] = block; });
  const box = el('div', 'schema-screen');
  if (panel && !slots.every((slot) => lines['brief:' + slot])) {
    const story = el('div', 'story');
    (panel.lines || []).filter((row) => row.key.indexOf('brief:') === 0).forEach((row) => story.appendChild(storyRow(row)));
    box.appendChild(story);
  }
  screen.sections.forEach((section) => {
    const sec = el('div', 'ss-section ss-' + section.key);
    sec.appendChild(el('div', 'ss-section-title', section.title));
    (section.blocks || []).forEach((key) => {
      const block = blocks[key] || { key, title: key, question: '' };
      sec.appendChild(schemaBlock(payload, view, lines, block, readings[key] || {}));
    });
    box.appendChild(sec);
  });
  return box;
}

/** 一塊：讀法（短評的格依序、再放既有元件）；都沒有就印合約的 pending、或「還沒寫」（沒有敘事的頁）。
 *  接著是這一塊的圖，最後一個展開（`blockDetail`）。不改任何一格、不加字。 */
function schemaBlock(payload, view, lines, block, reading) {
  const node = el('div', 'fq ss-block');
  node.id = 'blk-' + block.key;
  const head = el('h3', 'fq-title', block.title);
  if (block.question) head.title = block.question;
  node.appendChild(head);
  const story = el('div', 'story');
  (reading.slots || []).forEach((slot) => { if (lines['brief:' + slot]) story.appendChild(storyRow(lines['brief:' + slot])); });
  if (story.childNodes.length) {
    node.appendChild(story);
  } else if (reading.pending) {
    // 讀法句還沒有：照印合約的缺席句（有元件也印——B3 有營收、讀法句還沒寫）
    node.appendChild(el('div', 'row-reason ss-pending', reading.pending));
  } else if ((reading.slots || []).length && !(reading.parts || []).length) {
    node.appendChild(el('div', 'row-reason ss-pending', '還沒寫（這一檔還沒有研究寫的敘事）'));
  } else if (!(reading.parts || []).length) {
    node.appendChild(el('div', 'row-reason ss-pending', '還沒寫'));
  }
  (reading.parts || []).forEach((part) => questionPart(view, part).forEach((n) => node.appendChild(n)));
  blockVisuals(payload, view, block.key).forEach((n) => node.appendChild(n));
  const detail = blockDetail(payload, view, block.key);
  if (detail) node.appendChild(detail);
  return node;
}

/** 塊底下的展開（2026-10-08 使用者：「給我看的留，給機器看的拿掉」）：這一塊給人讀的論證與要核對的數字。
 *  原本散在頁尾四張卡與稽核區的內容搬進對應的塊；每塊最多一個展開、展開裡不再套展開（2026-09-08「太多展開」）。
 *  沒有內容就不放。「數字與出處」掛 id `tq-<題>`——首屏「會死嗎／已定價嗎／出現在數字裡了嗎」點了打開它。 */
function blockDetail(payload, view, key) {
  if (key === 'B2') return chainDetail(payload, view);
  if (key === 'B4') return seatsDetail(payload, view);
  if (key === 'B6') return numbersDrill(view, 'priced_in', () => [pricedInPlain(), marketMultiples(view)]);
  if (key === 'B3') return numbersDrill(view, 'in_numbers', () => mixDetail(payload));
  if (key === 'B8') return downsideDetail(view);
  if (key === 'B9') return numbersDrill(view, 'will_it_die', () => [wipeoutUnlitRule(view)]);
  if (key === 'B11') return timelineDetail(view);
  return null;
}

/** 財務三題某一題的「數字與出處」（原稽核區那一題；敘事那一句引用的數字在這裡核對得到——AGENTS）。 */
function numbersDrill(view, question, extras) {
  const rows = tqNumbers(view, question);
  if (!rows) return null;
  const node = drill('數字與出處', () => {
    const box = el('div', 'block-detail');
    extras().filter(Boolean).forEach((n) => box.appendChild(n));
    box.appendChild(rows);
    return box;
  });
  node.id = 'tq-' + question;
  return node;
}

/** 「怎麼被定價」的兩個本益比與分析師家數（schema B6「本益比兩個年度」）：照抄 fundamental 面板的市場觀測，不算。 */
function marketMultiples(view) {
  const lines = view.fundamental ? lineMap(view.fundamental) : {};
  const bits = [];
  const trailing = lines.trailing_pe && lines.trailing_pe.datum;
  const forward = lines.forward_pe && lines.forward_pe.datum;
  const count = lines.analyst_count && lines.analyst_count.datum;
  if (trailing && typeof trailing.value === 'number') bits.push(`近四季本益比 ${fmtNumber(trailing.value, 1)} 倍`);
  if (forward && typeof forward.value === 'number') bits.push(`用明年度共識 EPS 算 ${fmtNumber(forward.value, 1)} 倍`);
  if (count && typeof count.value === 'number') bits.push(`追蹤的分析師 ${count.value} 位`);
  return bits.length ? el('div', 'row-reason', `市場的數字（別人的，只當脈絡）：${bits.join('｜')}`) : null;
}

/** 灰燈的規則一句（wipeout 面板給的；灰＝這一項沒量到，不是綠）。 */
function wipeoutUnlitRule(view) {
  const rule = view.wipeout && view.wipeout.context && view.wipeout.context.unlit_rule;
  return rule ? el('div', 'row-reason', rule) : null;
}

/** 「需求傳導」的展開：這條鏈怎麼走（圖的敘述＋圖裡 claim 的引文，照抄原論證卡的第一段），以及錨與吃到多少的出處——
 *  走到哪個錨、哪天起每一家都申報了、哪幾家由年初累計差分推算、它是代理、換匯用哪一季的季均價。2026-10-08 使用者：
 *  圖下那一坨小字不用——圖只留 Y 軸與量，這些照抄 materialize 的 `demand_anchor`／`capture`，放這裡給要查的時候看。 */
function chainDetail(payload, view) {
  const line = view.argument ? lineMap(view.argument)['argument:chain'] : null;
  const demand = payload.demand_anchor || {};
  const cap = payload.capture || {};
  const notes = [];
  const anchors = demand.anchors || [];
  if (anchors.length) {
    notes.push('它走到的需求錨：' + anchors.map((a) => `${a.name || a.node}`
      + (a.basis === 'company' ? '（退回公司層才走到）' : '')).join('、'));
  }
  (demand.series || []).forEach((s) => {
    const pts = s.points || [];
    if (!pts.length) return;
    const last = pts[pts.length - 1];
    notes.push(`${s.label}：最新一期 ${last.period}，${last.known_on} 起${s.aggregation === 'single' ? '申報' : '每一家都申報了'}`
      + ((last.derived || []).length && s.aggregation !== 'single' ? `（${last.derived.join('、')} 由年初累計差分推算）` : '')
      + `。${s.proxy || ''}`);
  });
  const cpts = cap.points || [];
  if (cpts.length) {
    const last = cpts[cpts.length - 1];
    notes.push(`吃到多少：營收用${cap.revenue_source || '—'}`
      + (last.per_usd ? `；換美元用季均價（FRED H.10，${last.period} 一美元 ${fmtNumber(last.per_usd, 2)} ${CURRENCY_WORD[last.currency] || last.currency}）` : '')
      + `；${last.known_on} 起營收、錨、匯率都齊。往上＝吃到的比例變大。`);
  }
  // 路徑上各層（S3c）：有宣告代表公司的層，逐家印用哪一種營收、為什麼代表、最新一季誰沒進來（照抄 materialize）
  const hops = (payload.path_layers || {}).hops || {};
  Object.keys(hops).forEach((node) => {
    const h = hops[node];
    (h.representatives || []).forEach((r) => {
      notes.push(`${h.name}｜代表公司 ${r.name}（${r.scope_label}${r.segment ? '：' + r.segment : ''}）：${r.why}`);
    });
    const latest = h.latest || {};
    (latest.missing || []).forEach((m) => notes.push(`${h.name}｜${latest.period} 沒算進來：${m.name || m.company} ${m.reason}`));
    if (h.declaration) {
      notes.push(`${h.name}｜代表公司宣告於 ${h.declaration.declared_on}，重看日 ${h.declaration.expires}`
        + (h.declaration.overdue ? '（已過重看日）' : ''));
    }
  });
  if (!line && !notes.length) return null;
  return drill('細節：這條鏈怎麼走、錨、吃到多少與各層代表公司的出處', () => {
    const box = el('div', 'block-detail');
    if (line) box.appendChild(argumentSection(line));
    notes.forEach((text) => box.appendChild(el('div', 'row-reason', text)));
    return box;
  });
}

/** 路徑上各層（B2，個股頁 S3c）：錢從需求錨往下走到它坐的層，每一節一行——年增（層＝研究宣告的代表公司加總、公司＝它自己）
 *  或產生端宣告的缺席原因。押的格那幾條路徑先列、其餘收在一個展開；順序照 materialize（索引不是名次）。只照抄、不算。 */
function pathFigure(payload) {
  const pl = payload.path_layers;
  if (!pl) return null;
  const box = el('div', 'path-layers');
  box.appendChild(el('div', 'chart-axis-title', '路徑上各層：錢從需求錨往下，經過的每一層有沒有在長'));
  if (pl.absence) {
    box.appendChild(el('div', 'row-reason ss-pending', pl.absence.reason || absenceLabel(pl.absence.kind) || '沒有'));
    return box;
  }
  const hops = pl.hops || {};
  const hopRow = (node) => {
    const h = hops[node] || { name: node, kind_label: '' };
    const row = el('div', 'path-hop');
    row.appendChild(el('span', 'path-kind', h.kind_label || ''));
    row.appendChild(el('span', 'path-name', h.name || node));
    let text = '';
    if (h.kind === 'anchor') {
      text = (h.series || []).filter((s) => typeof s.yoy === 'number')
        .map((s) => `${s.label} ${fmtPercent(s.yoy)}（${s.period}）`).join('；') || ((h.absence || {}).reason || '');
    } else if (h.latest) {
      text = `年增 ${fmtPercent(h.latest.yoy)}（${h.latest.period}${h.latest.coverage ? `，代表公司 ${h.latest.coverage} 家` : ''}）`
        + (h.kind === 'company' ? `｜${h.proxy || ''}` : '') + (h.includes_page_company ? '｜含本公司' : '');
    } else {
      text = (h.absence || {}).reason || '沒有';
    }
    row.appendChild(el('span', h.latest || h.kind === 'anchor' ? 'path-value' : 'path-value path-absent', text));
    return row;
  };
  const pathBox = (p) => {
    const one = el('div', 'path-one');
    p.nodes.forEach((node) => one.appendChild(hopRow(node)));
    return one;
  };
  const paths = pl.paths || [];
  const shown = paths.filter((p) => p.focus);
  const head = shown.length ? shown : paths.slice(0, 1);
  head.forEach((p) => box.appendChild(pathBox(p)));
  const rest = paths.filter((p) => head.indexOf(p) < 0);
  if (rest.length) box.appendChild(drill(`其他 ${rest.length} 條路徑`, () => {
    const more = el('div', 'block-detail');
    rest.forEach((p) => more.appendChild(pathBox(p)));
    return more;
  }));
  return box;
}

/** 營收從哪來（B3，個股頁 S3d）：分部／產品線占比——一塊一列（名字｜長度＝占比的條｜百分比，前一次的占比括號裡），
 *  客戶集中度與 backlog 先印第一句（全文與出處在這一塊的「數字與出處」）。全部照抄 materialize 的 `revenue_mix`：
 *  分部依占比由大到小是 materialize 排好的呈現順序，前端不排、不算（條的長度只是座標換算）。 */
function mixFigures(payload) {
  const mix = payload.revenue_mix;
  if (!mix) return [];
  if (mix.unread) return [el('div', 'row-reason ss-pending', `營收結構：${mix.unread.reason}`)];
  const out = [];
  // 人工記的分部／產品線占比，加上台股年報機械抽的地區別（同一個形狀，各自一塊；note＝年報說依什麼分地區）
  (mix.shares || []).concat(mix.regions ? [mix.regions] : []).forEach((s) => {
    const latest = (s.points || [])[(s.points || []).length - 1];
    if (!latest) return;
    const box = el('div', 'mix-box');
    const prev = (s.points || []).length > 1 ? s.points[s.points.length - 2] : null;
    box.appendChild(el('div', 'chart-axis-title',
      `${s.label}營收占比（${latest.period || latest.as_of}${prev ? `；括號是前一次 ${prev.period || prev.as_of}` : ''}）`));
    if (s.note) box.appendChild(el('div', 'row-reason', s.note));
    (latest.parts || []).forEach((p) => {
      const row = el('div', 'mix-row');
      row.appendChild(el('span', 'mix-name', p.name));
      const track = el('span', 'mix-track');
      const bar = el('span', 'mix-bar');
      bar.style.width = `${Math.max(0, Math.min(100, p.share * 100))}%`;
      track.appendChild(bar);
      row.appendChild(track);
      row.appendChild(el('span', 'mix-pct', fmtRatioPct(p.share, 1)
        + (typeof p.prev_share === 'number' ? `（${fmtRatioPct(p.prev_share, 1)}）` : '')));
      box.appendChild(row);
    });
    out.push(box);
  });
  if (mix.absences && mix.absences.shares) out.push(el('div', 'row-reason ss-pending', `營收占比：${mix.absences.shares.reason}`));
  if (mix.absences && mix.absences.regions) out.push(el('div', 'row-reason ss-pending', `地區營收：${mix.absences.regions.reason}`));
  [['customers', '客戶集中度'], ['backlog', 'backlog 與長約']].forEach(([key, label]) => {
    const item = mix[key];
    if (item) out.push(el('div', 'row-reason', `${label}（${item.as_of}）：${item.headline}`));
    else if (mix.absences && mix.absences[key]) out.push(el('div', 'row-reason ss-pending', `${label}：${mix.absences[key].reason}`));
  });
  (mix.conflicts || []).forEach((c) => out.push(el('div', 'row-reason',
    `${c.label || c.field}（${c.as_of}）有 ${(c.ids || []).length} 筆同時生效的紀錄`
    + (c.declared_parallel ? '（登記過的刻意並存）' : '') + '——不挑一個，這一筆不印')));
  return out;
}

/** 押的那一塊占營收多少（B3，2026-10-14）：敘事押的層 × 層代表公司宣告 × 分部占比——一層一句；對不上照印哪一段沒有。
 *  全部照抄 materialize 的 `bet_share`（占比是 Engine C 觀測、不是這裡算的）。 */
function betShareLines(payload) {
  const bet = payload.bet_share;
  if (!bet) return [];
  if (bet.absence) return [el('div', 'row-reason ss-pending', `押的那一塊：${bet.absence.reason}`)];
  return (bet.items || []).map((item) => {
    if (item.value === 'share') {
      const prev = typeof item.prev_share === 'number' ? `；前一次 ${fmtRatioPct(item.prev_share, 1)}` : '';
      const newer = item.newer_conflict ? `——較新的 ${item.newer_conflict} 那一次有多筆同時生效的紀錄、不挑一個，這裡是前一次` : '';
      return el('div', 'row-reason', `押的那一塊：「${item.node_name}」由研究宣告用「${item.segment}」分部代表——`
        + `占營收 ${fmtRatioPct(item.share, 1)}（${item.period}${prev}）${newer}`);
    }
    if (item.value === 'whole_company') {
      return el('div', 'row-reason', `押的那一塊：「${item.node_name}」由研究宣告用全公司營收代表——整家公司就是押的那一塊`);
    }
    return el('div', 'row-reason ss-pending', `押的那一塊：${item.reason}`);
  });
}

/** 事件之後跟組比（B5，個股頁 S3e）：研究說過會改變信心的事（這一檔名下醒過的等待、已過的確定檢核點），每件一列——日期、
 *  哪一種、說什麼、事件前最後一個收盤，與每一組 1／5／20 個交易日的相對漲跌（本檔 − 組員平均）；還沒滿 n 日寫「還沒滿」。
 *  全部照抄 materialize 的 `event_reaction`（報酬是那邊算好的，這裡只換成百分比字樣；不排序、不上色）。 */
function eventReactionLines(payload) {
  const er = payload.event_reaction;
  if (!er) return [];
  const out = [];
  const counts = er.counts || {};
  // 不算的那幾種照數寫（判定之前 AI 標旗不算事件；估計日期的檢核點差一兩天就會算到別的事上）
  const skipped = [
    counts.flagged_unjudged ? `${counts.flagged_unjudged} 件 AI 標旗、還沒判定是否觸及` : null,
    counts.judged_not_touched ? `${counts.judged_not_touched} 件判定沒觸及` : null,
    counts.other_wakes ? `${counts.other_wakes} 件其他醒法` : null,
    counts.estimated_checkpoints ? `${counts.estimated_checkpoints} 個已過的檢核點只有估計日期` : null,
  ].filter(Boolean);
  const estimated = skipped.length
    ? el('div', 'row-reason ss-pending', `不算事件的：${skipped.join('、')}（判定觸及、日期確定才算）`)
    : null;
  if (er.absence) {
    out.push(el('div', 'row-reason ss-pending', `事件之後跟組比：${er.absence.reason}`));
    if (estimated) out.push(estimated);
    return out;
  }
  (er.events || []).forEach((e) => {
    const price = e.price_before
      ? `｜事件前收盤 ${fmtNumber(e.price_before.close, 2)}${e.price_before.unit ? ' ' + e.price_before.unit : ''}（${e.price_before.date}）`
      : '';
    const late = e.date_basis === 'woken_at' ? '（這是系統發現它醒的日子，事件可能更早）'
      : (e.date_basis === 'watch_date' ? '（研究定的日子，事件本身可能早幾天）' : '');
    const parts = (e.reactions || []).map((r) => {
      if (r.absence) return `相對「${r.theme}」組：${r.absence}`;
      const windows = (r.windows || []).map((w) => (w.pending ? `${w.n} 日 還沒滿`
        : (w.absence ? `${w.n} 日 ${w.absence}` : `${w.n} 日 ${signedPct(w.relative)}`)));
      return `相對「${r.theme}」組：${windows.join('、')}`;
    });
    if (e.reaction_absence) parts.push(`相對同組：${e.reaction_absence.reason}`);
    out.push(el('div', 'row-reason', `${e.date} ${e.kind_label}${late}：${e.label || '—'}${price}`
      + (parts.length ? `｜${parts.join('；')}` : '')));
  });
  if ((er.total || 0) > (er.events || []).length) {
    out.push(el('div', 'row-reason', `（另有 ${er.total - er.events.length} 件較早的事，沒列）`));
  }
  if (estimated) out.push(estimated);
  return out;
}

/** B3「數字與出處」裡的營收結構細節：客戶集中度與 backlog 的全文、每一次占比觀測的出處與沒畫的欄位、押的那一塊的宣告理由（照抄）。 */
function mixDetail(payload) {
  const mix = payload.revenue_mix || {};
  const out = [];
  ((payload.bet_share || {}).items || []).filter((item) => item.value).forEach((item) => out.push(el('div', 'row-reason',
    `押的那一塊「${item.node_name}」的代表公司宣告：${item.why}${item.source_ref ? `｜占比出處：${item.source_ref}` : ''}`)));
  [['customers', '客戶集中度'], ['backlog', 'backlog 與長約']].forEach(([key, label]) => {
    const item = mix[key];
    if (item) out.push(el('div', 'row-reason', `${label}（${item.as_of}）全文：${item.text}｜出處：${item.source_ref || '—'}`));
  });
  (mix.shares || []).concat(mix.regions ? [mix.regions] : []).forEach((s) => (s.points || []).forEach((p) => out.push(el('div', 'row-reason',
    `${s.label}占比 ${p.period || p.as_of}：出處 ${p.source_ref || '—'}`
    + ((p.ignored || []).length ? `｜不是占比、沒畫的欄位：${p.ignored.join('、')}` : '')))));
  return out;
}

/** 「技術鏈」的展開：它坐的每一層現在讀成什麼（讀圖面板照抄）。節點印名字——層說明的標題、圖上的名字，都沒有才印 ID
 *  （ID 放 title）；哪幾層有層說明連到閱讀頁。完整引文與反證在圖頁那一層（點層名）。 */
function seatsDetail(payload, view) {
  const panel = view.readings;
  if (!panel) return null;
  const ctx = panel.context || {};
  const titles = {};
  (ctx.layer_notes || []).forEach((n) => { titles[n.node] = n.title; });
  const names = payload.node_names || {};
  const rows = (panel.lines || []).filter((line) => line.role === 'reading');
  const links = layerNoteLinks(ctx);
  if (!rows.length && !links) return null;
  return drill(`它坐的層：現在讀成什麼（${rows.length} 層有讀圖）`, () => {
    const box = el('div', 'block-detail');
    if (!rows.length) box.appendChild(el('p', 'note', panel.reason || '還沒有讀圖'));
    const list = el('ul', 'weak');
    rows.forEach((line) => {
      const m = /^reading:(.+):(layer|socket)$/.exec(line.key) || [];
      const node = m[1] || line.key;
      const li = el('li');
      const link = el('a', null, `${titles[node] || names[node] || node}（${m[2] === 'socket' ? '插槽' : '層'}）`);
      link.href = '#/graph/' + encodeURIComponent(node);       // 2026-10-28：讀圖頁併進圖頁，連到那一層
      link.title = node;
      li.appendChild(link);
      const d = line.datum || {};
      li.appendChild(el('span', 'rule', typeof d.value === 'string' && d.value ? d.value
        : (absenceLabel(d.absence_kind) || d.reason || '—')));
      list.appendChild(li);
    });
    if (rows.length) box.appendChild(list);
    const unread = (ctx.seats || []).length - rows.length;
    if (unread > 0) box.appendChild(el('p', 'note', `它坐的另外 ${unread} 個節點還沒有讀圖。`));
    if (links) box.appendChild(links);
    const more = el('a', null, '每一層的引文與反證在「圖」頁 →');
    more.href = '#/graph';
    box.appendChild(more);
    return box;
  });
}

/** 「錯了怎麼知道」的展開：每條反證——誰在盯、多久看一次、觸發後 48 小時做什麼（照抄 downside 面板，與心跳段 2 同一套；
 *  watch 編號放 title，查得到但不擋在句子裡）。研究時寫的風險原文附在後面。 */
function downsideDetail(view) {
  const panel = view.downside;
  const rows = panel ? (panel.lines || []).filter((line) => line.role === 'downside') : [];
  const risks = view.argument ? lineMap(view.argument)['argument:risks'] : null;
  const riskText = risks && risks.datum && typeof risks.datum.value === 'string' && risks.datum.value;
  if (!panel && !riskText) return null;
  return drill('每條反證：多久看一次、觸發後做什麼', () => {
    const box = el('div', 'block-detail');
    if (panel && !rows.length) {
      // 「名下還沒有反證」與「這次沒讀到反證的來源」下一步不同（3.7 R1）：標題跟著產生端宣告的分型走（首屏同一個函式）。
      const head = el('div', 'attention-head', downsideAbsenceHead(panel) + '　');
      const badge = absenceBadge(panel.absence_kind);
      if (badge) head.appendChild(badge);
      box.appendChild(head);
      if (panel.reason) box.appendChild(el('div', 'attention-body', panel.reason));
    } else if (rows.length) {
      const counts = (panel.context || {}).counts || {};
      box.appendChild(el('div', 'rule', `在盯 ${counts.active || 0}｜醒來待判 ${counts.fired || 0}｜`
        + `觸及待處置 ${counts.touched || 0}｜到期待複查 ${counts.expired || 0}｜未盯 ${counts.unwatched || 0}`));
      const list = el('ul', 'weak');
      rows.forEach((line) => {
        const r = line.datum.value || {};
        const li = el('li', null, r.condition || '');
        if (r.watch_id) li.title = 'watch ' + r.watch_id;
        const bits = [r.source_label || line.display_label, (r.state_label || '—') + (r.until ? `（到期 ${r.until}）` : '')];
        if (r.check_frequency) bits.push('多久看一次：' + r.check_frequency);
        if (r.action_48h) bits.push('觸發後要做什麼：' + r.action_48h);
        li.appendChild(el('span', 'rule', bits.join('｜')));
        // 同一筆 watch 只印一列；敘事也以來源鍵連到它時，把另一個來源寫在這裡（不另起一列、不多算一次）。
        if ((r.also || []).length) li.appendChild(el('span', 'rule', '也連到這一條：' + r.also.map((a) => a.source_label).join('、')));
        list.appendChild(li);
      });
      box.appendChild(list);
    }
    ((panel && panel.notes) || []).forEach((text) => box.appendChild(el('p', 'note', text)));
    if (riskText) box.appendChild(argumentSection(risks));
    return box;
  });
}

/** 「接下來看什麼」的展開：研究時寫的時間表（原論證卡第三段）＋催化劑的日期（description／expected_at——3.7 覆核：
 *  原本照抄 label／due，畫面只剩內部狀態字 unlinked）。 */
function timelineDetail(view) {
  const line = view.argument ? lineMap(view.argument)['argument:timeline'] : null;
  const hasText = Boolean(line && line.datum && typeof line.datum.value === 'string' && line.datum.value);
  const catalysts = (view.research && view.research.catalysts) || [];
  if (!hasText && !catalysts.length) return null;
  return drill('時間表', () => {
    const box = el('div', 'block-detail');
    if (hasText) box.appendChild(argumentSection(line));
    if (catalysts.length) {
      box.appendChild(el('div', 'group-title', '什麼時候會知道'));
      box.appendChild(listOf(catalysts.map((c) => [c.expected_at || '日期未定', c.description || c.label,
        c.date_confidence].filter(Boolean).join('｜'))));
    }
    return box;
  });
}

/** 首屏塊裡的既有元件（字全由 materialize 端給）。認不得的元件名照印出來，不靜默略過（INV-3）。 */
function questionPart(view, part) {
  const lines = view.candidate ? lineMap(view.candidate) : {};
  const state = lines['candidate:state'] && lines['candidate:state'].datum;
  const row = state && state.value;
  if (part === 'priced_in' || part === 'in_numbers' || part === 'will_it_die') return wordsBlock(view, [part]);
  if (part === 'wipeout') return [lampsBlock(view, true)].filter(Boolean);
  if (part === 'disproof') return disproofBrief(view);
  if (part === 'confirm') return confirmLines(row);
  if (part === 'shared_bet') return sharedBetLines(row);
  return [el('div', 'row-reason', `（這一題的元件 ${part} 這版畫面還不認得）`)];
}

/* 候選狀態＋財務三題三個字（Phase 3 Step 3.7）。**全部照抄** candidate 面板——字由 materialize 端給
   （與候選板同一個推導），本畫面不判、不算。沒有敘事也沒有持有＝不上板，三個字照印（會死嗎看燈，兩題「未答」）。
   2026-09-30 使用者回饋（「這三個字是要我去候選板看詳細嗎？」）：三個字可以點，點了打開同一頁那一題的數字；
   2026-10-08 起數字住在那一題的那一塊（會不會死／怎麼被定價／押對了夠大嗎）的「數字與出處」裡。 */
const CANDIDATE_WORDS = [['candidate:will_it_die', '會死嗎', 'will_it_die'], ['candidate:priced_in', '已定價嗎', 'priced_in'],
  ['candidate:in_numbers', '出現在數字裡了嗎', 'in_numbers']];

/** 打開同一頁那一題的「數字與出處」、捲過去（`numbersDrill` 掛了 id `tq-<題>`）。不在就不動。 */
function jumpToNumbers(question) {
  const box = document.getElementById('tq-' + question);
  if (!box) return;
  box.open = true;
  box.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/** 候選狀態在等的那一筆 watch：哪天醒、最晚哪天到期重問。watch id 放 title（查得到，但不擋在句子裡）。 */
function candidateWatchLine(watch) {
  const bits = [];
  if (watch.until) bits.push(`${watch.until} 那天醒來重看`);
  if (watch.expires) bits.push(`最晚 ${watch.expires} 到期重問（到期是重問，不是丟掉）`);
  if (watch.status && watch.status !== 'active') bits.push(`這筆等待目前是「${watch.status}」`);
  const line = el('div', 'row-reason', '在等：' + (bits.join('；') || '沒寫醒來與到期日'));
  line.title = 'watch ' + watch.watch_id;
  return line;
}

/** 敘事的 confirm 條件（Phase 7 Step 7.0d）：每條一句，**整句由 materialize 端組好**（`engine_b/disproof.py::confirm_line`），
 * 這裡照印不組字。觸及＝「結構確認了」的提醒，不是買進訊號，也不改候選狀態；沒有 confirm 條件就不印。候選板與個股頁共用這一個。 */
function confirmLines(row, tag) {
  return ((row && row.confirm) || []).map((c) => {
    const line = el(tag || 'div', c.state === 'touched' ? 'warn' : 'row-reason', c.line || c.condition);
    if (c.watch_id) line.title = 'watch ' + c.watch_id;
    return line;
  });
}

/** 歸零燈（B9 會不會死）：燈名＋顏色＋一句白話理由，照抄 wipeout 面板。2026-10-08 使用者：「這四個燈號到底代表什麼，
 * 稀釋是啥、going concern 是什麼」——燈名改用 page_schema 的 B9 白話問句（錢夠不夠／怕不怕還債／會不會一直增資／
 * 會計師有沒有警告；名字只住合約那一份，L16），綠燈也寫理由（「沒事」是怎麼沒事），四盞燈上面印一句白話（`plain_wipeout`）。
 * `withGreen`＝綠燈也列（十三塊版面逐盞列；讀不到合約的舊 server 只列不是綠的）。灰＝沒量到，不是沒事。 */
function lampsBlock(view, withGreen) {
  const panel = view.wipeout;
  if (!panel) return null;
  const names = lampNames();
  const items = [];
  (panel.lines || []).filter((line) => line.role === 'wipeout').forEach((line) => {
    const d = line.datum || {};
    const value = d.value || {};
    if (value.colour === 'green' && !withGreen) return;
    const colour = WIPEOUT_COLOURS[value.colour];
    const name = names[line.key] || plainLine(line.key, line.display_label).replace(/^歸零旗標：/, '');
    const why = value.reason || d.reason || absenceLabel(d.absence_kind) || '';
    items.push(`${colour ? colour.mark : '⬜'} ${name}${colour ? '' : '（沒量到，不是沒事）'}${why ? '：' + why : ''}`);
  });
  if (!items.length) return null;
  const box = el('div', 'lamp-notes');
  const plain = (VOCAB && VOCAB.plain_wipeout) || '';
  if (plain && withGreen) box.appendChild(el('div', 'row-reason lamp-plain', plain));
  items.forEach((text) => box.appendChild(el('div', 'lamp-row', text)));
  return box;
}

/** 燈名：page_schema 的 B9 元素名（`wipeout/<key>` 那一條 line 對到的元素；合約只有一份，前端不另寫）。 */
function lampNames() {
  const out = {};
  ((VOCAB && VOCAB.page_schema && VOCAB.page_schema.elements) || []).forEach((element) => {
    (element.lines || []).forEach((spec) => {
      if (String(spec).indexOf('wipeout/') === 0) out[String(spec).slice('wipeout/'.length)] = element.label;
    });
  });
  return out;
}

/** 財務三題的三個字（可點：打開同一頁那一題的「數字與出處」）。`questions`＝印哪幾題（十三塊版面分到各自那一塊；
 * 讀不到合約的舊 server 三個一起）。「已定價嗎」的白話 2026-10-08 起只放在那一題的「數字與出處」裡（首屏只留字）。 */
function wordsBlock(view, questions) {
  const panel = view.candidate;
  if (!panel || !(panel.lines || []).length) return [];
  const lines = lineMap(panel);
  const words = el('div', 'candidate-words');
  CANDIDATE_WORDS.filter((entry) => questions.indexOf(entry[2]) >= 0).forEach(([key, label, question]) => {
    const d = lines[key] && lines[key].datum;
    const word = el('button', 'word word-link', `${label}　${d && d.value ? d.value : '—'} ↓`);
    word.type = 'button';
    word.title = '打開這一題的數字與出處';
    word.addEventListener('click', () => jumpToNumbers(question));
    words.appendChild(word);
  });
  return [words];
}

/** ③ 每條反證與盯它的 watch 狀態——照抄 downside 面板（論證層那張卡同一份；這裡只印條件與狀態，細節在那張卡）。 */
function disproofBrief(view) {
  const panel = view.downside;
  if (!panel) return [];
  const lines = (panel.lines || []).filter((line) => line.role === 'downside');
  if (!lines.length) {
    return [el('div', 'row-reason', downsideAbsenceHead(panel) + (panel.reason ? '：' + panel.reason : ''))];
  }
  return lines.map((line) => {
    const r = line.datum.value || {};
    return el('div', 'row-reason', `反證：${r.condition || ''}｜${r.state_label || '—'}${r.until ? `（到期 ${r.until}）` : ''}`);
  });
}

/** downside 沒有任何一列時的標題：「名下還沒有反證」與「這次沒讀到反證的來源」下一步不同（3.7 R1），跟著產生端宣告的分型走。 */
function downsideAbsenceHead(panel) {
  if (panel.absence_kind === 'not_yet_recorded') return '名下還沒有反證';
  return panel.absence_kind === 'point_in_time_unavailable' ? '回看的那天不推反證與 watch' : '這次沒讀到反證的來源';
}

/** ⑤ 那一題的元件：和持有的 alpha 檔共用的需求錨與層（Phase 7 Step 7.0e）。**整句由 materialize 端組好**
 * （`alpha/providers/candidates.py::shared_bet`），這裡照印——不打分、不排序（依 ticker 字母）、不加權。 */
function sharedBetLines(row, tag) {
  const bet = row && row.shared_bet;
  if (!bet) return [];
  return (bet.lines || []).map((text) => el(tag || 'div', 'row-reason', text));
}

/** 首頁分組的中文（`alpha.candidates.LIST_GROUP_LABELS` 經 `.meta.json` 的那一份；讀不到回 null，不另寫一份）。 */
function listGroupLabel(key) {
  const hit = ((VOCAB && VOCAB.list_groups) || []).find((g) => g.key === key);
  return hit ? hit.label : null;
}

function candidateLine(view, inQuestions) {
  const panel = view.candidate;
  if (!panel) return null;      // 3.7 之前 materialize 的 artifact 沒有這個面板
  const lines = lineMap(panel);
  const node = el('div', 'candidate-line');
  const head = el('div', 'candidate-state');
  head.appendChild(document.createTextNode('候選狀態：'));
  const state = lines['candidate:state'] && lines['candidate:state'].datum;
  const row = state && state.value;
  if (row) {
    head.appendChild(el('strong', null, row.derived_label || row.derived || '—'));
    if (row.declared && row.declared !== row.derived) {
      head.appendChild(el('span', 'dim', `（敘事宣告：${row.declared_label || row.declared}）`));
    }
    if (typeof row.stall_days === 'number') head.appendChild(el('span', 'dim', `　滯留 ${row.stall_days} 天`));
    if (row.sheet_verified === false) head.appendChild(el('span', 'dim', '　持股未驗'));
  } else {
    // 非邊緣＝規定不寫敘事，不是「還沒做」（2026-10-28 使用者）：產生端在 context 宣告 edge_state，字取首頁分組字彙那一份。
    const notEdge = (panel.context || {}).edge_state === 'not_edge' && listGroupLabel('not_edge_no_narrative');
    const badge = notEdge ? el('span', 'badge', notEdge) : absenceBadge(panel.absence_kind);
    if (badge) head.appendChild(badge);
    if (panel.reason) head.appendChild(el('span', 'dim', '　' + panel.reason));
  }
  node.appendChild(head);
  if (row && row.reason) node.appendChild(el('div', 'row-reason', '理由：' + row.reason));
  if (row && row.watch) node.appendChild(candidateWatchLine(row.watch));
  // 五題版面：confirm 條件、三個字與白話、燈已放在③②④底下（Phase 7 Step 7.0e），這一行只留候選狀態本身。
  if (!inQuestions) {
    confirmLines(row).forEach((line) => node.appendChild(line));
    if ((panel.lines || []).length) {
      wordsBlock(view, CANDIDATE_WORDS.map((entry) => entry[2])).forEach((n) => node.appendChild(n));
      const lamps = lampsBlock(view, false);
      if (lamps) node.appendChild(lamps);
    }
  }
  if (row) {
    (row.preconditions || []).forEach((text) => node.appendChild(el('div', 'row-reason', '前提失效：' + text)));
    (row.rewrite || []).forEach((text) => node.appendChild(el('div', 'row-reason', text)));
    if (row.note) node.appendChild(el('div', 'row-reason', row.note));
  }
  // 「和其他檔並排看」在首頁（2026-10-28 候選板併進首頁），不是這一檔的細節（細節在上面三個字點下去的稽核區）。
  const link = el('a', 'dim', '和其他檔一起看（公司）→');
  link.href = '#/';
  node.appendChild(link);
  return node;
}

/** 「已定價嗎」的白話（Phase 7 Step 7.0c；字串由 materialize 從 contracts 的 PLAIN_PRICED_IN 帶來；沒有就不印，不自己補一份）。 */
function pricedInPlain() {
  const text = (VOCAB && VOCAB.plain_priced_in) || '';
  return text ? el('div', 'row-reason priced-in-plain', text) : null;
}

/** 層／插槽／押在哪一格的白話（字彙由 materialize 從 contracts 的 PLAIN_BET_UNITS 帶來；沒有就不印，不自己補一份）。 */
function unitGlossary() {
  const table = (VOCAB && VOCAB.plain_bet_units) || null;
  if (!table) return null;
  const box = el('div', 'glossary');
  ['layer', 'socket', 'ride'].forEach((key) => { if (table[key]) box.appendChild(el('div', 'rule', table[key])); });
  return box.childNodes.length ? box : null;
}

/* ⚠ **2026-09-23（Phase 0 Step 0b.1）：`priceScale`（那把尺）整個函式退役。**
   它畫的是現價／沒賭對的目標價／賭對的目標價／判斷錯了的目標價／分析師平均，而
   ROADMAP「個股頁」對照表把整把尺列進「拿掉」。走勢圖（`priceCard`）留著——它是脈絡不是訊號。
   接手首屏的是句子、燈、候選狀態與財務三題（Phase 3）。 */

/** 論證的一段（argument 面板的 paragraph：這條鏈怎麼走／風險與認錯條件／時間表）：文字、研究長文、圖裡 claim 的引文，照抄。
 *  2026-10-08 起三段分別住「需求傳導」「錯了怎麼知道」「接下來看什麼」三塊的展開裡（原本是頁尾一張「憑什麼這樣想」卡）。 */
function argumentSection(line) {
  const d = line.datum || {};
  const sec = el('div', 'arg-section');
  if (typeof d.value === 'string' && d.value) {
    sec.appendChild(el('p', 'arg-text', d.value));
  } else {
    sec.appendChild(el('p', 'arg-text muted', '（' + (d.reason || '缺料') + '）'));
  }
  const deps = d.dependencies || {};
  (deps.long_form || []).forEach((item) => {
    const box = el('div', 'arg-long');
    box.appendChild(el('div', 'arg-long-title', item.title || ''));
    box.appendChild(el('div', 'arg-long-text', item.text || ''));
    sec.appendChild(box);
  });
  if ((deps.citations || []).length) {
    const list = el('ul', 'arg-cites');
    deps.citations.forEach((c) => {
      const li = el('li');
      const who = el('span', 'cite-who', `${c.who || '？'}　${c.date || ''}`);
      li.appendChild(who);
      li.appendChild(document.createTextNode('　' + (c.statement || '')));
      if (c.url) {
        const a = el('a', 'cite-link', '原文 ↗');
        a.href = c.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
        if (c.title) a.title = c.title;
        li.appendChild(document.createTextNode(' '));
        li.appendChild(a);
      } else if (c.title) {
        li.title = c.title;
      }
      list.appendChild(li);
    });
    sec.appendChild(el('div', 'arg-long-title', '引文（圖裡的 claim，照抄）'));
    sec.appendChild(list);
  }
  return sec;
}

async function renderDetail(ticker) {
  markNav('stocks', '這一家我們押什麼、憑什麼、什麼會推翻它？');
  let payload;
  try {
    payload = await getJSON(`${API}/stocks/${encodeURIComponent(ticker)}`);
  } catch (err) {
    app.textContent = '';
    const backLink = el('a', 'back', '← 回清單');
    backLink.href = '#/';
    app.appendChild(backLink);
    const box = el('div', 'error');
    const detail = (err.body && err.body.error) || {};
    box.appendChild(el('h2', null, `讀不到 ${ticker} 的判讀`));
    box.appendChild(el('p', null, detail.reason || detail.message || 'request failed'));
    if (detail.remedy) {
      const p = el('p', 'note');
      p.appendChild(document.createTextNode('修法：'));
      p.appendChild(el('code', null, detail.remedy));
      box.appendChild(p);
    }
    if (detail.note) box.appendChild(el('p', 'note', detail.note));
    app.appendChild(box);
    return;
  }

  const view = payload.view;
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';

  const back = el('a', 'back', '← 回清單');
  back.href = '#/';
  app.appendChild(back);

  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.ticker));
  head.appendChild(el('div', 'company', payload.company_label || ''));
  const what = whatLine(payload);
  if (what) head.appendChild(what);
  const sub = headerLine(payload, view);
  if (sub) head.appendChild(sub);
  app.appendChild(head);

  // 2026-10-08 使用者：「舊有的資訊非必要的就拿掉，除非是給我看的；給機器看的不用顯示出來」。
  // 一頁只剩頁首＋十三塊（個股頁 schema v1.0）：①每塊一句讀法 ②塊底下一個展開放這一塊給人讀的論證（這條鏈怎麼走、
  // 坐的層讀成什麼、每條反證、時間表）③要核對的數字與出處也在那一塊的展開裡（財務三題）。原本的「基本數字／憑什麼這樣想／
  // 讀圖／錯了怎麼知道」四張卡的內容搬進對應的塊；「稽核」與「完整細節」兩個大展開、每塊的「這一塊的格」（填得滿表）拿掉——
  // 給查核用的欄位（authority、digest、readiness、填得滿表、原始 JSON）留在 artifact 與 `/api/v1/stocks/<T>`，不必有畫面。
  app.appendChild(briefCard(payload, view));
  window.scrollTo(0, 0);
}

/** 頁首「做什麼」（schema B0；2026-10-08 使用者：「像 COHR 就寫個 CW DFB 雷射，一目了然」）：materialize 組好的句子照印
 *  （`what_it_does`：押的層或插槽，敘事沒宣告時是圖上它供貨或開發的節點；在示意圖的哪一格）。前端不挑、不組。 */
function whatLine(payload) {
  const what = payload.what_it_does;
  if (!what) return null;
  const box = el('div', 'detail-what');
  if (what.line) {
    box.appendChild(el('div', 'detail-what-line', what.line));
    if (what.where_line) box.appendChild(el('div', 'detail-what-where', what.where_line));
  } else {
    box.appendChild(el('div', 'detail-what-where', `做什麼：還不知道——${(what.absence || {}).reason || '沒說為什麼'}`));
  }
  return box;
}

/** 頁首一行：現價與收盤日、這份判讀哪天產生（原「基本數字」那一格搬上來；判讀不在點擊時重算）。 */
function headerLine(payload, view) {
  const head = view.headline ? lineMap(view.headline) : {};
  const price = head.current_price && head.current_price.datum;
  const quoteUnit = price && price.dependencies ? price.dependencies.quote_unit : null;
  const bits = [];
  if (price && typeof price.value === 'number') {
    bits.push(`現在股價 ${fmtQuantity(price.value, quoteUnit) || '—'}${price.as_of ? `（${price.as_of} 收盤）` : ''}`);
  } else if (price) {
    bits.push(`現在股價：沒有（${absenceLabel(price.absence_kind) || price.reason || '沒說為什麼'}）`);
  }
  const generated = payload.freshness && payload.freshness.generated_at;
  if (generated) bits.push(`這份判讀產生於 ${String(generated).slice(0, 10)}`);
  return bits.length ? el('div', 'detail-sub', bits.join('｜')) : null;
}

/* ---------- 共用：導覽、行內強調、表格 ----------
   ⚠ 2026-10-28：「結構表」頁（renderStructureTable 與它專用的欄位函式：soleSourceBadge、edgeCell、subCell、anchorCell、
   hopsText、nodeLabel、RELATION_PLAIN、TABLE_COLUMNS、chainList、TABLE_VOCAB）拿掉——併進「圖」頁（使用者照推薦：11 頁收成 5 頁）。
   去處：「某一層有哪幾家在供貨」→圖頁每層的公司（結構表 supplies_to 那幾列）；「從需求端走到這一層經過哪幾層」→圖頁每層
   「讀法、引文與反證」裡的需求鏈；已知限制→圖頁「解讀前要知道」；搜尋→圖頁搜尋（只藏不排）。逐邊的可替代性、獨家、證據強度、
   合格狀態、離錨幾步是查核欄位：留在 structure_table artifact 與 `python -m query.structure`。 */

/** 標出目前那一頁，並把它回答的問題印在導覽列下面（2026-10-28：每一頁宣告它回答你的哪一個問題；字串只住
 * index.html 的 data-question，這裡照抄）。`question` 只給「借用導覽列上某一頁、但問的是另一件事」的頁（個股頁）。 */
function markNav(name, question) {
  let asked = question || '';
  document.querySelectorAll('.nav a').forEach((link) => {
    const active = link.dataset.view === name;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
    if (link.dataset.question) link.title = link.dataset.question;
    if (active && !asked) asked = link.dataset.question || '';
  });
  const slot = document.getElementById('page-question');
  if (slot) slot.textContent = asked ? `這一頁回答：${asked}` : '';
}

/** authority 的固定文字帶著 markdown 強調（**x**、`x`）。這裡只把它們變成 <strong>／<code>，
    不改一個字——用 DOM 節點組，不用 innerHTML。 */
function mdInline(text) {
  const frag = document.createDocumentFragment();
  const source = String(text || '');
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let match;
  while ((match = re.exec(source)) !== null) {
    if (match.index > last) frag.appendChild(document.createTextNode(source.slice(last, match.index)));
    const token = match[0];
    if (token.startsWith('**')) frag.appendChild(el('strong', null, token.slice(2, token.length - 2)));
    else frag.appendChild(el('code', null, token.slice(1, token.length - 1)));
    last = match.index + token.length;
  }
  if (last < source.length) frag.appendChild(document.createTextNode(source.slice(last)));
  return frag;
}

function mdParagraph(text, className) {
  const p = el('p', className || 'note');
  p.appendChild(mdInline(text));
  return p;
}

function th(text) { return el('th', null, text); }

function companyCell(row, detailSet) {
  const cell = el('td', 'rank-company');
  const ticker = row.ticker || '—';
  if (row.ticker && detailSet.has(row.ticker)) {
    const link = el('a', 'ticker-link', ticker);
    link.href = '#/' + encodeURIComponent(row.ticker);
    link.title = '開單檔判讀（含 disproof 與催化劑）';
    cell.appendChild(link);
  } else {
    const plain = el('span', 'ticker-plain', ticker);
    plain.title = row.ticker ? '這檔尚未 materialize 單檔判讀' : 'registry 沒有登記 research ticker';
    cell.appendChild(plain);
  }
  const company = el('div', 'company', row.company_label || row.company_id);
  company.title = row.company_id;
  cell.appendChild(company);
  return cell;
}

function rankTable(rows, columns, detailSet) {
  const wrap = el('div', 'table-wrap');
  const table = el('table', 'rank');
  const head = el('thead');
  const headRow = el('tr');
  columns.forEach((col) => headRow.appendChild(th(col.title)));
  head.appendChild(headRow);
  table.appendChild(head);
  const body = el('tbody');
  rows.forEach((row) => {
    const tr = el('tr');
    columns.forEach((col) => tr.appendChild(col.cell(row, detailSet)));
    body.appendChild(tr);
  });
  table.appendChild(body);
  // 手機上每一列變一張小卡（2026-10-07：追蹤表兩條線在手機上右邊欄位被切掉；與計分表、層說明同一個 `stackTable`）
  wrap.appendChild(stackTable(table));
  return wrap;
}

/* ---------- 資產配置（beta state；照抄 Engine D beta monitor 的輸出，不重算、不排序） ----------
   圖表依 dataviz skill：形式先於顏色；色跟實體走（sleeve 的 slot 由 materialize 固定）；細的 mark、
   hairline 格線；圖上直接印數字（差距列印目標／容忍／實際／差距），tooltip 只加分不當唯一讀法。
   2026-10-07：「表格版」拿掉（使用者：「不需要給我看的…不是收起來 是拿掉」）——它與圖上印的數字重複。所有數字都是 artifact 的原值，
   這裡只做 ×100 的百分比排版與座標換算——沒有任何財務算術。 */

const SVG_NS = 'http://www.w3.org/2000/svg';

function svgEl(tag, attrs, text) {
  const node = document.createElementNS(SVG_NS, tag);
  Object.keys(attrs || {}).forEach((k) => node.setAttribute(k, String(attrs[k])));
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

/* （個股頁 S5b 的圖住這一段：與資產配置的圖一樣只做座標換算——首屏卡片那段有「不得自己算報酬」的檢查，畫圖不放在那裡。） */
/* ---------- 個股頁 S5b：圖（2026-10-08；schema v1.0 規則 6、8、9） ----------
   量化圖只畫系統裡的數字（三題、需求錨、吃到多少的值照抄，不另算）；意思交給 Y 軸與那一句讀法（規則 8），圖下不放一坨說明；
   圖上的字不准互相重疊——由 `?selfcheck=1` 機械量測（selfCheck），0 才算過（S5c）。
   2026-10-08 使用者回饋（電腦上看）：圖縮在左邊、看起來歪；柱狀圖要有 Y 軸（軸上寫這是什麼、標量），下面那一坨小字不用。
   所以圖照**這一頁內容欄的寬度 1:1 出圖**（`chartWidth`；手機約 340、電腦最多 880），柱狀圖一律用 `barChart`（Y 軸＋刻度＋最新一期）。
   放哪一塊照 page_schema：B2 需求傳導＝錨與吃到多少、B3 營收從哪來＝營收、B6 怎麼被定價＝參考尺與走勢。
   SVG 元素用資產配置那一段既有的 `svgEl`／`SVG_NS`（同一份，不另寫）。座標換算只住這一段（同 `pct()`／`meter()` 的寫法）。 */

function tqLine(view, suffix) {
  const panel = view && view.three_questions;
  if (!panel || !Array.isArray(panel.lines)) return null;
  return panel.lines.find((line) => String(line.key || '').endsWith(suffix)) || null;
}

const CURRENCY_WORD = { TWD: '元台幣', USD: '美元', JPY: '日圓', EUR: '歐元', GBP: '英鎊', CNY: '元人民幣',
  KRW: '韓元', SEK: '瑞典克朗', CAD: '加幣', AUD: '澳幣', HKD: '港幣', CHF: '瑞士法郎' };

function fmtMultiple(v) {
  return fmtNumber(v, v >= 100 ? 0 : v >= 10 ? 1 : 2);
}

/** 圖的寬（px）＝這一頁內容欄的寬，1:1 出圖：手機約 340、電腦最多 880（再寬字就太散）。 */
function chartWidth() {
  const w = (app && app.clientWidth) || 360;
  return Math.max(300, Math.min(880, w - 56));
}

/** 估字寬（11px：中文一個字寬、其他約 0.6 個）——只拿來決定標籤放哪一列，真的有沒有疊字由 selfcheck 量。 */
function labelWidth(s, size) {
  const px = size || 11;
  return Array.from(String(s)).reduce((w, ch) => w + (ch.charCodeAt(0) >= 0x2000 ? px : px * 3 / 5), 0);
}

/** 柱狀圖的量級：最大值 ≥ 1 億就用「億」，≥ 1 萬用「萬」，否則原單位（台幣、美元、日圓都適用）。 */
function scaleFor(maxAmount) {
  if (maxAmount >= 1e8) return { divisor: 1e8, word: '億' };
  if (maxAmount >= 1e4) return { divisor: 1e4, word: '萬' };
  return { divisor: 1, word: '' };
}

/** 好讀的刻度：0 到最大值之間 3 到 4 格，每格是 1、2、2.5、5 乘 10 的次方。 */
function barTicks(maxShown) {
  const raw = maxShown / 3;
  const exponent = Math.floor(Math.log10(raw));
  const base = 10 ** exponent;
  const f = raw / base;
  const step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * base;
  const ticks = [0];
  while (ticks[ticks.length - 1] < maxShown) ticks.push(ticks[ticks.length - 1] + step);
  return { ticks, step };
}

/** 正規柱狀圖：左上是 Y 軸的名字（這條序列是什麼、單位），左邊刻度，下面首尾期別，最新一期頭上寫數字（與年增）。
 *  `items`：[{period, amount（原單位）}]；`unit`：幣別字（美元、元台幣）；`latest`：最新一期頭上的字。只做座標換算，值照抄。 */
function barChart({ items, title, unit, latest, klass }) {
  const W = chartWidth();
  const maxAmount = Math.max(...items.map((it) => it.amount));
  if (!(maxAmount > 0)) return null;
  const scale = scaleFor(maxAmount);
  const shown = (amount) => amount / scale.divisor;
  const { ticks, step } = barTicks(shown(maxAmount));
  const topTick = ticks[ticks.length - 1];
  const left = 52, right = W - 8, top = 26, bottom = 136;
  const y = (v) => bottom - (v / topTick) * (bottom - top);
  const slot = (right - left) / items.length;
  const gap = Math.max(3, Math.round(slot / 4));
  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${bottom + 24}`, class: 'chart chart-bars', role: 'img', 'aria-label': title });
  ticks.forEach((t) => {
    svg.appendChild(svgEl('line', { x1: left, y1: y(t), x2: right, y2: y(t), class: t === 0 ? 'chart-axis' : 'chart-grid' }));
    svg.appendChild(svgEl('text', { x: left - 6, y: y(t) + 4, 'text-anchor': 'end', class: 'chart-tick' },
      fmtNumber(t, step < 1 ? 1 : 0)));
  });
  items.forEach((it, i) => {
    const top_ = y(shown(it.amount));
    svg.appendChild(svgEl('rect', { x: left + slot * i + gap / 2, y: top_, width: Math.max(2, slot - gap),
      height: Math.max(1, bottom - top_), rx: 1.5, class: klass || 'bar bar-pos' }));
  });
  const last = items[items.length - 1];
  const lastX = left + slot * (items.length - 0.5);
  if (latest) {
    const w = labelWidth(latest, 12);
    const x0 = Math.max(left, Math.min(right - w, lastX - w / 2));
    // 標籤靠右收進圖裡時會蓋到前一根柱：放在它橫跨的每一根柱的上方（手機寬度量到「1,239.3」壓在較高的前一根上）
    const spanned = items.filter((it, i) => left + slot * (i + 1) - gap / 2 >= x0 && left + slot * i + gap / 2 <= x0 + w);
    const peak = spanned.length ? Math.min(...spanned.map((it) => y(shown(it.amount)))) : y(shown(last.amount));
    svg.appendChild(svgEl('text', { x: x0, y: Math.max(16, peak - 6), class: 'chart-label chart-label-strong' }, latest));
  }
  svg.appendChild(svgEl('text', { x: left, y: bottom + 17, 'text-anchor': 'start', class: 'chart-label' }, items[0].period));
  svg.appendChild(svgEl('text', { x: right, y: bottom + 17, 'text-anchor': 'end', class: 'chart-label' }, last.period));
  const wrap = el('div', 'chart-wrap');
  // Y 軸的名字是圖上方的一般文字：手機上長名字（雲端四大現金資本支出：MSFT、GOOGL、AMZN、META）會自己換行
  wrap.appendChild(el('div', 'chart-axis-title', `${title}（${scale.word}${unit}）`));
  wrap.appendChild(svg);
  return wrap;
}

function blockVisuals(payload, view, key) {
  const out = [];
  if (key === 'B2') {
    anchorFigures(payload).forEach((n) => out.push(n));
    const path = pathFigure(payload);
    if (path) out.push(path);
    const capture = captureFigure(payload);
    if (capture) out.push(capture);
  }
  if (key === 'B3') {
    const n = revenueBars(view); if (n) out.push(n);
    betShareLines(payload).forEach((m) => out.push(m));
    mixFigures(payload).forEach((m) => out.push(m));
  }
  if (key === 'B5') eventReactionLines(payload).forEach((m) => out.push(m));
  if (key === 'B4') {
    // 標出它坐的層：讀圖面板的「坐的節點」（與讀圖、是不是新賭注同一份 seats）；頁首「做什麼」講的那幾格（押的格）粗框加標籤
    const seats = ((view.readings || {}).context || {}).seats || Object.keys(payload.node_names || {});
    const what = payload.what_it_does || {};
    const word = what.source === 'rides' ? '押在' : '在';
    (payload.diagrams || []).forEach((d) => out.push(diagramFigure(d, seats, payload.ticker, what.focus, word)));
  }
  if (key === 'B6') { const n = rulerChart(view); if (n) out.push(n); out.push(priceFigure(payload)); }
  return out;
}

/** 參考尺（B6）：今天的倍數落在自家近三年的哪裡。**全部在同一條對數刻度的線上**（2026-10-08 使用者：同組中位要在線上、
 *  最高最低也要有線）：細線是整把尺、粗的一段是自家三年的範圍（兩端有刻度線）、中位一條刻度線、今天一個點、同組中位一個菱形
 *  （只在同口徑時畫）。每個記號旁邊直接寫它是什麼；標籤會撞在一起就換一列放（字不准重疊——規則 9）。
 *  對數刻度——倍數常跨兩個數量級（例：AXTI 三年 P/S 0.53 → 96），線性尺會把中位擠到邊上。 */
const RULER_BASIS = { 'P/S': '股價營收比（P/S）', 'EV/S': '企業價值營收比（EV/S）' };

function rulerChart(view) {
  const own = tqLine(view, ':own_history_pctile');
  const d = own && own.datum;
  const dep = (d && d.dependencies) || {};
  const det = dep.detail || {};
  if (!d || d.status !== 'available' || !(det.min > 0 && det.max > 0 && det.median > 0 && det.multiple_today > 0)) return null;
  const basis = dep.basis || '倍數';
  const cohortLine = tqLine(view, ':cohort_median');
  const cd = cohortLine && cohortLine.datum;
  const cohort = cd && cd.status === 'available' && typeof cd.value === 'number' && cd.value > 0
    && (cd.dependencies || {}).basis === dep.basis ? cd : null;
  const marks = [det.min, det.max, det.median, det.multiple_today].concat(cohort ? [cohort.value] : []);
  const lo = Math.min(...marks) / 1.15;
  const hi = Math.max(...marks) * 1.15;
  const W = chartWidth();
  const L = 16, R = W - 16, Y = 40;
  const x = (v) => L + (Math.log(v) - Math.log(lo)) / (Math.log(hi) - Math.log(lo)) * (R - L);
  const rows = { above: Y - 16, below: Y + 26, below2: Y + 43 };
  const placed = { above: [], below: [], below2: [] };
  const labels = [];
  const place = (text, at, prefer, strong) => {
    const w = labelWidth(text, strong ? 12 : 11);
    const x0 = Math.max(2, Math.min(W - 2 - w, at - w / 2));
    const row = prefer.find((name) => placed[name].every(([a, b]) => x0 + w + 8 <= a || b + 8 <= x0)) || prefer[prefer.length - 1];
    placed[row].push([x0, x0 + w]);
    labels.push({ text, x: x0, y: rows[row], strong });
  };
  const tx = x(det.multiple_today);
  place(`今天 ${fmtMultiple(det.multiple_today)}`, tx, ['above', 'below2'], true);
  place(`最低 ${fmtMultiple(det.min)}`, x(det.min), ['below', 'below2']);
  place(`最高 ${fmtMultiple(det.max)}`, x(det.max), ['below', 'below2']);
  place(`中位 ${fmtMultiple(det.median)}`, x(det.median), ['below', 'above', 'below2']);
  if (cohort) place(`同組中位 ${fmtMultiple(cohort.value)}`, x(cohort.value), ['above', 'below', 'below2']);
  const height = placed.below2.length ? rows.below2 + 8 : rows.below + 8;
  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${height}`, class: 'chart chart-ruler', role: 'img',
    'aria-label': `今天的 ${basis} 在自家三年的位置` });
  svg.appendChild(svgEl('line', { x1: L, y1: Y, x2: R, y2: Y, class: 'ruler-axis' }));
  svg.appendChild(svgEl('line', { x1: x(det.min), y1: Y, x2: x(det.max), y2: Y, class: 'ruler-range' }));
  [det.min, det.max].forEach((v) => svg.appendChild(svgEl('line', { x1: x(v), y1: Y - 10, x2: x(v), y2: Y + 10, class: 'ruler-end' })));
  svg.appendChild(svgEl('line', { x1: x(det.median), y1: Y - 10, x2: x(det.median), y2: Y + 10, class: 'ruler-median' }));
  if (cohort) {
    const cx = x(cohort.value);
    svg.appendChild(svgEl('path', { d: `M${cx} ${Y - 8}L${cx + 7} ${Y}L${cx} ${Y + 8}L${cx - 7} ${Y}Z`, class: 'ruler-cohort' }));
  }
  svg.appendChild(svgEl('circle', { cx: tx, cy: Y, r: 6, class: 'ruler-today' }));
  labels.forEach((lab) => svg.appendChild(svgEl('text', { x: lab.x, y: lab.y,
    class: lab.strong ? 'chart-label chart-label-strong' : 'chart-label' }, lab.text)));
  const wrap = el('div', 'chart-wrap');
  wrap.appendChild(svg);
  const cdet = cohort ? ((cohort.dependencies || {}).detail || {}) : {};
  wrap.appendChild(el('div', 'chart-legend', `今天 ${fmtMultiple(det.multiple_today)} 倍＝自家近三年第 ${fmtNumber(d.value, 0)} 百分位`
    + `（三年裡約 ${fmtNumber(d.value, 0)}% 的交易日倍數比今天低）。倍數＝${RULER_BASIS[basis] || basis}，對數刻度`
    + (cohort ? `；同組＝${cdet.theme || '主題等權組'}（同口徑 ${cdet.n_same_basis || '?'} 檔），只當脈絡。` : '；沒有同口徑的主題等權組。')));
  return wrap;
}

/** 營收（B3 營收從哪來，2026-10-08 使用者：營收放在一起看）：最近 12 期（台股月營收、EDGAR 季營收照抄三題③的序列），
 *  最新一期頭上寫年增。幣別由序列自己帶（`alpha.three_questions._series_currency`），混幣別就不畫（不換算）。 */
function revenueBars(view) {
  const line = tqLine(view, ':in_numbers_series');
  const d = line && line.datum;
  if (!d || d.status !== 'available' || !Array.isArray(d.value) || d.value.length < 2) return null;
  const det = (d.dependencies && d.dependencies.detail) || {};
  if (!det.currency) {
    return el('div', 'row-reason', Array.isArray(det.currencies) && det.currencies.length
      ? `營收序列的幣別混在一起（${det.currencies.join('／')}）——不畫成一張圖` : '營收序列沒標幣別——不畫');
  }
  const items = d.value.slice(-12).map((p) => ({
    period: p.data_month || String(p.period_end || '').slice(0, 7),
    amount: typeof p.revenue_twd_thousand === 'number' ? p.revenue_twd_thousand * 1000 : p.value,
    yoy: typeof p.yoy === 'number' ? p.yoy : null,
  }));
  if (items.some((it) => typeof it.amount !== 'number' || !isFinite(it.amount))) return null;
  const last = items[items.length - 1];
  const monthly = typeof d.value[0].data_month === 'string';      // 台股月營收的點帶 data_month；EDGAR 的帶 period_end
  // 標題照抄口徑字樣（不做算術）：日本 EDINET 是半年、20-F 是年度，其餘季度（2026-10-21 日韓財報來源；順帶修 20-F 被標成每季）
  const basisText = String((d.dependencies || {}).basis || '');
  const title = monthly ? '每月營收' : basisText.includes('半年') ? '每半年營收' : basisText.includes('年度') ? '每年營收' : '每季營收';
  return barChart({ items, title, unit: CURRENCY_WORD[det.currency] || det.currency,
    latest: last.yoy == null ? null : `年增 ${fmtPercent(last.yoy)}` });
}

/** 需求錨（B2「錨的變化」，個股頁 S3a）：這家公司在結構表走到的錨對到的 A2 序列——每條一張柱狀圖（Y 軸寫它是什麼、
 *  最新一期頭上寫量與年增）。可知日、哪幾家推算、代理說明、走到哪個錨，放進這一塊的「細節」（`chainDetail`），圖下不放字。
 *  全部照抄 materialize 的 `demand_anchor`（不加總、不換算）；沒有就照寫原因（走不到錨／題材沒宣告序列／這一輪沒讀到）。 */
function anchorFigures(payload) {
  const demand = payload.demand_anchor;
  if (!demand) return [];
  if (demand.absence) {
    return [el('div', 'row-reason ss-pending', `錨的變化：${demand.absence.reason || absenceLabel(demand.absence.kind) || '沒有'}`)];
  }
  const out = [];
  (demand.series || []).forEach((s) => { const fig = anchorBars(s); if (fig) out.push(fig); });
  return out;
}

function anchorBars(s) {
  if (s.absence || !(s.points || []).length) {
    return el('div', 'row-reason ss-pending', `${s.label || s.key}：${(s.absence && s.absence.reason) || '沒有值'}`);
  }
  const pts = s.points.slice(-12);
  const who = (s.components || []).map((c) => c.ticker).join('、');
  const items = pts.map((p) => ({ period: p.period, amount: p.value }));
  const lastAmount = items[items.length - 1].amount;
  const lastYoy = pts[pts.length - 1].yoy;
  const scale = scaleFor(Math.max(...items.map((it) => it.amount)));
  const latest = `${fmtNumber(lastAmount / scale.divisor, 0)}${lastYoy != null ? `（年增 ${fmtPercent(lastYoy)}）` : ''}`;
  return barChart({ items,
    title: s.aggregation === 'single' ? `${s.label}（會計季）` : `${s.label}${who ? `：${who}` : ''}`,
    unit: CURRENCY_WORD[s.currency] || s.currency || '', latest });
}

/** 吃到多少（B2，個股頁 S3b）：每 10 億美元的錨對應它多少美元營收——往上＝吃到的比例變大。全部照抄 materialize 的 `capture`
 *  （季營收、換匯的季均價、比值都在 `alpha.capture` 算好）；換匯與可知日放進這一塊的「細節」。沒有就照寫原因。 */
function captureFigure(payload) {
  const cap = payload.capture;
  if (!cap) return null;
  if (cap.absence || !(cap.points || []).length) {
    return el('div', 'row-reason ss-pending', `吃到多少：${(cap.absence && cap.absence.reason) || '沒有值'}`);
  }
  const pts = cap.points.slice(-12);
  const last = pts[pts.length - 1];
  const scale = scaleFor(Math.max(...pts.map((p) => p.per_billion)));
  return barChart({ items: pts.map((p) => ({ period: p.period, amount: p.per_billion })),
    title: '吃到多少：每 10 億美元雲端資本支出對應它的營收', unit: '美元',
    latest: fmtNumber(last.per_billion / scale.divisor, 1), klass: 'bar bar-capture' });
}

/** 技術示意圖（B4 與層說明頁共用）：研究 session 畫的 SVG，materialize 檢查過才嵌、編成 data URI；用 <img> 顯示
 *  （SVG 在 img 裡不執行任何東西）。規則 6：標「示意」、附出處——出處摺起來，第一眼只看圖。
 *  `mine`＝這一頁要標出來的節點（個股頁：它坐的層；閱讀頁：那一層）。2026-10-08 使用者：「我想知道它出現在示意圖的哪一個地方」
 *  ——圖的每一格帶它畫的是哪幾個節點與位置（`d.boxes`，畫圖工具量的），坐的那幾格疊一個框、寫「在這裡」；圖上方一句話列出是哪幾格。
 *  框只是疊在圖片上的位置換算（同 pct() 的寫法），不改圖本身。 */
/** 一張示意圖＋「在這裡」的框（2026-10-08 使用者：「我想知道它出現在示意圖的哪一個地方」）。位置表（`d.boxes`，畫圖器記的
 *  每一格位置與節點）換成百分比疊在圖上——只是座標換算，不改圖。`mine`＝它坐的節點（框線）；`focus`＝頁首「做什麼」講的那幾個
 *  （押的格；粗框＋標籤）。`focusWord`：押的格寫「押在」。手畫的圖沒有位置表＝照實說標不出。 */
function diagramFigure(d, mine, who, focus, focusWord) {
  const box = el('div', 'diagram');
  box.appendChild(el('div', 'diagram-title', d.title || '示意圖'));
  const want = new Set(mine || []);
  const strong = new Set(focus || mine || []);
  const hits = (Array.isArray(d.boxes) ? d.boxes : []).filter((b) => (b.nodes || []).some((n) => want.has(n)));
  const isFocus = (b) => (b.nodes || []).some((n) => strong.has(n));
  const titles = (list) => list.map((b) => `「${b.title}」`).join('、');
  if (who && !Array.isArray(d.boxes)) {
    box.appendChild(el('div', 'diagram-where', '這張圖沒有記下每一格的位置（不是用畫圖工具畫的），標不出在哪一格'));
  } else if (who && hits.length) {
    const main = hits.filter(isFocus);
    const also = hits.filter((b) => !isFocus(b));
    const head = main.length ? `${who} ${focusWord || '在'}：${titles(main)}` : `${who} 在這張圖的：${titles(also)}`;
    box.appendChild(el('div', 'diagram-where', main.length && also.length ? `${head}｜圖上也在：${titles(also)}` : head));
  }
  const frame = el('div', 'diagram-frame');
  const img = document.createElement('img');
  img.className = 'diagram-img';
  img.src = d.src;
  img.alt = `示意圖：${d.title || ''}`;
  img.loading = 'lazy';
  frame.appendChild(img);
  if (d.height > 0 && d.width > 0) {
    hits.forEach((b) => {
      const mark = el('div', isFocus(b) ? 'diagram-mark' : 'diagram-mark diagram-mark-also');
      mark.style.top = `${(b.top / d.height) * 100}%`;
      mark.style.height = `${(b.height / d.height) * 100}%`;
      mark.style.left = `${(b.left / d.width) * 100}%`;
      mark.style.width = `${(b.span / d.width) * 100}%`;
      if (who && isFocus(b)) mark.appendChild(el('span', 'diagram-mark-tag', `${who} ${focusWord || '在'}這裡`));
      frame.appendChild(mark);
    });
  }
  box.appendChild(frame);
  // 「圖上：…」是畫圖那天圖上的供應商——日期跟著印，之後新入圖的不會自己出現在圖裡
  box.appendChild(el('div', 'chart-legend', `示意｜${d.caption || ''}${d.drawn_at ? `｜${d.drawn_at} 畫` : ''}`));
  const sources = d.sources || [];
  if (sources.length) {
    box.appendChild(drill(`出處 ${sources.length} 份`, () => {
      const list = el('div', 'ss-cells');
      sources.forEach((s) => list.appendChild(el('div', 'attention-body', `${s.what || ''}　${s.ref || ''}`)));
      return list;
    }));
  }
  return box;
}

function fmtMoney(value, currency) {
  if (typeof value !== 'number' || !isFinite(value)) return null;
  const text = value.toLocaleString('zh-Hant', { maximumFractionDigits: 0 });
  return currency ? `${currency} ${text}` : text;
}

function fmtRatioPct(value, digits) {
  if (typeof value !== 'number' || !isFinite(value)) return null;
  return (value * 100).toLocaleString('zh-Hant', { minimumFractionDigits: digits, maximumFractionDigits: digits }) + '%';
}

function tile(label, valueText, subText, extraClass) {
  const box = el('div', 'tile ' + (extraClass || ''));
  box.appendChild(el('div', 'tile-label', label));
  box.appendChild(el('div', 'tile-value', valueText === null || valueText === undefined ? '—' : valueText));
  if (subText) box.appendChild(el('div', 'tile-sub', subText));
  return box;
}

function statusBadge(kind, text) {
  const icon = { good: '●', warning: '▲', serious: '▲', critical: '■', neutral: '○' }[kind] || '○';
  const badge = el('span', 'badge badge-' + ({ good: 'ready', warning: 'stale', serious: 'stale', critical: 'blocked', neutral: 'absence' }[kind] || 'absence'), `${icon} ${text}`);
  return badge;
}

/* 行情狀態 → 徽章（圖示＋文字，永遠不只靠顏色）。字彙來自 artifact.vocab，不在這裡另寫。 */
function priceStatusBadge(inst) {
  const table = (BETA_VOCAB && BETA_VOCAB.price_status_labels) || {};
  const status = inst.price_status;
  const kind = status === 'observed' ? 'good' : (status === 'insufficient_history' ? 'neutral' : 'critical');
  return statusBadge(kind, inst.status_label || table[status] || status);
}

/* ① 現在的配置：水平堆疊條（部分對整體，≤ 6 段，2px 表面間隙）＋ 圖例（≥ 2 系列必有） */
function allocationStack(sleeves) {
  const wrap = el('div');
  const stack = el('div', 'stack');
  const legend = el('div', 'legend');
  sleeves.forEach((s) => {
    if (typeof s.actual !== 'number') return;
    const seg = el('div');
    seg.className = 'swatch-' + s.slot;
    seg.style.flexGrow = String(s.actual);
    seg.title = `${s.label} ${fmtRatioPct(s.actual, 1)}`;
    stack.appendChild(seg);
    const item = el('span');
    item.appendChild(el('span', 'key swatch-' + s.slot));
    item.appendChild(document.createTextNode(`${s.label} ${fmtRatioPct(s.actual, 1) || '算不到'}`));
    legend.appendChild(item);
  });
  wrap.appendChild(stack);
  wrap.appendChild(legend);
  return wrap;
}

/* ② 距目標多遠：每個 sleeve 一條分歧條（低於目標往左、高於往右），灰帶＝容忍區間（到位、無偏好）。 */
function gapRows(sleeves) {
  const box = el('div', 'gaps');
  let extent = 0.02;
  sleeves.forEach((s) => {
    if (typeof s.gap === 'number') extent = Math.max(extent, Math.abs(s.gap));
    if (typeof s.band === 'number') extent = Math.max(extent, s.band);
  });
  extent = extent * 1.15;
  const pct = (ratio) => 50 + (ratio / extent) * 50;
  sleeves.forEach((s) => {
    const row = el('div', 'gap-row');
    const head = el('div', 'gap-head');
    const name = el('div');
    name.appendChild(el('span', 'key swatch-' + s.slot));
    name.appendChild(document.createTextNode(s.label));
    head.appendChild(name);
    head.appendChild(el('div', 'gap-nums',
      `目標 ${fmtRatioPct(s.target, 1)}｜容忍 ±${fmtRatioPct(s.band, 1)}｜實際 ${fmtRatioPct(s.actual, 1) || '算不到'}`));
    row.appendChild(head);
    const right = el('div');
    const track = el('div', 'gap-track');
    if (typeof s.band === 'number') {
      const band = el('div', 'gap-band');
      band.style.left = pct(-s.band) + '%';
      band.style.width = (pct(s.band) - pct(-s.band)) + '%';
      track.appendChild(band);
    }
    const zero = el('div', 'gap-zero');
    zero.style.left = '50%';
    track.appendChild(zero);
    if (typeof s.gap === 'number') {
      const bar = el('div', 'gap-bar ' + (s.gap < 0 ? 'neg' : 'pos'));
      const a = pct(Math.min(0, s.gap));
      const b = pct(Math.max(0, s.gap));
      bar.style.left = a + '%';
      bar.style.width = Math.max(b - a, 0.4) + '%';
      bar.title = `${s.label} 差距 ${fmtRatioPct(s.gap, 1)}`;
      track.appendChild(bar);
    }
    right.appendChild(track);
    const state = el('div', 'gap-state');
    state.appendChild(document.createTextNode(
      (typeof s.gap === 'number' ? `差距 ${s.gap > 0 ? '+' : ''}${fmtRatioPct(s.gap, 1)}　` : '') + (s.state_label || '')));
    if (s.unavailable_label) state.appendChild(el('span', 'dim', '　' + s.unavailable_label));
    right.appendChild(state);
    row.appendChild(right);
    box.appendChild(row);
  });
  return box;
}

/* ③ 儀表：單一比值對一個上限（同色系軌道；狀態色一定配圖示＋文字）。 */
function meter(ratio, cap, opts) {
  const o = opts || {};
  const wrap = el('div');
  const track = el('div', 'meter');
  const fill = el('div', 'meter-fill ' + (o.tone || ''));
  const scale = o.scale || cap || 1;
  fill.style.width = (typeof ratio === 'number' ? Math.max(0, Math.min(100, (ratio / scale) * 100)) : 0) + '%';
  track.appendChild(fill);
  if (typeof o.warn === 'number') { const w = el('div', 'meter-cap'); w.style.left = (o.warn / scale) * 100 + '%'; w.title = '警戒'; track.appendChild(w); }
  if (typeof cap === 'number' && cap < scale) { const c = el('div', 'meter-cap'); c.style.left = (cap / scale) * 100 + '%'; c.title = '上限'; track.appendChild(c); }
  wrap.appendChild(track);
  const labels = el('div', 'meter-labels');
  labels.appendChild(el('span', null, o.left || '0'));
  labels.appendChild(el('span', null, o.right || ''));
  wrap.appendChild(labels);
  return wrap;
}

/* ④ 52 週區間位置：軌道＝低點→高點，標記＝現在。純位置，不是訊號。 */
function rangeMeter(level) {
  const wrap = el('div');
  const track = el('div', 'meter');
  const p = level && typeof level.range_percentile_52w === 'number' ? level.range_percentile_52w : null;
  const fill = el('div', 'meter-fill');
  fill.style.width = (p === null ? 0 : p * 100) + '%';
  track.appendChild(fill);
  if (p !== null) { const mark = el('div', 'meter-mark'); mark.style.left = (p * 100) + '%'; track.appendChild(mark); }
  wrap.appendChild(track);
  const labels = el('div', 'meter-labels');
  labels.appendChild(el('span', null, '52 週低點'));
  labels.appendChild(el('span', null, p === null ? '位置：算不到' : `位置 ${fmtRatioPct(p, 0)}`));
  labels.appendChild(el('span', null, '52 週高點'));
  wrap.appendChild(labels);
  return wrap;
}

/* ⑤ 折線：單一系列（不需圖例）、2px、10% 面積淡色、hairline 格線、端點標籤、十字線 tooltip。 */
function niceTicks(lo, hi, count) {
  if (!(hi > lo)) return [lo];
  const span = hi - lo;
  const raw = span / count;
  const mag = Number('1e' + Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = (norm >= 5 ? 10 : (norm >= 2 ? 5 : (norm >= 1 ? 2 : 1))) * mag;
  const ticks = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) ticks.push(Number(v.toFixed(10)));
  return ticks;
}

function lineChart(series, opts) {
  const o = opts || {};
  const W = 640; const H = 200; const padL = 46; const padR = 60; const padT = 10; const padB = 24;
  const wrap = el('div', 'chart');
  if (!series || series.length < 2) {
    wrap.appendChild(el('p', 'note', o.emptyNote || '沒有足夠的序列可畫。'));
    return wrap;
  }
  const values = series.map((r) => r.close);
  const lo = Math.min.apply(null, values);
  const hi = Math.max.apply(null, values);
  const padY = (hi - lo) / 12.5 || Math.abs(hi) / 50 || 1;   // 座標留白，不是任何財務算術
  const yMin = lo - padY; const yMax = hi + padY;
  const x = (i) => padL + (i / (series.length - 1)) * (W - padL - padR);
  const y = (v) => padT + (1 - (v - yMin) / (yMax - yMin)) * (H - padT - padB);
  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': o.ariaLabel || '' });
  niceTicks(yMin, yMax, 3).forEach((t) => {
    svg.appendChild(svgEl('line', { x1: padL, x2: W - padR, y1: y(t), y2: y(t), class: 'grid' }));
    svg.appendChild(svgEl('text', { x: padL - 6, y: y(t) + 3, 'text-anchor': 'end', class: 'tick' }, fmtNumber(t, decimalsFor(t))));
  });
  svg.appendChild(svgEl('line', { x1: padL, x2: W - padR, y1: H - padB, y2: H - padB, class: 'axis' }));
  const d = series.map((r, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(r.close).toFixed(1)}`).join(' ');
  svg.appendChild(svgEl('path', { d: `${d} L${x(series.length - 1).toFixed(1)},${H - padB} L${x(0).toFixed(1)},${H - padB} Z`, class: 'area' }));
  svg.appendChild(svgEl('path', { d: d, class: 'line' }));
  const last = series[series.length - 1];
  svg.appendChild(svgEl('circle', { cx: x(series.length - 1), cy: y(last.close), r: 4, class: 'dot' }));
  svg.appendChild(svgEl('text', { x: x(series.length - 1) + 8, y: y(last.close) + 4, class: 'end-label' }, fmtNumber(last.close, decimalsFor(last.close))));
  svg.appendChild(svgEl('text', { x: padL, y: H - 6, class: 'tick' }, series[0].session_date));
  svg.appendChild(svgEl('text', { x: W - padR, y: H - 6, 'text-anchor': 'end', class: 'tick' }, last.session_date));
  const cross = svgEl('line', { x1: 0, x2: 0, y1: padT, y2: H - padB, class: 'cross', visibility: 'hidden' });
  const hoverDot = svgEl('circle', { cx: 0, cy: 0, r: 4, class: 'dot', visibility: 'hidden' });
  svg.appendChild(cross);
  svg.appendChild(hoverDot);
  const hit = svgEl('rect', { x: padL, y: padT, width: W - padL - padR, height: H - padT - padB, class: 'hit', tabindex: 0 });
  svg.appendChild(hit);
  wrap.appendChild(svg);
  const tip = el('div', 'tip');
  wrap.appendChild(tip);
  const show = (i, clientX) => {
    const r = series[i];
    cross.setAttribute('x1', x(i)); cross.setAttribute('x2', x(i)); cross.setAttribute('visibility', 'visible');
    hoverDot.setAttribute('cx', x(i)); hoverDot.setAttribute('cy', y(r.close)); hoverDot.setAttribute('visibility', 'visible');
    tip.textContent = '';
    const b = el('b', null, fmtNumber(r.close, decimalsFor(r.close)));
    tip.appendChild(el('span', 'k'));
    tip.appendChild(b);
    tip.appendChild(document.createTextNode(`　${r.session_date}`));
    tip.style.display = 'block';
    const box = wrap.getBoundingClientRect();
    const px = clientX === null ? (x(i) / W) * box.width : clientX - box.left;
    tip.style.left = Math.min(Math.max(px + 12, 0), box.width - tip.offsetWidth - 4) + 'px';
    tip.style.top = '4px';
  };
  const hide = () => { cross.setAttribute('visibility', 'hidden'); hoverDot.setAttribute('visibility', 'hidden'); tip.style.display = 'none'; };
  hit.addEventListener('pointermove', (ev) => {
    const box = svg.getBoundingClientRect();
    const rel = ((ev.clientX - box.left) / box.width) * W;
    const i = Math.round(((rel - padL) / (W - padL - padR)) * (series.length - 1));
    show(Math.max(0, Math.min(series.length - 1, i)), ev.clientX);
  });
  hit.addEventListener('pointerleave', hide);
  hit.addEventListener('focus', () => show(series.length - 1, null));
  hit.addEventListener('blur', hide);
  return wrap;
}

/* 首頁卡片的折線（2026-10-28）：單一系列（不需圖例）、無軸、線用次要色、最後一點用強調色；hover 讀 <title> 的頭尾兩點。
   只做座標換算——漲跌數字不在這裡算（卡片照印三題已算好的那幾個）。 */
function sparkline(points) {
  const W = 104; const H = 30; const pad = 3;
  const closes = points.map((p) => p.close);
  const lo = Math.min.apply(null, closes);
  const hi = Math.max.apply(null, closes);
  const span = (hi - lo) || 1;                                   // 座標留白，不是任何財務算術
  const n = points.length;
  const x = (i) => pad + (i / (n - 1)) * (W - 2 * pad);
  const y = (c) => pad + (1 - (c - lo) / span) * (H - 2 * pad);
  const first = points[0]; const last = points[n - 1];
  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'spark', role: 'img',
                             'aria-label': `最近 ${n} 個收盤：${first.session_date} 到 ${last.session_date}` });
  const d = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.close).toFixed(1)}`).join(' ');
  svg.appendChild(svgEl('path', { d: d, class: 'spark-line' }));
  svg.appendChild(svgEl('circle', { cx: x(n - 1).toFixed(1), cy: y(last.close).toFixed(1), r: 2.6, class: 'spark-dot' }));
  svg.appendChild(svgEl('title', {}, `${first.session_date} 收 ${fmtNumber(first.close, decimalsFor(first.close))}`
    + ` → ${last.session_date} 收 ${fmtNumber(last.close, decimalsFor(last.close))}`));
  return svg;
}

/** 帶正負號的百分比（預設一位小數）。只有這一份——2026-10-08 前追蹤表那邊另有一個同名函式，JS 後宣告的會蓋掉前面的，
 *  兩份剛好都印一位小數才沒出事（同一天新圖表的 `niceTicks` 撞名就讓整頁「無法載入」）。 */
function signedPct(value, digits = 1) {
  const text = fmtRatioPct(value, digits);
  return text === null ? '—' : (value > 0 ? '+' + text : text);
}

function instrumentCard(inst) {
  const card = el('section', 'panel inst');
  const head = el('div', 'inst-head');
  head.appendChild(el('span', 'ticker', inst.ticker));
  head.appendChild(el('span', 'company', inst.sleeve_label || inst.sleeve));
  head.appendChild(priceStatusBadge(inst));
  if (typeof inst.current_nominal_weight === 'number') head.appendChild(el('span', 'dim', `占 NAV ${fmtRatioPct(inst.current_nominal_weight, 1)}`));
  card.appendChild(head);

  const hb = inst.heartbeat || {};
  // 價格先於一切（看股網站的讀法）：最新完整交易日收盤＋1 日漲跌；單位未登記就明說，不猜。
  const latest = inst.latest_close;
  const priceRow = el('div', 'numbers');
  if (latest && typeof latest.close === 'number') {
    priceRow.appendChild(numberBlock('收盤（' + (latest.session_date || '—') + '）',
      fmtNumber(latest.close, decimalsFor(latest.close)) || '—',
      latest.quote_unit ? latest.quote_unit : '報價單位未登記（provider 原值）'));
  } else {
    priceRow.appendChild(numberBlock('收盤', '—', '沒有已收盤觀測——不是 0'));
  }
  priceRow.appendChild(numberBlock('1 日', signedPct(hb.return_1d, 1), hb.session_date ? '至 ' + hb.session_date : '',
    typeof hb.return_1d === 'number' ? signClass(hb.return_1d) : ''));
  card.appendChild(priceRow);
  const hbRow = el('div', 'hb');
  const dateNode = el('span');
  dateNode.appendChild(document.createTextNode('最新完整交易日 '));
  dateNode.appendChild(el('b', null, hb.session_date || '—'));
  hbRow.appendChild(dateNode);
  [['1日', hb.return_1d], ['5日', hb.return_5d], ['20日', hb.return_20d]].forEach(([k, v]) => {
    const n = el('span');
    n.appendChild(document.createTextNode(k + ' '));
    const b = el('b', null, signedPct(v, 1));
    if (typeof v === 'number') b.classList.add(signClass(v));
    n.appendChild(b);
    hbRow.appendChild(n);
  });
  card.appendChild(hbRow);
  if (hb.twse_reference) {
    const t = hb.twse_reference;
    card.appendChild(el('p', 'note', `TWSE 官方參考 ${t.session_date || ''}：${signedPct(t.return_1d, 1)}（只作最新日期與當日漲跌 reference，不混入自身序列）`));
  }

  const level = inst.water_level || {};
  card.appendChild(rangeMeter(level));
  const wl = el('div', 'status-line');
  wl.appendChild(el('span', null, `距 52 週高點 ${signedPct(level.pct_from_52w_high, 1)}`));
  wl.appendChild(el('span', null, `距 200 日均線 ${signedPct(level.pct_from_sma200, 1)}`));
  if (level.status && level.status !== 'observed') wl.appendChild(statusBadge('neutral', `水位：${level.status}`));
  card.appendChild(wl);

  (inst.blocker_labels || []).forEach((t) => card.appendChild(el('p', 'warn', '▲ ' + t)));
  (inst.warning_labels || []).forEach((t) => card.appendChild(el('p', 'note', t)));

  card.appendChild(lineChart(inst.series, { ariaLabel: `${inst.ticker} 已收盤收盤價`, emptyNote: inst.series_note }));
  card.appendChild(el('p', 'note', inst.series_note || ''));
  return card;
}

function riskTone(value, warn, cap) {
  if (typeof value !== 'number') return 'neutral';
  if (typeof cap === 'number' && value >= cap) return 'critical';
  if (typeof warn === 'number' && value >= warn) return 'warning';
  return 'good';
}

function riskItem(label, value, warn, cap, opts) {
  const o = opts || {};
  const box = el('div', 'tile risk-item');
  const head = el('div', 'tile-label');
  head.appendChild(el('span', null, label));
  const tone = riskTone(value, warn, cap);
  head.appendChild(statusBadge(tone, { good: '正常', warning: '警戒', critical: '達上限', neutral: '未知' }[tone]));
  box.appendChild(head);
  box.appendChild(el('div', 'tile-value', o.valueText || (typeof value === 'number' ? fmtRatioPct(value, 1) : '算不到')));
  box.appendChild(meter(value, cap, { warn: warn, scale: o.scale || cap, tone: tone === 'good' ? '' : tone,
    left: '0', right: o.rightText || (typeof cap === 'number' ? `上限 ${o.capText || fmtRatioPct(cap, 1)}` : '') }));
  if (o.sub) box.appendChild(el('div', 'tile-sub', o.sub));
  return box;
}

let BETA_VOCAB = null;

async function renderBeta() {
  markNav('beta');
  let payload;
  try {
    payload = await getJSON(`${API}/beta`);
  } catch (err) {
    renderStateError(err, '讀不到資產配置');
    return;
  }
  BETA_VOCAB = payload.vocab || {};
  const notes = payload.notes || {};
  const cap = payload.capital || {};
  const cur = cap.base_currency || '';
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';

  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.title));
  const badges = el('div', 'badges');
  if (payload.freshness && payload.freshness.state === 'stale') {
    const b = el('span', 'badge badge-stale', 'stale'); b.title = payload.freshness.rule; badges.appendChild(b);
  }
  badges.appendChild(el('span', 'badge badge-fresh', `monitor ${(payload.point_in_time || {}).report_as_of ? String(payload.point_in_time.report_as_of).slice(0, 16) : ''}`));
  head.appendChild(badges);
  app.appendChild(head);

  // ① 資本：一個主數字（可部署現金）＋三個小數字。
  const sec0 = el('section', 'panel');
  sec0.appendChild(el('h2', null, '現在有多少錢可以動'));
  const tiles = el('div', 'tiles');
  tiles.appendChild(tile('自有現金可部署', fmtMoney(cap.deployable_cash_base, cur), 'cash floor 以上，alpha／beta 共用', 'hero'));
  tiles.appendChild(tile('投資組合總值（NAV）', fmtMoney(cap.nav_base, cur), `其中已投入非現金 ${fmtMoney(cap.invested_non_cash_base, cur) || '—'}`));
  const credit = cap.credit || {};
  tiles.appendChild(tile('未動用貸款額度', fmtMoney(credit.undrawn_amount_base, cur), '不算自有現金；提款逐次人工核准'));
  tiles.appendChild(tile('已借款／月息', `${fmtMoney(credit.drawn_amount_base, cur) || '—'}`, `月息約 ${fmtMoney(credit.estimated_monthly_interest_base, cur) || '—'}｜條件 ${credit.terms_status || '—'}`));
  sec0.appendChild(tiles);
  sec0.appendChild(el('p', 'note', notes.loan || ''));
  app.appendChild(sec0);

  // ② 配置：堆疊條（現在長怎樣）＋ 分歧條（距目標多遠）。
  const alloc = payload.allocation || {};
  const sec1 = el('section', 'panel');
  sec1.appendChild(el('h2', null, '現在的配置 vs 目標'));
  if (alloc.status !== 'available') {
    sec1.appendChild(el('p', 'warn', '▲ 配置算不出來：' + (alloc.unavailable_reason || '未知原因') + '（不是 0，是沒讀到）'));
  } else {
    sec1.appendChild(el('div', 'panel-questions', `分母＝已投入的非現金部位 ${fmtMoney(alloc.invested_non_cash_base, cur) || ''}；不含現金，cash floor 是另一個 authority`));
    sec1.appendChild(allocationStack(alloc.sleeves || []));
    sec1.appendChild(el('div', 'group-title', '距目標多遠（灰帶＝容忍區間，落在裡面就是到位）'));
    sec1.appendChild(gapRows(alloc.sleeves || []));
    sec1.appendChild(el('p', 'note', notes.band || ''));
  }
  (alloc.correlation_warnings || []).forEach((w) => {
    const p = el('p', 'warn');
    p.appendChild(document.createTextNode('▲ ' + (w.name || '') + '：' + (w.detail || '')));
    sec1.appendChild(p);
  });
  app.appendChild(sec1);

  // ③ 風控：只量測，不建議。
  const risk = payload.risk || {};
  const snap = risk.snapshot || {};
  const th = risk.thresholds || {};
  const sec2 = el('section', 'panel');
  sec2.appendChild(el('h2', null, '風控儀表（只量測，不建議）'));
  const grid = el('div', 'risk-grid');
  grid.appendChild(riskItem('總曝險（持股＋槓桿 ETF＋借款）', snap.total_exposure_weight, th.total_exposure_warning, th.total_exposure_cap,
    { valueText: typeof snap.total_exposure_weight === 'number' ? snap.total_exposure_weight.toFixed(2) + 'x' : '算不到',
      capText: typeof th.total_exposure_cap === 'number' ? th.total_exposure_cap.toFixed(2) + 'x' : '',
      sub: typeof snap.wipeout_index_drawdown === 'number' ? `自有資本歸零門檻：指數跌 ${fmtRatioPct(snap.wipeout_index_drawdown, 0)}` : '' }));
  const etf = snap.etf_leverage || {};
  grid.appendChild(riskItem('槓桿 ETF 資金占比', etf.nominal_weight, th.leveraged_nominal_warning, th.leveraged_nominal_cap, { sub: '投入槓桿 ETF 的資金占 NAV' }));
  grid.appendChild(riskItem('換算槓桿曝險', etf.effective_weight, th.leveraged_effective_warning, th.leveraged_effective_cap, { sub: '乘上 2x／3x 之後' }));
  grid.appendChild(riskItem('已提款貸款占 NAV', snap.loan_leverage_weight, null, null, { scale: 0.25, rightText: '（只記錄，不設上限）' }));
  Object.keys(risk.issuer_focus || {}).forEach((issuer) => {
    const e = risk.issuer_focus[issuer];
    grid.appendChild(riskItem(`${issuer} 穿透曝險（已知至少）`, e.total_weight, th.issuer_concentration_warning, null,
      { scale: 0.5, rightText: `警戒 ${fmtRatioPct(th.issuer_concentration_warning, 0)}`,
        sub: `直接 ${fmtRatioPct(e.direct_weight, 1)}｜間接 ${fmtRatioPct(e.indirect_weight, 1)}；覆蓋 partial` }));
  });
  sec2.appendChild(grid);
  (risk.warning_labels || []).forEach((t) => sec2.appendChild(el('p', 'note', '· ' + t)));
  if (risk.hard_blocks && risk.hard_blocks.length) sec2.appendChild(el('p', 'warn', '■ 硬擋：' + risk.hard_blocks.join('、')));
  sec2.appendChild(el('p', 'note', notes.leverage_labels || ''));
  sec2.appendChild(el('p', 'note', notes.lookthrough || ''));
  app.appendChild(sec2);

  // ④ 逐檔：每一檔自己的心跳、52 週位置、自身收盤折線。
  const sec3 = el('section', 'panel');
  sec3.appendChild(el('h2', null, '每一檔現在在哪裡'));
  sec3.appendChild(el('p', 'note', notes.water_level || ''));
  app.appendChild(sec3);
  (payload.instruments || []).forEach((inst) => app.appendChild(instrumentCard(inst)));

  // ⑤ 這份畫面多新（一行；行情更新狀態跟著印——價格是這一頁唯一會自己舊掉的東西）。
  app.appendChild(stateFooter(payload, `行情更新 ${(payload.refresh || {}).status || '—'}`));
  window.scrollTo(0, 0);
}

function renderStateError(err, title) {
  app.textContent = '';
  const box = el('div', 'error');
  const detail = (err.body && err.body.error) || {};
  box.appendChild(el('h2', null, title));
  box.appendChild(el('p', null, detail.reason || detail.message || 'request failed'));
  if (detail.remedy) {
    const p = el('p', 'note');
    p.appendChild(document.createTextNode('修法：'));
    p.appendChild(el('code', null, detail.remedy));
    box.appendChild(p);
  }
  if (detail.note) box.appendChild(el('p', 'note', detail.note));
  app.appendChild(box);
}

/* ---------- 計數格（KPI tile 列） ----------
   ⚠ 2026-10-28：「走圖」頁（renderGraphWalk、walkFraction、walkHitList、duplicateSide）拿掉——併進「圖」頁。
   去處：研究缺口（薄層沒人讀、獨家且自報、供給側未填）→圖頁「還沒讀的地方」逐條；其餘六型是圖的整理工作→圖頁一行計數，
   逐條（含重複節點兩端的逐字，L18）在 `python -m query.graph_walk`（`tests/test_duplicate_nodes.py` 守它印逐字）；
   九型「命中／母體」一行→心跳段 3。 */

function kpiRow(items) {
  const row = el('div', 'tiles');
  items.forEach((it) => row.appendChild(tile(it.label, it.value, it.sub, it.cls)));
  return row;
}

/* ---------- 讀圖（structure_readings state）：狀態字、個股頁的層說明連結、圖預測對錯表 ----------
   讀圖是研究判斷（A3）：照抄 ledger 寫下的判讀、單位、引文與反證，加上 materialize 當下與圖比對的**狀態**。
   ⚠ 2026-10-28：「讀圖」頁（renderStructureReadings、readingRow）拿掉——每一份讀圖的判讀、引文、反證與狀態搬到「圖」頁的層卡片
   （「讀法、引文與反證」點開）；現行／該重讀計數→圖頁頂端一行；圖預測對錯表→追蹤表頁（「我們說過的話，後來對不對」）。 */

const READING_STATUS_TEXT = {
  current: '現行', stale: '跟圖不一致（該重讀）', stale_low: '只有證據等級變了（不必重讀）', expired: '過期（該重讀）',
};

/* ⚠ 2026-10-08：個股頁的「讀圖」卡（`readingsCard`）拿掉——坐的層讀成什麼搬進「技術鏈」那一塊的展開（`seatsDetail`，
   節點印名字不印 ID）；「圖上它供貨或開發的節點：tech:…」那一長串 ID 是給機器的，不再印。 */

/* 坐的層有層說明的，連到閱讀頁（個股頁 plan S4b）。清單照 materialize 給的（與「坐的層」同一份、同一個順序）；
   讀不到 ledger 就說讀不到，不印成「沒有層說明」。 */
function layerNoteLinks(context) {
  const notes = context.layer_notes || [];
  const absence = context.layer_notes_absence;
  if (!notes.length && !absence) return null;
  const box = el('div', 'layer-note-links');
  if (absence) box.appendChild(el('p', 'warn', `▲ 層說明這次沒讀到：${absence.reason}（${absence.kind}）`));
  if (notes.length) {
    const p = el('p', 'note');
    p.appendChild(document.createTextNode('它坐的層有層說明（客戶為什麼選這家的變體、什麼會讓它被換掉）：'));
    notes.forEach((n, i) => {
      if (i) p.appendChild(document.createTextNode('、'));
      const link = el('a', null, n.title || n.node);
      link.href = '#/layer/' + encodeURIComponent(n.node);
      p.appendChild(link);
    });
    box.appendChild(p);
  }
  return box;
}

/* ---------- 圖（2026-10-28 使用者照推薦：讀圖、走圖、層說明、結構表併成一頁；brainstorm 2026-10-28 定案 6：骨架＝層） ----------
   回答「圖的哪裡有機會」：哪一層押得下去、哪一層還要讀、那裡坐著哪幾家小公司、錢在不在變多。
   資料全由 /api/v1/graph 接好、排好（區照字彙表、區內照節點 id、層內公司照首頁的組序）；這裡只畫、只篩（搜尋只藏不排）。 */

function companyChip(c) {
  const chip = el(c.page ? 'a' : 'span', 'co' + (c.main ? ' co-main' : ' co-dim'));
  if (c.page) chip.href = '#/' + encodeURIComponent(c.ticker);
  chip.appendChild(el('span', 'co-name', c.name));
  if (c.state) chip.appendChild(el('i', null, c.state));
  chip.title = [c.ticker, c.name, c.state, c.page ? '' : '沒有個股頁'].filter(Boolean).join('｜');
  return chip;
}

/** 一層的「讀法、引文與反證」（原讀圖頁每一列的內容）：點開才畫。 */
function layerReading(layer) {
  const box = el('div', 'layer-reading');
  const r = layer.reading || {};
  if (layer.kind_plain) box.appendChild(el('p', 'note', `${layer.kind_label}＝${layer.kind_plain}`));
  if (r.text) box.appendChild(mdParagraph(r.text, 'layer-reading-text'));
  (r.citations || []).forEach((c) => {
    const quote = el('div', 'verbatim', c.quote);
    quote.appendChild(el('div', 'src', `${c.angle}｜${(c.edge || []).join(' ')}｜${c.source_id}`
      + (c.independent ? '｜外部印證' : '')));
    box.appendChild(quote);
  });
  (r.disproof || []).forEach((d) => {
    box.appendChild(el('span', 'rule', `反證／確認條件：${d.condition}（出處 ${d.source || '—'}｜`
      + `${d.watch_id ? '有 watch 在盯（' + (d.watch_status || '?') + '）' : '沒有登記 watch'}）`));
  });
  if ((layer.chain || []).length) box.appendChild(el('p', 'note', '從需求端走過來：' + layer.chain.join(' → ')));
  if (layer.reason) box.appendChild(el('p', 'note', '狀態：' + layer.reason));
  box.appendChild(el('p', 'note', `讀於 ${layer.read_on || '—'}｜到期 ${layer.expires || '—'}`));
  return box;
}

function layerCard(layer, zoneKey) {
  const card = el('div', 'layer-card');
  card.dataset.node = layer.node;
  const head = el('div', 'layer-head');
  head.appendChild(el('span', 'layer-name', layer.label));
  head.appendChild(el('span', 'layer-unit', layer.unit_label || ''));
  const kind = el('span', 'layer-kind kind-' + layer.kind, layer.kind_label);
  if (layer.kind_plain) kind.title = layer.kind_plain;
  head.appendChild(kind);
  if (layer.needs_reread) head.appendChild(el('span', 'layer-flag', READING_STATUS_TEXT[layer.status] || '該重讀'));
  if (layer.layer_note) {
    const note = el('a', 'layer-note-link', '層說明');
    note.href = '#/layer/' + encodeURIComponent(layer.node);
    note.title = layer.layer_note.title || '';
    head.appendChild(note);
  }
  head.appendChild(el('span', 'layer-read', `讀到 ${String(layer.read_on || '—').slice(0, 10)}`));
  card.appendChild(head);

  const cos = el('div', 'layer-cos');
  if ((layer.companies || []).length) layer.companies.forEach((c) => cos.appendChild(companyChip(c)));
  else cos.appendChild(el('span', 'co-none', '圖上還沒有這一層的供應商'));
  card.appendChild(cos);

  if (layer.growth) {
    const g = layer.growth;
    card.appendChild(el('div', 'layer-money', `錢在變多嗎：代表公司營收年增 ${signedPct(g.yoy, 0)}`
      + `（${g.period || '—'}；${(g.members || []).join('、')}）`));
  }
  // 押在還判不出的層上的缺 X：缺的多半就是這一份讀圖（F2：一層多半只押一檔，讀一層推一檔）
  if (zoneKey === 'undecided' && (layer.waiting || []).length) {
    card.appendChild(el('div', 'layer-wait', `押在這一層的缺 X：${layer.waiting.join('、')}——缺的多半就是這一份讀圖`));
  }
  if ((layer.also_linked || []).length) {
    card.appendChild(el('div', 'layer-also', '這份讀圖另外關聯（不是這一層的供應商）：' + layer.also_linked.join('、')));
  }
  (layer.reread_reasons || []).forEach((r) => card.appendChild(el('div', 'layer-flag-line', '該重讀：' + r)));
  const more = el('details', 'layer-more');
  more.appendChild(el('summary', null, '讀法、引文與反證'));
  more.addEventListener('toggle', () => {
    if (more.open && more.childElementCount === 1) more.appendChild(layerReading(layer));
  }, { once: false });
  card.appendChild(more);
  card._haystack = [layer.label, layer.node, ...(layer.companies || []).flatMap((c) => [c.name, c.ticker]),
    ...(layer.also_linked || [])].filter(Boolean).join(' ').toLowerCase();
  return card;
}

function graphHoles(holes) {
  const sec = el('section', 'panel');
  sec.appendChild(el('h2', null, '還沒讀的地方（研究下一步）'));
  if (holes.absence) {
    sec.appendChild(el('p', 'warn', `▲ ${holes.absence.reason}——不是 0`));
    return sec;
  }
  (holes.research || []).forEach((q) => {
    const block = el('div', 'hole');
    if (q.absence) {
      block.appendChild(el('p', 'warn', `▲ ${q.short}：${q.absence.reason}——不是 0`));
      sec.appendChild(block);
      return;
    }
    block.appendChild(el('div', 'hole-head', `${q.short}：${q.hit_n} 處`));
    block.appendChild(el('div', 'note', `算一處的條件：${q.hit_rule}（看的是：${q.scope_rule}，共 ${q.scope_n} 個）`));
    if ((q.hits || []).length) {
      const list = el('ul', 'weak');
      q.hits.forEach((h) => {
        const li = el('li');
        const link = el('a', null, h.label);
        link.href = '#/graph/' + encodeURIComponent(h.node);
        link.title = h.node;
        li.appendChild(link);
        if ((h.suppliers || []).length) li.appendChild(el('span', 'dim', `　供應商：${h.suppliers.join('、')}`));
        list.appendChild(li);
      });
      block.appendChild(list);
    }
    sec.appendChild(block);
  });
  const upkeep = (holes.upkeep || []).filter((q) => !q.absence);
  if (upkeep.length) {
    sec.appendChild(el('p', 'note', '圖的整理工作（研究 session 處理，逐條在 `python -m query.graph_walk`）：'
      + upkeep.map((q) => `${q.short} ${q.hit_n}`).join('、')));
  }
  (holes.upkeep || []).filter((q) => q.absence).forEach((q) => sec.appendChild(el('p', 'warn', `▲ ${q.short}：${q.absence.reason}`)));
  return sec;
}

async function renderGraph(focus) {
  markNav('graph');
  let payload;
  try {
    payload = await getJSON(`${API}/graph`);
  } catch (err) {
    renderStateError(err, '讀不到圖');
    return;
  }
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';
  const c = payload.counts || {};
  const kindLabels = payload.kind_labels || {};
  const zones = payload.zones || [];

  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.title || '圖'));
  app.appendChild(head);
  const tally = zones.map((z) => (z.kinds || []).map((k) => `${kindLabels[k] || k} ${(c.by_kind || {})[k] || 0}`).join('、'))
    .filter(Boolean).join('｜');
  app.appendChild(el('p', 'graph-tally', `${c.layers} 份讀圖：${tally}｜該重讀 ${c.needs_reread ?? '—'}`
    + `｜錢在變多嗎量得到 ${c.growth_measured} 層｜層說明 ${c.layer_notes ?? '—'} 份`));

  const controls = el('div', 'table-filter');
  const search = el('input');
  search.type = 'search';
  search.placeholder = '搜尋層或公司（例：InP、Coherent、3081）';
  search.setAttribute('aria-label', '搜尋圖');
  const shown = el('div', 'dim table-filter-count');
  controls.appendChild(search);
  controls.appendChild(shown);
  app.appendChild(controls);

  const cards = [];
  const sections = [];
  zones.forEach((zone) => {
    const sec = el('details', 'zone');
    sec.open = Boolean(zone.expanded);
    sec.appendChild(el('summary', 'zone-head', `${zone.label}（${(zone.layers || []).length}）`));
    const empty = el('p', 'note', '這一區沒有符合的層。');
    empty.hidden = true;
    sec.appendChild(empty);
    (zone.layers || []).forEach((layer) => {
      const card = layerCard(layer, zone.key);
      cards.push(card);
      sec.appendChild(card);
    });
    if (!(zone.layers || []).length) sec.appendChild(el('p', 'note', '現在 0 層。'));
    sections.push({ sec, empty, zone });
    app.appendChild(sec);
  });
  const apply = () => {
    const q = search.value.trim().toLowerCase();
    let visible = 0;
    cards.forEach((card) => {
      const hit = !q || card._haystack.includes(q);
      card.hidden = !hit;
      if (hit) visible += 1;
    });
    sections.forEach(({ sec, empty, zone }) => {
      const any = Array.from(sec.querySelectorAll('.layer-card')).some((card) => !card.hidden);
      empty.hidden = !q || any || !(zone.layers || []).length;
      if (q && any) sec.open = true;
    });
    shown.textContent = q ? `顯示 ${visible}／${cards.length} 層（藏起 ${cards.length - visible} 層，順序不變）` : `全部 ${cards.length} 層`;
  };
  search.addEventListener('input', apply);
  apply();

  app.appendChild(graphHoles(payload.holes || {}));

  const notes = payload.notes || {};
  const tail = el('section', 'panel');
  tail.appendChild(el('h2', null, '解讀前要知道'));
  const ol = el('ol', 'limits');
  (payload.limitations || []).forEach((text) => {
    const li = el('li');
    li.appendChild(mdInline(text));
    ol.appendChild(li);
  });
  if (ol.childElementCount) tail.appendChild(ol);
  [notes.companies, notes.growth, notes.order].filter(Boolean).forEach((text) => tail.appendChild(mdParagraph(text)));
  if ((payload.withdrawn || []).length) tail.appendChild(el('p', 'note', '有紀錄但已全部撤回的讀圖：' + payload.withdrawn.join('、')));
  const absences = payload.absences || {};
  [['structure_table', '坐在這一層的公司與需求鏈這次不印'], ['layer_notes', '層說明連結這次不印'],
    ['graph_walk', '研究缺口這次不印']].forEach(([key, effect]) => {
    if (absences[key]) tail.appendChild(el('p', 'warn', `▲ ${absences[key].reason}——${effect}（不是沒有）`));
  });
  if ((absences.unreadable_pages || []).length) {
    tail.appendChild(el('p', 'warn', `▲ 讀不到的個股頁 ${absences.unreadable_pages.length} 檔（它們的短名與狀態這次不印）：`
      + absences.unreadable_pages.join('、')));
  }
  app.appendChild(tail);
  app.appendChild(stateFooter(payload));

  const target = focus ? cards.find((card) => card.dataset.node === focus) : null;
  if (target) {
    const zone = target.closest('details.zone');
    if (zone) zone.open = true;
    const more = target.querySelector('details.layer-more');
    if (more) more.open = true;
    target.classList.add('layer-focus');
    target.scrollIntoView({ block: 'start' });
  } else {
    if (focus) app.insertBefore(el('p', 'warn', `▲ 圖上沒有 ${focus} 的現行讀圖（可能還沒讀、或已撤回）。`), app.firstChild);
    window.scrollTo(0, 0);
  }
}

/* 圖預測對錯表（Phase 5 Step 5.4）：每一份讀圖斷言一個機械的終局。判定只來自 supersede 鏈與互動判定的反證觸及；
   錯的分「當時已有反例」與「之後才出現」。只印不判、不排序（列序＝節點字典序、同節點按寫下時間）。 */
const PREDICTION_COLUMNS = [
  { title: '節點', cell: (row) => el('td', 'nowrap', row.unit === 'socket' ? `${row.node}［插槽］` : row.node) },
  { title: '讀法', cell: (row) => el('td', 'nowrap', row.kind) },
  { title: '寫下', cell: (row) => el('td', 'nowrap', row.created_on) },
  { title: '到期', cell: (row) => el('td', 'nowrap', row.expires) },
  { title: '終局', cell: (row, labels) => el('td', null, (labels.outcomes || {})[row.outcome] || row.outcome) },
  { title: '錯的種類', cell: (row, labels) => el('td', null, row.wrong_kind ? ((labels.wrong_kinds || {})[row.wrong_kind] || row.wrong_kind) : '—') },
  { title: '依據', cell: (row) => el('td', 'nowrap', row.basis || '—') },
];

function renderPredictions(table) {
  const sec = el('section', 'panel');
  sec.appendChild(el('h2', null, '圖預測對錯表：讀圖說的，後來對了嗎'));
  if (!table) {
    sec.appendChild(el('p', 'note', '這份 artifact 還沒有預測表——跑一次 `python -m webapp materialize --structure-readings` 產生（不是 0）。'));
    return sec;
  }
  if (table.absence) {
    sec.appendChild(el('p', 'warn', `▲ ${table.absence.reason}（${table.absence.kind}）——不是 0。`));
    return sec;
  }
  const c = table.counts || {};
  const wrongBy = (kind) => ['reversed', 'disproof_touched', 'retracted'].reduce((n, o) => n + ((c[o] || {})[kind] || 0), 0);
  sec.appendChild(kpiRow([
    { label: '對', value: String(c.held || 0), sub: '同讀法、圖有變（帶新來源）或已到期後重讀' },
    { label: '錯', value: String(table.wrong_total || 0),
      sub: `當時已有 ${wrongBy('already_available')}／之後才出現 ${wrongBy('emerged_later')}／未定日 ${wrongBy('undated')}` },
    { label: '現行', value: String(c.open || 0), sub: table.earliest_open_expiry ? `最早 ${table.earliest_open_expiry} 到期` : '—' },
    { label: '改寫／非斷言', value: `${c.rewritten || 0}／${c.non_assertion || 0}`, sub: '不算對錯' },
  ]));
  const labels = table.labels || {};
  const rows = table.rows || [];
  const wrap = el('div', 'table-wrap');
  const t = el('table', 'rank');
  const head = el('thead');
  const hr = el('tr');
  PREDICTION_COLUMNS.forEach((col) => hr.appendChild(th(col.title)));
  head.appendChild(hr);
  t.appendChild(head);
  const body = el('tbody');
  rows.forEach((row) => {
    const tr = el('tr');
    PREDICTION_COLUMNS.forEach((col) => tr.appendChild(col.cell(row, labels)));
    body.appendChild(tr);
  });
  t.appendChild(body);
  wrap.appendChild(t);
  sec.appendChild(wrap);
  if ((table.unreadable_nodes || []).length) {
    sec.appendChild(el('p', 'warn', `▲ ledger 有壞行的節點不在表內：${table.unreadable_nodes.map((n) => n.node).join('、')}`));
  }
  if (table.source_dates !== 'available') sec.appendChild(el('p', 'warn', '▲ SourceDoc 日期這次讀不到：錯的種類是「日期讀不到」，不是未定日。'));
  sec.appendChild(el('p', 'note', table.stale_note || ''));
  return sec;
}

/* ⚠ 2026-10-28：「在等什麼」頁（renderWatches／watchList／watchRow）拿掉——併進首頁（使用者照推薦：11 頁收成 5 頁）。
   各段去處：重看日→首頁卡片與「接下來兩週會揭曉」；停滯、fired 未消化、追源需處置→每日心跳 watch 那一行（短版不是 0 才印）；
   反證與確認條件→個股頁（敘事的，每條帶盯它的 watch 狀態）與讀圖頁（讀圖的）；還在等的總數、可主動輪詢、喚醒去處、醒來待檢
   是 agent 的佇列→`python -m engine_b.event_watch counters`／`semantic-queue`、drain。artifact 與 `/api/v1/watches` 照留
   （不是收起來，是拿掉畫面）。 */

/* 共用頁尾：只留「這份畫面多新」一行（2026-10-07 使用者：「App 是要給人看的…不需要給我看的…不是收起來 是拿掉」）。
   authority、新鮮度身分、content digest 與「這一頁不是什麼」清單照樣在 artifact 裡（查核用、`/api/v1/*` 讀得到），不印。
   過期時把規則一起印——那是唯一需要你知道的事。`extra` 給個別頁面補一小段（例：資產配置的行情更新狀態）。 */
function stateFooter(payload, extra) {
  const f = payload.freshness || {};
  const age = Number(f.age_hours);
  // 本地時間（看的人在哪就印哪裡的鐘點）；解析不了就照原字串印，不猜
  const stamp = new Date(f.generated_at);
  const two = (n) => String(n).padStart(2, '0');
  const local = Number.isNaN(stamp.getTime()) ? String(f.generated_at || '—')
    : `${stamp.getFullYear()}-${two(stamp.getMonth() + 1)}-${two(stamp.getDate())} ${two(stamp.getHours())}:${two(stamp.getMinutes())}`;
  const when = `這份畫面產生於 ${local}（${Number.isFinite(age) ? age.toFixed(1) + ' 小時前' : '時間不明'}）`;
  const stale = f.state === 'stale' ? `｜▲ 已過期：${f.rule || ''}` : '';
  return el('p', 'note state-footer', when + (extra ? '｜' + extra : '') + stale);
}

/* ---------- 部位與問責（positions state；照抄 outcome 腳本與 Decision Store，不重算） ----------
   ⚠ 這一頁最容易被讀錯：兩種報酬的錨點語意不同，而且**樣本效度必須先於數字**——
   反過來排版的話，一份有效 n 接近 1 的觀測會看起來像 N 個獨立驗證。 */

function returnCell(value) {
  const cell = el('td', 'nowrap');
  const text = fmtRatioPct(value, 1);
  if (text === null) { cell.textContent = '—'; return cell; }
  cell.textContent = (value > 0 ? '+' : '') + text;
  cell.classList.add(signClass(value));
  return cell;
}

/* 欄位名一律白話（2026-09-08 使用者：「錨點前／入圖以來／超額是啥意思」——要查表才懂的詞不當欄名）。 */
/* 兩條線（Phase 5 Step 5.2）：live＝我們真的買的、paper＝我們寫下判斷的。**分母分開**——壓成一張表就是 L12。
   每一格照抄 artifact，不重算、不比、不排序；空的那條印「還沒有列」，不印 0%。
   2026-10-07 使用者（「舊店…連你都不會看就也沒必要給我看了…不是收起來 是拿掉」）：history（舊店入圖日）與舊店的
   ①–⑤（舊 Decision Store 計數、入圖日 cohort 的聚合與逐檔、賭注收斂）不再印——artifact 照樣帶著，心跳與 outcome 腳本照讀。 */
const LANE_ORDER = ['live', 'paper'];
const LANE_TITLES = {
  live: 'live：我們真的買的（trade_log 的成交；起算＝成交價）',
  paper: 'paper：我們寫下判斷的（每檔第一份 v2 敘事那天；起算＝那天收盤）',
};

/* 多主題等權組 S1（2026-10-06）：每一列只跟自己所屬的組比；沒有值的列印「為什麼沒有」，不印 0、不印空白。
   種類與短標籤都由產生缺席的程式宣告、跟著資料走（`alpha.theme_cohort.cohort_absence`）——前端不維護第二份對照表（L16）；
   舊 artifact 沒帶標籤時照印種類字串。 */
function cohortExcessCell(row) {
  if (row.excess_theme_cohort !== null && row.excess_theme_cohort !== undefined) return returnCell(row.excess_theme_cohort);
  const absence = row.theme_cohort_absence || {};
  if (absence.kind) return el('td', 'note', `不比（${absence.label || absence.kind}）`);
  return returnCell(null);
}

const PAPER_LANE_COLUMNS = [
  { title: '標的', cell: (row, set) => companyCell({ ticker: row.ticker, company_id: row.company_id }, set) },
  { title: '寫下判斷那天', cell: (row) => el('td', 'nowrap', row.anchor_date || '—') },
  { title: '當時 → 現在的候選狀態', cell: (row) => el('td', 'nowrap', `${row.anchor_state || '—'} → ${row.current_state || '—'}`) },
  { title: '寫下前 30 天', cell: (row) => returnCell(row.pre_anchor_return) },
  { title: '寫下後到現在', cell: (row) => returnCell(row.absolute_return) },
  { title: '同期比 QQQ 多／少', cell: (row) => returnCell(row.excess_QQQ) },
  { title: '比自己所屬的主題等權組（排除本檔）', cell: (row) => cohortExcessCell(row) },
  { title: '最早點名它的來源', cell: (row) => el('td', null, row.first_named_by
      ? `${row.first_named_by.source}（${String(row.first_named_by.first_seen || '').slice(0, 10)}）`
      : (row.first_named_absence || '—')) },
];

const LIVE_LANE_COLUMNS = [
  { title: '標的', cell: (row, set) => companyCell({ ticker: row.ticker, company_id: row.company_id }, set) },
  { title: '成交代號', cell: (row) => el('td', 'nowrap', row.execution_symbol || '—') },
  { title: '成交日', cell: (row) => el('td', 'nowrap', row.anchor_date || '—') },
  { title: '成交價', cell: (row) => el('td', 'nowrap', fmtQuantity(row.anchor_raw, row.trade_currency) || '—') },
  { title: '現在或賣出', cell: (row) => el('td', 'nowrap', fmtQuantity(row.current_price, row.anchor_ccy) || '—') },
  { title: '成交後到現在', cell: (row) => returnCell(row.absolute_return) },
  { title: '同期比 QQQ 多／少', cell: (row) => returnCell(row.excess_QQQ) },
  { title: '比自己所屬的主題等權組（排除本檔）', cell: (row) => cohortExcessCell(row) },
  { title: '當時的收據', cell: (row) => el('td', null, (row.receipt && row.receipt.label) || '—') },
];

function laneSummaryText(entry) {
  const agg = entry.aggregate || {};
  const ex = entry.theme_cohort_excess || {};
  const pl = entry.power_law || {};
  const labels = ex.absent_labels || {};
  const absent = Object.entries(ex.absent || {}).map(([kind, tickers]) => `${labels[kind] || kind} ${tickers.length} 列`);
  return [`${entry.n} 列（算得出報酬 ${entry.measured}）`, `量測起始 ${entry.measurement_start || '—'}`,
    `等權 ${signedPct(agg.absolute)}`, `比 ${agg.benchmark || 'QQQ'} ${signedPct(agg.excess)}`,
    (ex.n ? `比自己所屬的組 ${signedPct(ex.mean)}（${ex.n}/${ex.of} 列）` : '比自己所屬的組：還沒有值')
      + (absent.length ? `（不比：${absent.join('、')}）` : ''),
    `曾達 2 倍 ${pl.reached_2x_ever ?? '—'}/${pl.n ?? '—'}（現價仍達 ${pl.reached_2x_now ?? '—'}）`].join('｜');
}

/* power-law 三量（D15；AGENTS「追蹤表印三個 power-law 統計量」）：原本只在舊店那一格印，舊店拿掉後跟著每條線走。
   最大單檔與其餘合計是恆等式的兩端（籃子總報酬 ＝ 最大單檔 ＋ 其餘），刻意不做除法；12／24 個月的分母是「已滿那麼久的檔數」，
   分母 0 印「分母還沒出現」，不印 0%（L12）。全部照抄 artifact。 */
function lanePowerLawText(entry) {
  const pl = entry.power_law || {};
  if (!pl.n) return '';
  const top = pl.top_contributor || {};
  const mat = pl.maturity || {};
  const share = ['12m', '24m'].map((k) => {
    const m = mat[k] || {};
    return m.matured ? `${k} ${m.reached_2x}/${m.matured} 檔（${fmtRatioPct(m.share, 0) || '—'}）` : `${k} 分母還沒出現`;
  }).join('、');
  return [`power-law 三量：籃子總報酬 ${signedPct(pl.basket_total_return)}`,
    `最大單檔 ${top.ticker || '—'} 貢獻 ${signedPct(top.contribution)}（該檔 ${signedPct(top.absolute_return)}）`
      + `＋其餘 ${top.rest_n ?? '—'} 檔合計 ${signedPct(top.rest_contribution)}`,
    `達 2 倍的比例 ${share}`].join('｜');
}

function renderPositionLanes(payload, detailSet) {
  const sec = el('section', 'panel callout');
  sec.appendChild(el('h2', null, '兩條線：我們真的買的、我們寫下判斷的'));
  const lanes = payload.lanes;
  if (!lanes) {
    sec.appendChild(el('p', 'note', '這份 artifact 還沒有三條 lane——跑一次 `python -m webapp materialize --positions` 產生（不是 0）。'));
    return sec;
  }
  sec.appendChild(mdParagraph((payload.notes || {}).lanes || ''));
  const cohort = payload.theme_cohort || {};
  if (cohort.absence) {
    sec.appendChild(el('p', 'warn', `主題等權組：${cohort.absence.reason}（${cohort.absence.kind}）——比主題等權組那一格全部缺席，不是 0。`));
  } else if (!Array.isArray(cohort.cohorts)) {
    sec.appendChild(el('p', 'note', '這份 artifact 早於「每一列只跟自己所屬的組比」——跑一次 `python -m webapp materialize --positions` 重算（不是 0）。'));
  } else {
    sec.appendChild(el('p', 'note', `主題等權組 ${cohort.cohorts.length} 組：每一列只跟自己所屬的組比（排除本檔）；不是組員的列印「不比」，不借別的題材的組。`));
    // 組的 id（tc_…雜湊）不印——那是給程式對帳用的；人讀題材名就夠（2026-10-07：「不需要給我看的…拿掉」）
    cohort.cohorts.forEach((entry) => {
      const missing = entry.missing_members || [];
      sec.appendChild(el('p', 'note', `・${entry.theme}（${entry.members_total} 檔，${entry.decided_on} 定）`
        + `｜取不到價的成員 ${missing.length}${missing.length ? '：' + missing.join('、') : ''}`));
    });
  }
  const budget = payload.price_budget || {};
  if ((budget.truncated || []).length) {
    sec.appendChild(el('p', 'warn', `取價超過上限 ${budget.cap} 檔，截掉 ${budget.truncated.length} 檔：${budget.truncated.join('、')}——那幾格是缺席，不是沒有價。`));
  }
  const barsNote = closingBarsNote(budget);
  if (barsNote) sec.appendChild(barsNote);
  for (const lane of LANE_ORDER) {
    const entry = lanes[lane] || {};
    sec.appendChild(el('h3', null, LANE_TITLES[lane]));
    if (entry.absence) {
      sec.appendChild(el('p', 'warn', `▲ ${entry.absence.reason}（${entry.absence.kind}）——不是 0，也不是「還沒有列」。`));
      continue;
    }
    if (lane === 'live') {
      sec.appendChild(el('p', 'note', `beta 事件 ${entry.beta_events ?? '—'} 不進 lane。`
        + ((entry.unmatched_sells || []).length ? `配對不到的賣出：${entry.unmatched_sells.join('；')}` : '')
        + ((entry.problems || []).length ? `▲ ${entry.problems.join('；')}` : '')));
    }
    if (!entry.n) {
      sec.appendChild(el('p', 'note', entry.empty_text || '還沒有列'));
      continue;
    }
    sec.appendChild(el('p', null, laneSummaryText(entry)));
    const powerLaw = lanePowerLawText(entry);
    if (powerLaw) sec.appendChild(el('p', 'note', powerLaw));
    if (lane === 'paper') sec.appendChild(rankTable(entry.rows || [], PAPER_LANE_COLUMNS, detailSet));
    if (lane === 'live') sec.appendChild(rankTable(entry.rows || [], LIVE_LANE_COLUMNS, detailSet));
    for (const bias of ((entry.power_law || {}).known_biases || []).slice(-1)) {
      sec.appendChild(el('p', 'note', `▲ ${bias}`));
    }
  }
  return sec;
}

async function renderPositions() {
  markNav('positions');
  let payload;
  try {
    payload = await getJSON(`${API}/positions`);
  } catch (err) {
    renderStateError(err, '讀不到部位與問責');
    return;
  }
  const detailSet = new Set(payload.analyst_view_tickers || []);
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';

  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.title));
  const badges = el('div', 'badges');
  if (payload.freshness && payload.freshness.state === 'stale') {
    const b = el('span', 'badge badge-stale', 'stale'); b.title = payload.freshness.rule; badges.appendChild(b);
  }
  head.appendChild(badges);
  app.appendChild(head);

  // 兩條線（Phase 5）：我們真的買的、我們寫下判斷的——分母分開；樣本數與量測起始日在每條線的第一行，先於報酬（樣本效度先於數字）。
  app.appendChild(renderPositionLanes(payload, detailSet));

  // 2026-10-07 使用者（「舊店…連你都不會看就也沒必要給我看了…不是收起來 是拿掉」）：舊店的 ①–⑤（舊 Decision Store 計數、
  // 入圖日 cohort 的樣本效度／聚合／逐檔、賭注收斂）不再印。artifact 照樣帶著，心跳與 outcome 腳本照讀；power-law 三量跟著上面兩條線走。
  // 圖自己的預測也要量（AGENTS 量測）：圖預測對錯表 2026-10-28 隨讀圖頁併進圖頁時搬來這裡——它答的正是這一頁的問題。
  try {
    const readings = await getJSON(`${API}/structure-readings`);
    app.appendChild(renderPredictions(readings.predictions));
  } catch (err) {
    app.appendChild(el('p', 'warn', '▲ 圖預測對錯表這次讀不到（structure_readings artifact）——不是 0。'));
  }
  app.appendChild(stateFooter(payload));
  window.scrollTo(0, 0);
}

/* ⚠ 2026-10-28：「候選板」頁（renderCandidates／candidateRow 與它的三個常數）拿掉——併進首頁（同上）。
   各段去處：各組檔數（0 也印）與最老滯留→首頁最下面那一行；各組逐列→首頁卡片＋個股頁候選狀態那行（理由、在等什麼、哪天醒）；
   沒有敘事、不上板→首頁兩個收合組；敘事該重寫→卡片上的「敘事該重寫 N」；持股解析不到→每日短版；三題與四盞燈的 rollup、
   邊緣判定計數→心跳段 2／段 4（同一份 artifact）。artifact 與 `/api/v1/candidates` 照留。 */

/* ---------- 路由 ---------- */

/* ---------- 帳號計分表（account_scorecard state；Phase 5 Step 5.5） ----------
   一格一個數或一個「為什麼沒有」，原文照抄；不排序帳號（照登記表 source_id 順序）、不加總、不換算——
   百分比的 ×100 只是排版。三個基準（QQQ／SOXX／主題等權組）並排，**不得只印一個**（單邊上漲偏差）。 */

const SCORECARD_BENCHMARK_LABELS = { QQQ: 'QQQ', SOXX: 'SOXX', theme_cohort: '主題等權組（排除本檔）' };

function scorecardCell(cell) {
  if (!cell) return '—';
  if (cell.value === null || cell.value === undefined) {
    const bits = [`沒有值（${cell.absence_kind || '—'}）`];
    if (cell.reason) bits.push(cell.reason);
    if (cell.revisit_after) bits.push(`${cell.revisit_after} 回來看`);
    return bits.join('——');
  }
  return `${fmtPercent(cell.value)}（n=${cell.n}）`;
}

/* 組那一格的分母為什麼比 QQQ／SOXX 少：照抄該格的 filter reasons（INV-3），標籤跟著 artifact 走（`theme_cohort.absence_labels`）。
   R2 2026-10-06 C1：先前頁首寫「不是組員的點名列在每格的濾掉理由裡」，但沒有任何一格印出來——那句話是假的。 */
function scorecardFilterLine(filter, labels) {
  const reasons = Object.entries((filter || {}).reasons || {});
  if (!reasons.length) return null;
  return `濾掉 ${filter.filtered}／${filter.input} 則：` + reasons.map(([k, n]) => `${labels[k] || k} ${n}`).join('、');
}

function scorecardExcessTable(account, payload) {
  const box = el('div', 'table-view');
  const table = el('table');
  const head = el('thead');
  const hr = el('tr');
  ['持有期', '比較基準', '全部點名', '每檔只算最早一次'].forEach((t) => hr.appendChild(el('th', null, t)));
  head.appendChild(hr);
  table.appendChild(head);
  const body = el('tbody');
  const all = (account.metrics || {}).excess_returns || {};
  const first = ((account.metrics_first_call_per_symbol || {}).excess_returns) || {};
  const allFilters = (account.metrics || {}).excess_return_filters || {};
  const firstFilters = ((account.metrics_first_call_per_symbol || {}).excess_return_filters) || {};
  const labels = (payload.theme_cohort || {}).absence_labels || {};
  const benches = [...(payload.benchmarks || []), 'theme_cohort'];
  (payload.horizons_days || []).forEach((h) => {
    benches.forEach((b) => {
      const key = `excess_${h}d_vs_${b}`;
      if (!(key in all)) return;          // 早於 5.5 的 artifact 沒有主題等權組那兩格——不補、不寫 0
      const tr = el('tr');
      [`點名後 ${h} 天`, SCORECARD_BENCHMARK_LABELS[b] || b].forEach((t) => tr.appendChild(el('td', null, t)));
      [[all[key], allFilters[key]], [first[key], firstFilters[key]]].forEach(([cell, filter]) => {
        const td = el('td', null, scorecardCell(cell));
        const line = b === 'theme_cohort' ? scorecardFilterLine(filter, labels) : null;
        if (line) td.appendChild(el('div', 'note', line));
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
  });
  table.appendChild(body);
  box.appendChild(stackTable(table));
  return box;
}

async function renderScorecard() {
  markNav('account-scorecard');
  let payload;
  try {
    payload = await getJSON(`${API}/account-scorecard`);
  } catch (err) {
    renderStateError(err, '讀不到帳號計分表');
    return;
  }
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';

  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.title));
  const badges = el('div', 'badges');
  if (payload.freshness && payload.freshness.state === 'stale') {
    const b = el('span', 'badge badge-stale', 'stale'); b.title = payload.freshness.rule; badges.appendChild(b);
  }
  head.appendChild(badges);
  app.appendChild(head);

  const sec0 = el('section', 'panel callout');
  sec0.appendChild(el('h2', null, '這張表量什麼'));
  sec0.appendChild(el('p', 'note', payload.this_is_not || ''));
  const counts = payload.tier_counts || {};
  sec0.appendChild(el('p', null, `as-of ${payload.as_of}｜tier 分佈：`
    + Object.keys(counts).map((t) => `${t} ${counts[t]}`).join('／')));
  const cohort = payload.theme_cohort;
  if (!cohort) {
    sec0.appendChild(el('p', 'warn', '主題等權組基準：這份 artifact 早於這一格——跑 `python -m webapp materialize --scorecard` 重算（不是 0）。'));
  } else if (cohort.absence) {
    sec0.appendChild(el('p', 'warn', `主題等權組基準：無（${cohort.absence.kind}）——${cohort.absence.reason}。對組的那幾格全部缺席，不是 0。`));
  } else if (!Array.isArray(cohort.cohorts)) {
    sec0.appendChild(el('p', 'warn', '主題等權組基準：這份 artifact 早於「每則點名只跟自己所屬的組比」——跑 `python -m webapp materialize --scorecard` 重算（不是 0）。'));
  } else {
    sec0.appendChild(el('p', 'note', `主題等權組基準 ${cohort.cohorts.length} 組：每則點名只跟自己所屬的組比；不是組員的點名不比——每個帳號表格裡「主題等權組」那幾格下面，印出被濾掉幾則、各是什麼理由。`));
    cohort.cohorts.forEach((entry) => {
      const missing = entry.missing || [];
      sec0.appendChild(el('p', 'note', `・${entry.cohort_id}（${entry.theme}，決定於 ${entry.decided_on}）`
        + `｜成員 ${entry.members_total}、取得到價 ${entry.members_priced}｜缺價：${missing.length ? missing.join('、') : '—'}`));
    });
  }
  const budget = payload.price_budget || {};
  sec0.appendChild(el('p', 'note', `取價：要 ${budget.requested ?? '—'} 檔、抓 ${budget.fetched ?? '—'} 檔（上限 ${budget.cap ?? '—'}）`
    + ((budget.theme_cohort_added || []).length ? `｜為主題等權組多抓 ${budget.theme_cohort_added.join('、')}` : '')));
  if ((budget.truncated || []).length) {
    sec0.appendChild(el('p', 'warn', `取價超過上限，截掉 ${budget.truncated.length} 檔：${budget.truncated.join('、')}——那幾格是缺席，不是沒有價。`));
  }
  const barsNote = closingBarsNote(budget);
  if (barsNote) sec0.appendChild(barsNote);
  if (payload.price_note) sec0.appendChild(el('p', 'warn', '▲ ' + payload.price_note));
  app.appendChild(sec0);

  (payload.accounts || []).forEach((account) => {
    const sec = el('section', 'panel');
    sec.appendChild(el('h2', null, `${account.harvest_key}｜tier ${account.tier}（pq1 加分 +${account.pq1_priority_bonus}）`));
    const f = account.lead_filter || {};
    sec.appendChild(el('p', null, `量測期間 ${account.measurement_start || '—'} → ${account.measurement_end || '—'}｜`
      + `具名點名 ${account.named_calls} 則／${account.distinct_symbols} 檔（貼文 ${f.input ?? '—'} 則，可計分 ${f.accepted ?? '—'}、濾掉 ${f.filtered ?? '—'}）`));
    const reasons = f.reasons || {};
    if (Object.keys(reasons).length) {
      sec.appendChild(el('p', 'note', '濾掉的理由：' + Object.keys(reasons).map((r) => `${r} ${reasons[r]}`).join('｜')));
    }
    sec.appendChild(scorecardExcessTable(account, payload));
    const m = account.metrics || {};
    const firstM = account.metrics_first_call_per_symbol || {};
    const list = el('ul', 'weak');
    [
      [`點名前 ${payload.lookback_days} 天漲幅中位數`, m.prior_30d_move, firstM.prior_30d_move],
      ['追源成功率', m.trace_success_rate, null],
      ['假設命中率', m.hypothesis_hit_rate, null],
      ['no-go 率', m.no_go_rate, null],
    ].forEach(([label, cell, firstCell]) => {
      const li = el('li');
      li.appendChild(el('div', null, `${label}：${scorecardCell(cell)}`));
      if (firstCell) li.appendChild(el('span', 'rule', `每檔只算最早一次：${scorecardCell(firstCell)}`));
      list.appendChild(li);
    });
    sec.appendChild(list);
    app.appendChild(sec);
  });

  const secB = el('section', 'panel');
  secB.appendChild(el('h2', null, '已知偏差（不是註腳，是這張表的一部分）'));
  const biases = el('ul', 'weak');
  (payload.known_biases || []).forEach((b) => biases.appendChild(el('li', null, b)));
  secB.appendChild(biases);
  app.appendChild(secB);
}

/* ---------- 層說明（layer_notes state；個股頁 plan S4b）：純文字閱讀頁 ----------
   照印 ledger 全文（三段依 ①②③ 的固定順序）、每個出處的兩種等級（層說明寫的「誰說的」與文件自宣告，並列不合併）、
   每條主張的 watch 狀態、哪幾頁連過來。**不做版面、不畫圖**（版面與示意圖在 S5）；列序是節點 id 的字母序，不是名次。 */

/** 研究 session 寫的 markdown，照原文一行一行印：`##` 變標題、`|` 開頭的連續行變表格、其餘保留縮排與換行。
    不改一個字——強調與程式碼記號交給 `mdInline`。 */
function plainText(text) {
  const box = el('div', 'plain-text');
  const lines = String(text || '').split('\n');
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    const sub = line.match(/^-#\s+(.*)$/);
    if (sub) {
      // Discord 的小字（`-# …`；2026-10-28 起短版的說明都用它）：淡色小一號，字一個不改
      const row = el('div', 'pt-line pt-sub');
      row.appendChild(inlineWithCites(sub[1]));
      box.appendChild(row);
    } else if (heading) {
      const h = el(heading[1].length <= 2 ? 'h3' : 'h4');
      h.appendChild(mdInline(heading[2]));
      box.appendChild(h);
    } else if (line.trim().startsWith('|')) {
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) { rows.push(lines[i]); i += 1; }
      i -= 1;
      box.appendChild(markdownTable(rows));
    } else {
      const row = el('div', line.trim() ? 'pt-line' : 'pt-line pt-blank');
      row.appendChild(inlineWithCites(line));
      box.appendChild(row);
    }
  }
  return box;
}

/** 正文裡的行內出處（〔一手·供應商自述｜`檔名` p.82〕）印成淡色小字——**字一個不改**，只讓正文先被讀到。 */
function inlineWithCites(text) {
  const frag = document.createDocumentFragment();
  String(text || '').split(/(〔[^〕]*〕)/).forEach((part) => {
    if (!part) return;
    if (part.startsWith('〔') && part.endsWith('〕')) {
      const span = el('span', 'cite-inline');
      span.appendChild(mdInline(part));
      frag.appendChild(span);
    } else {
      frag.appendChild(mdInline(part));
    }
  });
  return frag;
}

/** markdown 表格 → 表格（第二行的 `|---|` 分隔線略過；格子文字一個字不改）。手機上每列變一張小卡（`stackTable`）。 */
function markdownTable(rows) {
  const cells = (row) => row.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
  const wrap = el('div', 'table-wrap');
  const table = el('table', 'rank pt-table');
  const head = el('thead');
  const body = el('tbody');
  rows.forEach((row, index) => {
    const parts = cells(row);
    if (parts.every((c) => /^:?-{3,}:?$/.test(c))) return;
    const tr = el('tr');
    parts.forEach((c) => {
      const cell = el(index === 0 ? 'th' : 'td');
      cell.appendChild(inlineWithCites(c));
      tr.appendChild(cell);
    });
    (index === 0 ? head : body).appendChild(tr);
  });
  table.appendChild(head);
  table.appendChild(body);
  wrap.appendChild(stackTable(table));
  return wrap;
}

/** 窄螢幕（手機）時每一列變成一張小卡、每一格上面印欄名——欄名照抄表頭，不另寫一份。
    寬螢幕照舊是表格。給 `thead` 第一列的欄名，`tbody` 每一格掛 `data-label`。 */
function stackTable(table) {
  const headers = Array.from(table.querySelectorAll('thead tr:first-child th')).map((th) => th.textContent.trim());
  table.querySelectorAll('tbody tr').forEach((tr) => {
    Array.from(tr.children).forEach((cell, i) => { if (headers[i]) cell.setAttribute('data-label', headers[i]); });
  });
  table.classList.add('stack-table');
  return table;
}

/** 出處旁的「文件自宣告」：文件自己帶的等級（附哪裡寫的）與檔頭的宣告段（逐字）；都沒有就印缺席的那一句。 */
function declaredBlock(declared) {
  const box = el('div', 'declared');
  if (declared.absence) {
    box.appendChild(el('span', 'rule', '文件自宣告：' + declared.absence.label));
    return box;
  }
  const tiers = (declared.tiers || []).map((t) => `tier ${t.tier}（${t.from}）`);
  if (tiers.length) box.appendChild(el('span', 'rule', '文件自宣告的等級：' + tiers.join('；')));
  (declared.lines || []).forEach((text) => {
    const quote = el('div', 'verbatim pt-decl', text);
    quote.appendChild(el('div', 'src', '文件檔頭的宣告（逐字）'));
    box.appendChild(quote);
  });
  return box;
}

function citationList(citations) {
  const list = el('ul', 'weak');
  (citations || []).forEach((c) => {
    const li = el('li');
    const head = el('div');
    head.appendChild(el('span', 'badge badge-evidence', '層說明寫：' + c.evidence_label));
    head.appendChild(document.createTextNode(' '));
    head.appendChild(el('code', null, c.ref || '（沒有出處：' + c.evidence_label + '）'));
    li.appendChild(head);
    if (c.quote) li.appendChild(el('div', 'verbatim', c.quote));
    if (c.declared) li.appendChild(declaredBlock(c.declared));
    list.appendChild(li);
  });
  return list;
}

function companyName(payload, id) {
  const label = (payload.company_labels || {})[id];
  return label ? `${label}（${id}）` : id;
}

function citedByBlock(payload, row) {
  const sec = el('section', 'panel');
  sec.appendChild(el('h2', null, '哪幾頁連過來（由圖推：公司對這個節點有供貨或開發邊）'));
  const cited = row.cited_by || {};
  if (cited.absence) {
    sec.appendChild(el('p', 'warn', `▲ ${cited.absence.reason}（${cited.absence.kind}）`));
    return sec;
  }
  const pages = cited.pages || [];
  const p = el('p', null, pages.length ? `${pages.length} 頁：` : '0 頁');
  pages.forEach((page, i) => {
    if (i) p.appendChild(document.createTextNode('、'));
    const link = el('a', null, page.ticker);
    link.href = '#/' + encodeURIComponent(page.ticker);
    p.appendChild(link);
    if (page.label) p.appendChild(el('span', 'dim', `（${page.label}）`));
  });
  sec.appendChild(p);
  (cited.without_page || []).forEach((w) => {
    sec.appendChild(el('p', 'note', `也坐在這一層、但沒有個股頁：${companyName(payload, w.company_id)}——${w.reason}`));
  });
  return sec;
}

function claimList(payload, claims) {
  const list = el('ul', 'weak');
  claims.forEach((c) => {
    const li = el('li');
    li.appendChild(mdParagraph(`${c.n}. ${c.claim}`, 'pt-claim'));
    li.appendChild(el('span', 'rule', `狀態：${c.state_label}`
      + (c.watch_id ? `｜watch ${c.watch_id}（${c.watch_status}）` : '') + (c.watch_expires ? `｜到期 ${c.watch_expires}` : '')));
    li.appendChild(el('span', 'rule', '什麼會讓它變假／什麼事件要叫醒：' + c.condition));
    li.appendChild(el('span', 'rule', `核查頻率：${c.check_frequency}｜觸發後 48 小時：${c.action_48h}`));
    li.appendChild(el('span', 'rule', `證據等級：${c.evidence_label}｜盯的公司：`
      + (c.entities || []).map((id) => companyName(payload, id)).join('、')));
    li.appendChild(citationList(c.citations));
    list.appendChild(li);
  });
  return list;
}

async function loadLayerNotes() {
  try {
    return await getJSON(`${API}/layer-notes`);
  } catch (err) {
    renderStateError(err, '讀不到層說明');
    return null;
  }
}

async function renderLayerNote(node) {
  // ⚠ 2026-10-28：層說明清單頁併進「圖」頁（有層說明的層卡片上有「層說明」連結）；這一頁只剩單一層的閱讀頁。
  markNav('graph', '這一層在供應鏈裡做什麼、客戶為什麼選這家、什麼會讓它被換掉？');
  const payload = await loadLayerNotes();
  if (!payload) return;
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';
  const back = el('a', 'back', '← 圖（這一層）');
  back.href = '#/graph/' + encodeURIComponent(node);
  app.appendChild(back);
  const row = (payload.rows || []).find((r) => r.node === node);
  if (!row) {
    const box = el('div', 'error');
    box.appendChild(el('h2', null, `${node} 沒有現行的層說明`));
    box.appendChild(el('p', 'note', (payload.withdrawn || []).includes(node)
      ? '它有紀錄，但最新一筆是撤回——撤回後沒有現行的那一份（舊版不復活）。'
      : '這個節點還沒寫層說明，或節點 id 打錯了。'));
    app.appendChild(box);
    return;
  }
  // 2026-10-07 使用者回饋（「點進去看不懂、排版也歪」）：正文先、關於這份的資料放最後；行內出處淡化、每段出處清單摺起來。
  // 版面與示意圖（每塊一句讀法、鏈上的位置圖）仍在 S5——這一版只是讓手機讀得下去。
  const units = (payload.labels || {}).units || {};
  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, row.title));
  const pages = ((row.cited_by || {}).pages || []);
  const sub = el('div', 'company');
  sub.appendChild(document.createTextNode(`${units[row.unit] || row.unit}｜`));
  if (pages.length) {
    sub.appendChild(document.createTextNode('坐在這一層的個股頁：'));
    pages.forEach((page, i) => {
      if (i) sub.appendChild(document.createTextNode('、'));
      const link = el('a', null, page.ticker);
      link.href = '#/' + encodeURIComponent(page.ticker);
      sub.appendChild(link);
    });
  } else {
    sub.appendChild(document.createTextNode('還沒有個股頁連過來（原因見最下面）'));
  }
  head.appendChild(sub);
  // 寫於／重讀日一行（原本「關於這一份」一整塊，節點 id 與紀錄 id 不印——網址就是節點、紀錄 id 給互動 session 查）
  head.appendChild(el('div', 'dim', `寫於 ${String(row.created_at || '').slice(0, 10)}`
    + `${row.versions > 1 ? `（第 ${row.versions} 版）` : ''}｜重讀日 ${row.expires || '—'}：${row.reread_reason || '—'}`));
  app.appendChild(head);
  (row.reread || []).forEach((r) => app.appendChild(el('p', 'warn', '▲ 該重讀：' + r)));
  // 技術示意圖（2026-10-08，個股頁 S5b）：這一層在整條鏈的哪裡、光／電／熱怎麼走——放正文之前。
  (row.diagrams || []).forEach((d) => {
    const sec = el('section', 'panel layer-section');
    sec.appendChild(diagramFigure(d, [row.node], '這一層'));
    app.appendChild(sec);
  });

  (row.sections || []).forEach((section) => {
    const sec = el('section', 'panel layer-section');
    // 正文自己有段標題（`## ①…`）就不重複印；沒有才補契約的段名（段的順序由契約決定，materialize 已排好）
    if (!/^\s*#/.test(section.text || '')) sec.appendChild(el('h2', null, section.label));
    sec.appendChild(plainText(section.text));
    app.appendChild(sec);
  });

  const secC = el('section', 'panel');
  secC.appendChild(el('h2', null, '④ 主張：每條寫下即登記 watch'));
  if ((row.claims || []).length) secC.appendChild(claimList(payload, row.claims));
  else secC.appendChild(el('p', 'note', '這一份沒有自己的主張——牽涉個股的條件掛在那幾檔敘事的反證上（看個股頁）。'));
  app.appendChild(secC);

  // 出處（2026-10-07 使用者：「不是收起來 是拿掉」——原本每段一個摺疊）：正文裡的行內出處已經淡化在原位；
  // 這裡一次列完、不摺：每個出處並列「層說明寫」的等級與文件自己的宣告（第三方轉錄、AI 摘要、改寫過的節錄在這裡現形）。
  const cited = (row.sections || []).filter((s) => (s.citations || []).length);
  if (cited.length) {
    const secR = el('section', 'panel');
    secR.appendChild(el('h2', null, `出處（${cited.reduce((n, s) => n + s.citations.length, 0)} 個）`));
    secR.appendChild(el('p', 'note', '「層說明寫」看的是誰說的；「文件自宣告」是文件自己帶的等級與檔頭說明，沒有就印「文件沒宣告」。'));
    cited.forEach((s) => {
      secR.appendChild(el('div', 'group-title', s.label));
      secR.appendChild(citationList(s.citations));
    });
    app.appendChild(secR);
  }
  app.appendChild(citedByBlock(payload, row));

  app.appendChild(stateFooter(payload));
  window.scrollTo(0, 0);
}

/* ---------- 每日（daily state；2026-10-07 使用者指示：心跳太雜） ----------
   Discord 那一則（lead／市場大事／待你決定／狀態與健康度／下一次研究）照抄——daily ⑱ 寫的檔。
   完整心跳五段不印在這裡（同日使用者：「不需要給我看的…不是收起來 是拿掉」）：它照樣每天寫進 heartbeat 目錄，
   給互動 session 查細節；你要看的基本狀態已經在這一則的 ④。 */
async function renderDaily() {
  markNav('daily');
  let payload;
  try {
    payload = await getJSON(`${API}/daily`);
  } catch (err) {
    renderStateError(err, '讀不到每日');
    return;
  }
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';
  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.title));
  const badges = el('div', 'badges');
  if (payload.freshness && payload.freshness.state === 'stale') {
    const b = el('span', 'badge badge-stale', 'stale'); b.title = payload.freshness.rule; badges.appendChild(b);
  }
  head.appendChild(badges);
  app.appendChild(head);

  const brief = payload.brief || {};
  const sec = el('section', 'panel daily-brief');
  if (brief.markdown) sec.appendChild(plainText(brief.markdown));
  else sec.appendChild(el('p', 'warn', `▲ ${(brief.absence || {}).reason || '短版今天沒寫出來'}`));
  app.appendChild(sec);

  app.appendChild(stateFooter(payload));
  window.scrollTo(0, 0);
}

async function route() {
  const checkWidth = selfCheckWidth();
  if (checkWidth) document.documentElement.style.width = `${checkWidth}px`;   // 只在 ?selfcheck=1&w= 量測時
  const hash = window.location.hash || '#/';
  const target = decodeURIComponent(hash.replace(/^#\/?/, ''));
  app.textContent = '';
  app.appendChild(el('p', 'loading', '載入中…'));
  checkCodeFreshness();  // 不 await：橫幅與頁面各自載入，健康檢查慢不擋畫面
  try {
    if (!VOCAB) {
      const meta = await getJSON(`${API}/meta`);
      VOCAB = meta.vocabularies || {};
    }
    // 小寫或含連字號的路徑是保留字：ticker 一律大寫（store 的 slug 規則），所以不會撞到真實代碼。
    // ⚠ 2026-10-28：讀圖、走圖、層說明、結構表併成「圖」（`#/graph`；`#/graph/<node>` 打開那一層）；四個舊路徑落到圖頁並說一句。
    if (target === 'graph') await renderGraph();
    else if (target.startsWith('graph/')) await renderGraph(target.slice('graph/'.length));
    else if (['structure-table', 'graph-walk', 'structure-readings', 'layer-notes'].includes(target)) {
      await renderGraph();
      app.insertBefore(el('p', 'note', '「讀圖」「走圖」「層說明」「結構表」已併進這一頁：每一層讀成什麼、坐著誰、錢在不在變多都在層卡片上，'
        + '還沒讀的地方在下面。'), app.firstChild);
    }
    else if (target === 'beta') await renderBeta();
    else if (target === 'positions') await renderPositions();
    // ⚠ 2026-10-28：`#/watches`（在等什麼）與 `#/candidates`（候選板）併進首頁；舊連結落到首頁並說一句，不落到「讀不到判讀」。
    else if (target === 'watches' || target === 'candidates') {
      await renderList();
      app.insertBefore(el('p', 'note',
        '「候選板」與「在等什麼」已併進這一頁：各組檔數在最下面，重看日在卡片上與最上面的兩週日曆。'), app.firstChild);
    }
    // 2026-10-02（Phase 5 Step 5.5）：帳號計分表頁——心跳段 5 一直寫「完整表在 APP」，這一頁之前其實不存在。
    else if (target === 'account-scorecard') await renderScorecard();
    // 2026-10-07（個股頁 plan S4b）：層說明。`layer/` 帶斜線與小寫，不會撞到 ticker（ticker 一律大寫、不含斜線）。
    else if (target === 'daily') await renderDaily();
    else if (target.startsWith('layer/')) await renderLayerNote(target.slice('layer/'.length));
    // 2026-10-28：首頁「依層」。小寫帶連字號，不會撞到 ticker（ticker 一律大寫）。
    else if (target === 'by-layer') await renderList('layer');
    else if (target) await renderDetail(target);
    else await renderList();
    if (/[?&]selfcheck=1\b/.test(window.location.search)) setTimeout(selfCheck, 0);
  } catch (err) {
    app.textContent = '';
    const box = el('div', 'error');
    box.appendChild(el('h2', null, '無法載入'));
    // 讀不到判讀與頁面程式自己出錯是兩件事（L12）：伺服器回了錯（getJSON 帶 status）才是「讀不到」；其他照實印錯誤，
    // 不說成沒 materialize（2026-10-08：新圖表的程式錯被這一句蓋成「讀不到判讀」）
    const fromServer = Boolean(err && err.status);
    box.appendChild(el('p', null, fromServer ? 'APP 讀不到已 materialize 的判讀。' : '頁面程式出錯了（判讀本身讀得到）。'));
    if (fromServer) {
      const p = el('p', 'note');
      p.appendChild(document.createTextNode('請在本機跑：'));
      p.appendChild(el('code', null, 'python -m webapp materialize <TICKER>'));
      box.appendChild(p);
    }
    box.appendChild(el('p', 'note', `錯誤：${String((err && (err.stack || err.message)) || err).slice(0, 600)}`));
    app.appendChild(box);
  }
}

/** 個股頁 S5c 的機械量測（只在網址帶 `?selfcheck=1` 時跑；唯讀、不連網、不寫任何東西）：
 *  ①頁面橫向溢出（文件寬度超過視窗幾 px；逐一列出右緣超出視窗、又不在自己可捲動的容器裡的元素）
 *  ②圖上的字互相重疊的對數（schema v1.0 規則 9：0 才算過）。結果寫進 `#selfcheck`，headless 瀏覽器的 DOM 傾印讀得到。 */
function selfCheckWidth() {
  const m = /[?&]selfcheck=1\b.*?[?&]w=(\d{3,4})\b/.exec(window.location.search);
  return m ? Number(m[1]) : null;
}

function selfCheck() {
  // headless 瀏覽器的視窗最小約 496px：要量 390px 就用 `&w=390` 把根元素限寬（route 開頭套用），右緣跟 w 比。
  // 640px 以下的手機斷點在 390 與 496 都成立，限寬量到的就是手機版面。
  const vw = selfCheckWidth() || window.innerWidth;
  const doc = document.documentElement;
  // `&open=1`：先把每個展開打開再量（塊底下的論證與數字也要在 390px 不溢出、不疊字）。
  if (/[?&]open=1\b/.test(window.location.search)) app.querySelectorAll('details').forEach((d) => { d.open = true; });
  const offenders = [];
  const scrollsX = (node) => {
    for (let p = node.parentElement; p && p !== document.body; p = p.parentElement) {
      const ox = getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') return true;
    }
    return false;
  };
  app.querySelectorAll('*').forEach((node) => {
    const r = node.getBoundingClientRect();
    if (r.width > 0 && r.right > vw + 0.5 && !scrollsX(node)) {
      offenders.push({ el: node.tagName.toLowerCase() + (node.className && typeof node.className === 'string' ? '.' + node.className.split(' ').join('.') : ''),
        right: Math.round(r.right), text: (node.textContent || '').trim().slice(0, 40) });
    }
  });
  let overlaps = 0;
  const details = [];
  app.querySelectorAll('svg').forEach((svg) => {
    const boxes = Array.from(svg.querySelectorAll('text')).map((t) => ({ t: t.textContent, r: t.getBoundingClientRect() }));
    for (let i = 0; i < boxes.length; i += 1) {
      for (let j = i + 1; j < boxes.length; j += 1) {
        const a = boxes[i].r, b = boxes[j].r;
        if (a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5) {
          overlaps += 1;
          details.push(`${boxes[i].t} ↔ ${boxes[j].t}`);
        }
      }
    }
  });
  let maxRight = 0;
  app.querySelectorAll('*').forEach((node) => {
    const r = node.getBoundingClientRect();
    if (r.width > 0 && !scrollsX(node)) maxRight = Math.max(maxRight, r.right);
  });
  const result = { viewport: vw, doc_width: Math.round(Math.max(maxRight, doc.clientWidth > vw ? 0 : doc.scrollWidth)),
    page_overflow_px: Math.max(0, Math.round(maxRight - vw)),
    offenders: offenders.slice(0, 20), offenders_total: offenders.length,
    charts: app.querySelectorAll('svg').length, text_overlaps: overlaps, overlap_pairs: details.slice(0, 20) };
  let out = document.getElementById('selfcheck');
  if (!out) { out = document.createElement('pre'); out.id = 'selfcheck'; out.hidden = true; document.body.appendChild(out); }
  out.textContent = JSON.stringify(result);
  const focus = /[?&]focus=(\d)\b/.exec(window.location.search);   // 截圖看圖用：把第 n 張圖捲到頂端
  const wraps = app.querySelectorAll('.chart-wrap');
  if (focus && wraps[Number(focus[1])]) wraps[Number(focus[1])].scrollIntoView({ block: 'start' });
}

window.addEventListener('hashchange', route);
route();
