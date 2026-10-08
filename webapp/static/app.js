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

/* ---------- 結構化的值也要看得懂 ----------
   2026-09-08 使用者回饋：「感覺很多地方你就只是收乾淨而寫『見展開』」。
   說的就是這裡——值是物件時，先前那一列印的是「見下方展開」，而底下**沒有**那個展開。
   一句「見下方展開」等於什麼都沒說，而且它假裝有下文。

   現在每一種形狀都在這裡有一句人話；認不得的形狀退回逐格 `鍵：值`，**永遠看得到內容**。
   ⚠ 這一層**不算任何新數字**：`relative_gap`／`growth`／`delta_fair_value` 都是 authority
   已經算好的欄位，這裡只挑欄位、排版、翻標籤。 */
function structuredText(datum) {
  const v = datum && datum.value;
  if (!v || typeof v !== 'object' || Array.isArray(v)) return null;
  const bits = [];

  // ① 市場共識：平均值＋幾位分析師＋高低區間
  if ('avg' in v && 'analyst_count' in v) {
    if (typeof v.analyst_count === 'number') bits.push(`${v.analyst_count} 位分析師`);
    if (typeof v.low === 'number' && typeof v.high === 'number') {
      bits.push(`區間 ${fmtBig(v.low)}–${fmtBig(v.high)}`);
    }
    if (typeof v.growth === 'number') bits.push(`比去年 ${fmtPercent(v.growth)}`);
    if (v.accounting_basis) bits.push(`口徑 ${basisDisplay(v.accounting_basis).label}`);
    return { text: fmtBig(v.avg, v.currency), sub: bits.join('｜') };
  }
  // ⚠ 2026-09-23（Phase 0 Step 0b.1b）：「我們 vs 市場」「兩個指標的差距摘要」「敏感度」「目標價與現價的差」
  // 「持有區間」五種形狀隨估值鏈退役——它們的值不會再出現在任何 datum 裡。
  // ④ 五軸分數：宣告了什麼、實際採用什麼、為什麼被降級
  if ('declared' in v && 'effective' in v) {
    if (v.session_level_label) bits.push(v.session_level_label);
    if (v.downgrade_reason) bits.push(`降級原因：${v.downgrade_reason}`);
    return {
      text: v.declared === v.effective ? String(v.effective) : `${v.effective}（宣告 ${v.declared}）`,
      sub: bits.join('｜'),
    };
  }
  // ⑤ 到期／催化劑監看
  if ('days_to_expiry' in v || ('state' in v && 'label' in v)) {
    if (typeof v.days_to_expiry === 'number') bits.push(`還有 ${v.days_to_expiry} 天到期`);
    if (v.next_catalyst) bits.push(`下一個事件 ${v.next_catalyst}`);
    if (v.next_catalyst_confidence) bits.push(`把握度 ${v.next_catalyst_confidence}`);
    return { text: [v.label, v.state].filter(Boolean).join('｜'), sub: bits.join('｜') };
  }
  // ⑥ thesis 狀態
  if ('status' in v && 'next_check' in v) {
    bits.push(`下次核查 ${v.next_check || '未排定'}`);
    if (v.next_check_source) bits.push(`依據 ${v.next_check_source}`);
    return { text: String(v.status), sub: bits.join('｜') };
  }
  // ⑦ 自動失效能力：它會做什麼、不會做什麼
  if ('overall' in v && 'capability' in v) {
    if (v.capability) bits.push(v.capability);
    if (v.does_not) bits.push(`不做：${v.does_not}`);
    return { text: String(v.overall), sub: bits.join('｜') };
  }
  // ⑪ authority 自己組好的一句話——照抄，不改寫
  if (v.one_sentence) return { text: null, sub: v.one_sentence };
  if (v.note) return { text: null, sub: v.note };
  return null;
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

function readinessLabel(state) {
  const table = (VOCAB && VOCAB.readiness_states) || {};
  return table[state] || '';
}

function readinessBadge(state) {
  const text = { ready: 'ready', ready_with_flags: 'ready · 有旗標', blocked: 'blocked' }[state] || state;
  const badge = el('span', 'badge badge-' + state, text);
  badge.title = readinessLabel(state);
  return badge;
}

function basisDisplay(raw) {
  const table = (VOCAB && VOCAB.accounting_basis_display) || {};
  const entry = table[raw];
  if (!entry) return { label: raw || '未宣告', note: 'authority 沒有登記這個口徑值。', raw: raw };
  return { label: entry.label, note: entry.note, raw: raw };
}

/* ---------- 清單 ---------- */

function numberBlock(label, valueText, subText, klass) {
  const box = el('div', 'num');
  box.appendChild(el('div', 'num-label', label));
  box.appendChild(el('div', 'num-value ' + (klass || ''), valueText));
  if (subText) box.appendChild(el('div', 'num-sub', subText));
  return box;
}

function renderCard(row) {
  const card = el('a', 'card');
  card.href = '#/' + encodeURIComponent(row.ticker);

  const head = el('div', 'card-head');
  const left = el('div');
  left.appendChild(el('div', 'ticker', row.ticker));
  left.appendChild(el('div', 'company', row.company_label || row.company_id || ''));
  head.appendChild(left);

  const badges = el('div', 'badges');
  badges.appendChild(readinessBadge(row.readiness.state));
  // 研究完整度（2026-10-07 起不再是首頁分組，留在卡上）：只印兩種不常見、而且下一步不同的終局
  if (row.closure_terminal === 'settled' || row.closure_terminal === 'awaiting_report') {
    badges.appendChild(el('span', 'badge badge-fresh', row.closure_label || row.closure_terminal));
  }
  // ⚠ 2026-09-23（Phase 0 Step 0b.1b）：stance 徽章（這份判讀是不是我們自己的）隨 FY+1 模型退役。
  if (row.freshness && row.freshness.state === 'stale') {
    const b = el('span', 'badge badge-stale', 'stale');
    b.title = row.freshness.rule;
    badges.appendChild(b);
  }
  head.appendChild(badges);
  card.appendChild(head);

  const numbers = el('div', 'numbers');
  const price = row.price;
  numbers.appendChild(numberBlock(
    '現價',
    fmtQuantity(price.value, price.quote_unit) || '—',
    price.as_of ? `bar ${price.as_of}` : (price.reason ? '無現價' : '')));

  // ⚠ 2026-09-23（Phase 0 Step 0b.1）：卡片上的「沒賭對，要漲跌多少」與「賭注對了」兩格退役
  // ——它們是 overview.implied_return／payoff，也就是 ROADMAP 首屏那一列要拿掉的那把尺。
  // 卡片剩下的數字只有現價（A2 觀測）。「已定價嗎」改由財務三題回答（Phase 3）。
  card.appendChild(numbers);

  // 卡片＝短評第一句。⚠ 2026-09-23（Phase 0 Step 0b.1）：**尺的縮圖整塊退役**
  // （尺上原本是現價／沒賭對／賭對／分析師平均／區間）。首屏的單位是句不是格（AGENTS「APP」），
  // 所以卡片上留下來的是那句話，不是那把尺。
  const brief = row.brief || {};
  if (brief.our_bet && typeof brief.our_bet.value === 'string') {
    card.appendChild(el('div', 'card-brief', brief.our_bet.value));
  } else {
    // 缺席要現形：沒寫短評不是空白（INV-3）。70/73 檔今天都在這一支。
    card.appendChild(el('div', 'card-brief absent', '還沒寫短評'));
  }
  const attention = row.primary_attention;
  if (attention) {
    const kind = attention.absence_kind;
    const tone = attention.settled ? 'settled'
      : (row.readiness.state === 'blocked' ? 'blocked' : 'flags');
    const box = el('div', 'attention ' + tone);
    const head2 = el('div', 'attention-head');
    head2.appendChild(document.createTextNode(
      `${plainPanel(attention.panel, PANEL_TITLE[attention.panel] || attention.panel).title}：${attention.status}`));
    const badge = absenceBadge(kind);
    if (badge) { head2.appendChild(document.createTextNode(' ')); head2.appendChild(badge); }
    box.appendChild(head2);
    if (attention.reason) box.appendChild(el('div', 'attention-body', truncate(attention.reason, 220)));
    if (row.readiness.blocker_count > 1) {
      box.appendChild(el('div', 'attention-body',
        `本節之外另有 ${row.readiness.blocker_count - 1} 項 blocker`));
    }
    card.appendChild(box);
  }
  return card;
}

function truncate(text, limit) {
  const value = String(text);
  return value.length > limit ? value.slice(0, limit) + '…' : value;
}

const PANEL_TITLE = {
  headline: '頭條', fundamental: '基本面', why: '怎麼算到這裡',
  research: '研究現況', entry: 'Entry（optional）',
};

async function renderList() {
  markNav('stocks');
  const data = await getJSON(`${API}/stocks`);
  app.textContent = '';
  footerWarning.textContent = data.correlation_warning || '';
  if (!data.stocks.length && !data.unavailable.length) {
    app.appendChild(el('p', 'empty',
      '還沒有任何 materialized 判讀。請在本機跑 `python -m webapp materialize <TICKER>`。'));
    return;
  }
  /* 常駐計數器。**它必須自己出現**——寫在文件裡的檢查點六天內就被同一個形狀繞過兩次（L14）。
     ⚠ 2026-09-23：「有幾檔的判讀是我們自己的」隨 stance 退役；剩「已有判讀／有賭注」兩個數。 */
  const counters = data.view_counters;
  if (counters) {
    const bar = el('div', 'counter-bar');
    bar.appendChild(el('strong', null, counters.headline || ''));
    if (counters.note) bar.appendChild(el('span', 'note', counters.note));
    app.appendChild(bar);
  }

  /* 分段呈現。順序來自 /api/v1/stocks 的 groups（後端已排好），前端不自己排、不自己命名。 */
  const groups = data.groups || [];
  if (groups.length) {
    groups.forEach((group) => {
      const rows = data.stocks.filter((row) => row.group === group.key);
      if (!rows.length) return;
      const head = el('h2', 'group-head', `${group.label}（${rows.length}）`);
      app.appendChild(head);
      const cards = el('div', 'cards');
      rows.forEach((row) => cards.appendChild(renderCard(row)));
      app.appendChild(cards);
    });
    if (data.group_note) app.appendChild(el('p', 'note', data.group_note));
  } else {
    const cards = el('div', 'cards');
    data.stocks.forEach((row) => cards.appendChild(renderCard(row)));
    app.appendChild(cards);
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

function renderRow(label, datum) {
  const row = el('div', 'row');
  row.appendChild(el('div', 'row-label', label));
  const text = valueText(datum);
  const struct = text === null ? structuredText(datum) : null;
  if (text !== null) {
    const cell = el('div', 'row-value', text);
    if (datum.unit === 'ratio' && typeof datum.value === 'number') cell.classList.add(signClass(datum.value));
    row.appendChild(cell);
  } else if (struct && struct.text) {
    row.appendChild(el('div', 'row-value', struct.text));
  } else if (datum.value && typeof datum.value === 'object') {
    row.appendChild(el('div', 'row-value', ''));   // 內容在下一行，不寫「見下方展開」
  } else {
    row.classList.add('row-absent');
    const cell = el('div', 'row-value');
    const badge = absenceBadge(datum.absence_kind);
    if (badge) cell.appendChild(badge); else cell.appendChild(document.createTextNode('—'));
    row.appendChild(cell);
  }
  if (struct && struct.sub) row.appendChild(el('div', 'row-reason', struct.sub));
  else if (!struct && datum.value && typeof datum.value === 'object') {
    row.appendChild(keyValueList(datum.value));
  }
  if (datum.reason) row.appendChild(el('div', 'row-reason', datum.reason));
  return row;
}

function renderRows(lines, filterRoles) {
  const box = el('div', 'rows');
  const seen = {};
  let duplicates = 0;
  lines.filter((line) => !filterRoles || filterRoles.indexOf(line.role) >= 0)
    .forEach((line) => {
      // 上游偶爾送來完全相同的兩列（同 key 同值，例如 COHR 的 FY2027 共識各出現兩次）。
      // 這裡只印一次，**但把丟掉幾列講出來**——靜默去重會讓「沒有」與「被吃掉」同形（INV-3）。
      const fingerprint = line.key + '|' + JSON.stringify(line.datum.value);
      if (seen[fingerprint]) { duplicates += 1; return; }
      seen[fingerprint] = true;
      box.appendChild(renderRow(plainLine(line.key, line.display_label), line.datum));
    });
  if (duplicates) {
    box.appendChild(el('div', 'row-reason',
      `（上游送來 ${duplicates} 列與上面完全相同的重複資料，這裡只印一次。）`));
  }
  return box;
}

function panelShell(panel, title) {
  const node = el('section', 'panel');
  const heading = el('h2');
  heading.appendChild(document.createTextNode(title || panel.title));
  const badge = absenceBadge(panel.absence_kind);
  if (badge) { heading.appendChild(document.createTextNode(' ')); heading.appendChild(badge); }
  node.appendChild(heading);
  const questions = (panel.questions || [])
    .map((q) => (VOCAB && VOCAB.questions && VOCAB.questions[q]) || q).join('　');
  if (questions) node.appendChild(el('div', 'panel-questions', questions));
  return node;
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

function renderHeadline(view) {
  const panel = view.headline;
  const node = panelShell(panel, '現在多少錢：現價的每一格');
  const lines = lineMap(panel);

  const numbers = el('div', 'headline-numbers');
  const price = lines.current_price && lines.current_price.datum;
  const quoteUnit = price && price.dependencies ? price.dependencies.quote_unit : null;
  if (price) {
    numbers.appendChild(numberBlock('現價', fmtQuantity(price.value, quoteUnit) || '—',
      price.as_of ? `bar ${price.as_of}` : ''));
  }
  if (numbers.childNodes.length) node.appendChild(numbers);
  // ⚠ 2026-09-23（Phase 0 Step 0b.1b）：目標價、隱含報酬、兩桿拆解、epistemics 一句話、口徑列
  // 全部隨估值鏈退役；現價沒有值時由下面的每一格印它自己的缺席理由。
  node.appendChild(group('頭條的每一格（含缺席理由）', () => renderRows(panel.lines)));
  if (panel.notes && panel.notes.length) {
    node.appendChild(group('這一段不是什麼', () => listOf(panel.notes)));
  }
  return node;
}

function kv(label, text) {
  const row = el('div', 'row');
  row.appendChild(el('div', 'row-label', label));
  row.appendChild(el('div', 'row-value', ''));
  row.appendChild(el('div', 'row-reason', text));
  return row;
}

function listOf(items) {
  const list = el('ul', 'notes');
  items.forEach((t) => list.appendChild(el('li', null, t)));
  return list;
}

function renderFundamental(view) {
  const panel = view.fundamental;
  const node = panelShell(panel, '市場預測什麼（原始數字）');
  // ⚠ 2026-09-23（Phase 0 Step 0b.1b）：internal／consensus_same_period／comparison／market_proxy 四組
  // 隨 FY+1 因果橋與估值鏈退役；剩下的是 Engine C 的原始數字。
  const groups = [
    ['consensus_fiscal', '會計年度別共識（身分是 fiscal_period_end；只呈現，不相減）'],
    ['market_context', '市場脈絡與共識時序'],
  ];
  groups.forEach(([role, title]) => {
    const rows = (panel.lines || []).filter((line) => line.role === role);
    if (!rows.length) return;
    // 全部直接印出來。使用者已經點開「完整細節」了，再藏一層只是多一次摩擦。
    node.appendChild(el('div', 'group-title', `${title}（${rows.length} 項）`));
    node.appendChild(renderRows(rows));
  });
  node.appendChild(el('p', 'note', (panel.context || {}).rule || ''));
  if (panel.notes && panel.notes.length) {
    node.appendChild(group('這一段的警告與涵蓋率說明', () => listOf(panel.notes)));
  }
  return node;
}

function renderResearch(view) {
  const panel = view.research;
  const node = panelShell(panel, '研究現況與五軸判斷');
  const rows = (panel.lines || []).filter((line) => line.role === 'thesis' || line.role === 'lifecycle');
  if (rows.length) node.appendChild(renderRows(rows));

  // 舊 session 判讀的反證（`panel.disproofs`）2026-10-01 Phase 4 Step 4.7a 退役：恆「未盯」。反證住 downside 面板。
  if (panel.catalysts && panel.catalysts.length) {
    node.appendChild(group(`催化劑（${panel.catalysts.length}）`, () => listOf(
      panel.catalysts.map((c) => [c.description || c.label, c.expected_at || c.due, c.date_confidence, c.state]
        .filter(Boolean).join('｜')))));
  }
  if (panel.checkpoints && panel.checkpoints.length) {
    node.appendChild(group(`檢核點（${panel.checkpoints.length}）`, () => listOf(
      panel.checkpoints.map((c) => [c.date || c.due, c.what || c.label, c.decides ? '決定：' + c.decides : null,
        c.date_confidence].filter(Boolean).join('｜')))));
  }
  if (panel.risks && panel.risks.length) {
    node.appendChild(group(`風險（${panel.risks.length}）`, () => listOf(panel.risks)));
  }
  const scores = (panel.lines || []).filter((line) => line.role === 'score');
  if (scores.length) node.appendChild(group(`五軸判斷（${scores.length}）`, () => renderRows(scores)));
  if (panel.attention && panel.attention.length) {
    node.appendChild(group(`需要重看的研究成果（${panel.attention.length}）`, () => listOf(
      panel.attention.map((a) => `${a.artifact_type}：${a.state}｜${(a.reasons || []).join('；')}`))));
  }
  return node;
}

function renderFreshness(payload) {
  const f = payload.freshness;
  const node = el('section', 'panel');
  node.appendChild(el('h2', null, '這份判讀有多新'));
  const rows = el('div', 'rows');
  rows.appendChild(kv('materialize 於', `${f.generated_at}（${f.age_hours.toFixed(1)} 小時前，${f.state}）`));
  rows.appendChild(kv('視角', `${payload.point_in_time_mode}${payload.as_of ? '（as-of ' + payload.as_of + '）' : ''}`));
  rows.appendChild(kv('refresh 整體狀態', payload.refresh.overall));
  rows.appendChild(kv('研究 context digest', payload.research_context_digest || '—'));
  rows.appendChild(kv('artifact content digest', payload.content_digest));
  rows.appendChild(kv('新鮮度身分', payload.freshness_identity));
  node.appendChild(rows);
  node.appendChild(el('p', 'note', f.rule));
  if (payload.refresh.notes && payload.refresh.notes.length) {
    node.appendChild(group('refresh 註記', () => listOf(payload.refresh.notes)));
  }
  return node;
}

function renderReadiness(payload) {
  const readiness = payload.readiness;
  const node = el('section', 'panel');
  const head = el('h2');
  head.appendChild(document.createTextNode('判讀狀態　'));
  head.appendChild(readinessBadge(readiness.state));
  node.appendChild(head);
  node.appendChild(el('div', 'panel-questions', readinessLabel(readiness.state)));

  (readiness.blocker_details || []).forEach((item) => {
    const box = el('div', 'attention ' + (item.settled ? 'settled' : 'blocked'));
    const head2 = el('div', 'attention-head');
    head2.appendChild(document.createTextNode(
      `卡在「${plainPanel(item.panel, PANEL_TITLE[item.panel] || item.panel).title}」這一層（${item.status}）　`));
    const badge = absenceBadge(item.absence_kind);
    if (badge) head2.appendChild(badge);
    box.appendChild(head2);
    box.appendChild(el('div', 'attention-body', absenceLabel(item.absence_kind) || ''));
    if (item.reason) box.appendChild(el('div', 'attention-body', item.reason));
    node.appendChild(box);
  });
  (readiness.flag_details || []).forEach((item) => {
    const box = el('div', 'attention flags');
    const head2 = el('div', 'attention-head',
      `旗標：${plainPanel(item.panel, PANEL_TITLE[item.panel] || item.panel).title}（${item.status}）`);
    box.appendChild(head2);
    if (item.reason) box.appendChild(el('div', 'attention-body', item.reason));
    node.appendChild(box);
  });
  if (readiness.optional_unavailable && readiness.optional_unavailable.length) {
    // 面板名走 /meta 白話、缺席走產生端宣告的分型（3.7 覆核：原本印內部 key，並把「不上板」說成能力未提供）。
    const view = payload.view || {};
    const items = readiness.optional_unavailable.map((text) => {
      const key = String(text).split('：')[0];
      const panel = view[key] || {};
      const short = (VOCAB && VOCAB.plain_absence_short && VOCAB.plain_absence_short[panel.absence_kind]) || panel.status;
      return `${plainPanel(key, PANEL_TITLE[key] || key).title}（${short || '沒有內容'}）`;
    });
    node.appendChild(el('p', 'note',
      '選配面板沒有內容：' + items.join('、') + '——**不影響** readiness，不代表這檔研究不完整'));
  }
  node.appendChild(group('readiness 的判準原文', () => el('p', 'note', readiness.rule)));
  return node;
}

/* ---------- 白話別名：全部來自 /api/v1/meta，前端不維護第二份（L16） ---------- */

function plainPanel(key, fallback) {
  const table = (VOCAB && VOCAB.plain_panel_titles) || {};
  return table[key] || { title: fallback || key, hint: '' };
}

function plainLine(key, fallback) {
  const table = (VOCAB && VOCAB.plain_line_labels) || {};
  return table[key] || fallback || key;
}

function plainReadiness(state) {
  const table = (VOCAB && VOCAB.plain_readiness) || {};
  return table[state] || { label: state, note: readinessLabel(state) };
}

/* ---------- 單檔判讀：先給答案，細節收起來 ----------
   2026-09-08 使用者回饋：「太多展開、太多字、全部是內部術語，基本上看不懂」。
   改法有三條，順序就是這一頁的結構：
   ① **先給結論與價格**——現在多少錢、我們認為值多少、差多少，再配一張這檔自己的走勢；
   ② **只留會改變你行動的四塊**（卡在哪／最脆弱／什麼會推翻它／我們 vs 市場）；
   ③ 其餘**全部收進一個** `<details>`——原本六個面板的完整欄位一格沒刪，只是不再預設攤開。
   ⚠ 刪的是版面不是內容：任何一格都還在，`/api/v1/stocks/<T>` 也一個欄位沒少。 */

function conclusionCard(payload, view) {
  const panel = view.headline;
  const lines = lineMap(panel);
  const meta = plainPanel('headline', panel.title);
  const node = el('section', 'panel callout');
  node.appendChild(el('h2', null, meta.title));
  node.appendChild(el('div', 'panel-questions', meta.hint));

  const numbers = el('div', 'headline-numbers');
  const price = lines.current_price && lines.current_price.datum;
  const quoteUnit = price && price.dependencies ? price.dependencies.quote_unit : null;
  if (price) {
    numbers.appendChild(numberBlock(plainLine('current_price'), fmtQuantity(price.value, quoteUnit) || '—',
      price.as_of ? `收盤 ${price.as_of}` : ''));
  }
  if (numbers.childNodes.length) node.appendChild(numbers);
  // 沒有現價時，把「為什麼沒有」放在跟數字一樣顯眼的位置——不留白、不寫 0。
  if (price && (price.value === null || price.value === undefined)) {
    const box = el('div', 'attention ' + (isSettled(price.absence_kind) ? 'settled' : 'blocked'));
    const head = el('div', 'attention-head');
    head.appendChild(document.createTextNode(plainLine('current_price') + '：'));
    const badge = absenceBadge(price.absence_kind);
    if (badge) head.appendChild(badge);
    box.appendChild(head);
    if (price.reason) box.appendChild(el('div', 'attention-body', price.reason));
    node.appendChild(box);
  }
  // ⚠ 2026-09-23（Phase 0 Step 0b.1b）：目標價、隱含報酬、兩桿拆解、stance 橫幅、epistemics 一句話
  // 隨估值鏈退役（C／H 組）；賭注／下檔的四價區塊已隨 E 組退役。反證那一端在「錯了怎麼知道」面板（downside）。
  // D2（2026-09-18）：歸零旗標。它問「這家公司會不會直接歸零」。
  node.appendChild(wipeoutBlock(view));
  return node;
}

/* 歸零旗標（D2，2026-09-18）：四盞燈。**只畫顏色與一句話**——算出顏色的數字住稽核區
   （每盞燈的 dependencies.inputs），因為 D2 定案是「紅黃綠不給數字」。

   ⚠ 顏色**照抄** `alpha.wipeout` 的判定；本畫面不從 inputs 重判一次色，也不把四盞合成一個分數。
   ⚠ 灰燈與綠燈在畫面上必須一眼分得出來：灰＝這一項沒量到，不是「查過都沒事」。 */
const WIPEOUT_COLOURS = { red: { mark: '🔴', word: '紅' }, amber: { mark: '🟡', word: '黃' },
                          green: { mark: '🟢', word: '綠' } };

function wipeoutBlock(view) {
  const panel = view.wipeout;
  const meta = plainPanel('wipeout', panel ? panel.title : '會不會歸零');
  const node = el('div', 'bet');
  node.appendChild(el('div', 'group-title', meta.title));
  if (!panel) return node;
  node.appendChild(el('div', 'panel-questions', meta.hint));
  const tally = (panel.context && panel.context.tally) || {};
  node.appendChild(el('div', 'rule',
    `紅 ${tally.red || 0}｜黃 ${tally.amber || 0}｜綠 ${tally.green || 0}｜灰（沒量到）${tally.unlit || 0}`));
  const list = el('ul', 'weak');
  (panel.lines || []).filter((line) => line.role === 'wipeout').forEach((line) => {
    const d = line.datum;
    const value = (d && d.value) || {};
    const colour = WIPEOUT_COLOURS[value.colour];
    const li = el('li');
    li.appendChild(document.createTextNode(
      // ⚠ 2026-09-30（Step 3.7 渲染實測）：原本是 `plainLine(line.key) || display_label`——plainLine 查不到會回 key 本身，
      // 於是 `||` 右邊永遠用不到，畫面印出 `wipeout_going_concern` 這種內部名。fallback 要傳進去。
      `${colour ? colour.mark + ' ' + colour.word : '⬜ 灰'}　${plainLine(line.key, line.display_label)}`));
    const why = value.reason || d.reason;
    if (why) li.appendChild(el('span', 'rule', why));
    if (!colour) {
      const badge = absenceBadge(d.absence_kind);
      if (badge) li.appendChild(badge);
    }
    list.appendChild(li);
  });
  node.appendChild(list);
  if (panel.context && panel.context.unlit_rule) {
    node.appendChild(el('div', 'rule', panel.context.unlit_rule));
  }
  return node;
}

/* 賭注（V0，2026-09-15）與下檔（D2，2026-09-18）：「如果對了／如果反證成真，值多少」。
   數字全部照抄對應 panel 的輸出；本畫面不相減、不算年化、**不補 bull case 也不補 bear case**。
   沒寫時印一行「還沒寫」——缺席要現形，而且兩者都是 optional，不影響判讀完不完整。

   ⚠ 兩邊共用這一個函式，是為了讓兩組數字**逐格對得起來**——使用者要並排讀它們，
   而兩份各自手寫的區塊會在某次改動後悄悄長出不同的格。 */
/* ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`OVERLAY_BLOCKS` 與 `betBlock`（四價區塊）隨 E 組退役。 */
/* ⚠ 2026-09-23（Step 0b.1b）：`renderDownside` 隨 downside panel 退役。 */

function renderBet(view) {
  const panel = view.bet;
  const node = panelShell(panel, '賭注：我們賭什麼、押在哪一層、什麼必須為真（optional，不影響這份判讀完不完整）');
  node.appendChild(el('p', 'note', (panel.context || {}).optional_rule || ''));
  // Step 3.7：「押在哪一層（或哪個插槽）」是敘事宣告的 rides[]——印成「節點（層／插槽）」一句；其餘兩格照 renderRow。
  const box = el('div', 'rows');
  (panel.lines || []).forEach((line) => {
    const d = line.datum;
    if (line.key === 'rides' && Array.isArray(d.value)) {
      const row = el('div', 'row');
      row.appendChild(el('div', 'row-label', line.display_label));
      row.appendChild(el('div', 'row-value',
        d.value.map((r) => `「${r.node_name || r.node}」（${r.unit_label || r.unit}）`).join('、')));
      box.appendChild(row);
    } else {
      box.appendChild(renderRow(plainLine(line.key, line.display_label), d));
    }
  });
  node.appendChild(box);
  const glossary = unitGlossary();
  if (glossary) node.appendChild(glossary);
  if (panel.notes && panel.notes.length) {
    node.appendChild(group('賭注不是什麼', () => listOf(panel.notes)));
  }
  return node;
}

function priceCard(payload) {
  const series = payload.price_series || [];
  const node = el('section', 'panel');
  node.appendChild(el('h2', null, '股價走勢（這檔自己的收盤價）'));
  const price = (payload.overview && payload.overview.price) || {};
  node.appendChild(lineChart(series, {
    ariaLabel: `${payload.ticker} 收盤價`,
    emptyNote: '沒有取到這檔的收盤序列——沒有折線不是價格為 0。',
  }));
  const note = (VOCAB && VOCAB.price_series_note) || '';
  node.appendChild(el('p', 'note',
    (series.length ? `${series[0].session_date} 起，共 ${series.length} 個已收盤交易日` +
      (price.quote_unit ? `（單位 ${price.quote_unit}）。` : '。') : '') + note));
  // 2026-10-07：「表格版：每一個交易日的收盤」拿掉（使用者：「不需要給我看的…拿掉」）——十字線 tooltip 讀得到每一天的值。
  return node;
}

/* 個股頁 schema 的填得滿表（2026-10-08，個股頁 S2；稽核區）：十三塊 × 元素，每格有值或具名缺席。
   塊與元素的名字只來自 `/api/v1/meta` 的 `page_schema`（前端不留第二份）；這一檔的逐格結果是 artifact 的 `page_fill`。
   artifact 是 S2 之前 materialize 的就沒有這一格——照實說「還沒算」，不畫成空表（L13：沒算與沒有不得同形）。 */
function pageFillCard(payload) {
  const schema = VOCAB && VOCAB.page_schema;
  const fill = payload.page_fill;
  const node = el('section', 'panel');
  node.appendChild(el('h2', null, '這一頁填得滿嗎（個股頁 schema v1.0）'));
  if (!schema) {
    node.appendChild(el('div', 'panel-questions', '合約讀不到（/api/v1/meta 沒有 page_schema）——不是「全滿」也不是「全空」'));
    return node;
  }
  if (!fill || !Array.isArray(fill.rows)) {
    node.appendChild(el('div', 'panel-questions', '這份 artifact 是填得滿表上線之前算的——重跑 materialize 才有'));
    return node;
  }
  const s = fill.summary || {};
  node.appendChild(el('div', 'panel-questions',
    `${s.elements} 格：有值 ${s.value}、缺席 ${s.absent}（每一格缺席都說得出是哪一種、在哪裡找過；不放閘、不排序）`));
  const byKey = {};
  fill.rows.forEach((row) => { byKey[row.element] = row; });
  (schema.blocks || []).forEach((block) => {
    const box = el('div', 'attention');
    box.appendChild(el('div', 'attention-head', `${block.key}　${block.title}——${block.question}`));
    (schema.elements || []).filter((e) => e.block === block.key).forEach((element) => {
      const row = byKey[element.key] || {};
      const line = el('div', 'attention-body');
      line.appendChild(document.createTextNode(`${row.state === 'value' ? '●' : '○'} ${element.label}　`));
      if (row.state !== 'value') {
        const badge = absenceBadge(row.absence_kind);
        if (badge) line.appendChild(badge);
        if (row.looked) line.appendChild(document.createTextNode(`　找過：${row.looked}`));
      }
      box.appendChild(line);
    });
    node.appendChild(box);
  });
  return node;
}

function blockerCard(payload) {
  const readiness = payload.readiness;
  const plain = plainReadiness(readiness.state);
  const blockers = readiness.blocker_details || [];
  const flags = readiness.flag_details || [];
  if (!blockers.length && !flags.length) return null;
  const node = el('section', 'panel');
  const head = el('h2');
  head.appendChild(document.createTextNode('卡在哪　'));
  head.appendChild(el('span', 'badge badge-' + readiness.state, plain.label));
  node.appendChild(head);
  node.appendChild(el('div', 'panel-questions', plain.note));
  blockers.forEach((item) => {
    const box = el('div', 'attention ' + (item.settled ? 'settled' : 'blocked'));
    const head2 = el('div', 'attention-head');
    head2.appendChild(document.createTextNode(
      `${plainPanel(item.panel, PANEL_TITLE[item.panel] || item.panel).title}　`));
    const badge = absenceBadge(item.absence_kind);
    if (badge) head2.appendChild(badge);
    box.appendChild(head2);
    box.appendChild(el('div', 'attention-body', absenceLabel(item.absence_kind) || ''));
    if (item.reason) box.appendChild(el('div', 'attention-body', truncate(item.reason, 160)));
    node.appendChild(box);
  });
  flags.forEach((item) => {
    const box = el('div', 'attention flags');
    box.appendChild(el('div', 'attention-head',
      `要留意：${plainPanel(item.panel, PANEL_TITLE[item.panel] || item.panel).title}`));
    if (item.reason) box.appendChild(el('div', 'attention-body', truncate(item.reason, 220)));
    node.appendChild(box);
  });
  return node;
}

/* 錯了怎麼知道（Phase 3 Step 3.7，論證層）：每一條反證連到盯它的 watch；沒有 watch 的印「未盯」。
   **全部照抄** downside 面板（歸屬＝`attributed_watches`、落格＝`watch_category`，與心跳段 2 同一套）；
   本畫面不判、不算，連計數都是 materialize 端給的。舊判讀（session assessor）的反證 2026-10-01 退役、不在這裡印。 */
function downsideCard(view) {
  const panel = view.downside;
  if (!panel) return null;
  const meta = plainPanel('downside', panel.title);
  const node = el('section', 'panel');
  node.appendChild(el('h2', null, meta.title));
  if (meta.hint) node.appendChild(el('div', 'panel-questions', meta.hint));
  const lines = (panel.lines || []).filter((line) => line.role === 'downside');
  if (!lines.length) {
    const box = el('div', 'attention flags');
    // 「名下還沒有反證」與「這次沒讀到反證的來源」下一步不同（3.7 R1）：標題跟著產生端宣告的分型走（首屏③同一個函式）。
    const head = el('div', 'attention-head', downsideAbsenceHead(panel) + '　');
    const badge = absenceBadge(panel.absence_kind);
    if (badge) head.appendChild(badge);
    box.appendChild(head);
    if (panel.reason) box.appendChild(el('div', 'attention-body', panel.reason));
    node.appendChild(box);
  } else {
    const counts = (panel.context || {}).counts || {};
    node.appendChild(el('div', 'rule', `在盯 ${counts.active || 0}｜醒來待判 ${counts.fired || 0}｜`
      + `觸及待處置 ${counts.touched || 0}｜到期待複查 ${counts.expired || 0}｜未盯 ${counts.unwatched || 0}`));
    const list = el('ul', 'weak');
    lines.forEach((line) => {
      const r = line.datum.value || {};
      const li = el('li', null, r.condition || '');
      const bits = [r.source_label || line.display_label,
        r.watch_id ? `watch ${r.watch_id}：${r.state_label}` + (r.until ? `（到期 ${r.until}）` : '') : r.state_label];
      if (r.check_frequency) bits.push('多久看一次：' + r.check_frequency);
      if (r.action_48h) bits.push('觸發後要做什麼：' + r.action_48h);
      li.appendChild(el('span', 'rule', bits.join('｜')));
      // 同一筆 watch 只印一列；敘事也以來源鍵連到它時，把另一個來源寫在這裡（不另起一列、不多算一次）。
      if ((r.also || []).length) {
        li.appendChild(el('span', 'rule', '也連到這一條：' + r.also.map((a) => a.source_label).join('、')));
      }
      list.appendChild(li);
    });
    node.appendChild(list);
  }
  (panel.notes || []).forEach((text) => node.appendChild(el('p', 'note', text)));
  const catalysts = (view.research && view.research.catalysts) || [];
  if (catalysts.length) {
    node.appendChild(el('div', 'group-title', '什麼時候會知道'));
    // 催化劑的欄位是 description／expected_at（3.7 覆核：原本照抄 label／due，畫面只剩內部狀態字 unlinked）。
    node.appendChild(listOf(catalysts.map((c) => [c.expected_at || '日期未定', c.description || c.label,
      c.date_confidence].filter(Boolean).join('｜'))));
  }
  return node;
}

/* 財務三題的數字（Phase 3 Step 3.7，稽核區）：每一行＝值＋來源＋as of＋口徑＋規則，或缺席分型的中文。
   **照抄** three_questions 面板（read model 的同一格）；這裡只挑顯示格式（百分位、倍數、百分比、燈色），不算、不比、
   **沒有門檻**——幾分算已定價由寫敘事的人判斷。 */
const TQ_QUESTIONS = { will_it_die: '會死嗎', priced_in: '已定價嗎', in_numbers: '出現在數字裡了嗎' };
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

function threeQuestionsCard(view) {
  const panel = view.three_questions;
  if (!panel) return null;
  const meta = plainPanel('three_questions', panel.title);
  const node = el('section', 'panel');
  node.appendChild(el('h2', null, meta.title));
  if (meta.hint) node.appendChild(el('div', 'panel-questions', meta.hint));
  const lines = (panel.lines || []).filter((line) => line.role === 'three_question');
  if (!lines.length) {
    const box = el('div', 'attention flags');
    const head = el('div', 'attention-head', '這次沒有三題的數字　');
    const badge = absenceBadge(panel.absence_kind);
    if (badge) head.appendChild(badge);
    box.appendChild(head);
    if (panel.reason) box.appendChild(el('div', 'attention-body', panel.reason));
    node.appendChild(box);
    return node;
  }
  Object.keys(TQ_QUESTIONS).forEach((question) => {
    const rows = lines.filter((line) => (line.datum.dependencies || {}).question === question);
    if (!rows.length) return;
    const title = el('div', 'group-title', TQ_QUESTIONS[question]);
    title.id = 'tq-' + question;
    node.appendChild(title);
    if (question === 'priced_in') {
      const plain = pricedInPlain();
      if (plain) node.appendChild(plain);
    }
    const box = el('div', 'rows');
    rows.forEach((line) => {
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
        const where = [deps.source ? '來源 ' + deps.source : null, d.as_of ? 'as of ' + d.as_of : null,
          deps.basis ? '口徑 ' + deps.basis : null].filter(Boolean).join('｜');
        if (where) row.appendChild(el('div', 'row-reason', where));
        if (Array.isArray(d.value)) {
          const list = el('ul', 'weak');
          d.value.forEach((point) => list.appendChild(tqPoint(point)));
          row.appendChild(list);
        } else if (typeof d.value === 'object') {
          row.appendChild(keyValueList(d.value));
        }
      }
      // 算出這一格的輸入（倍數、中位數、窗、口徑理由）——敘事引用的數字要在這裡核對得到（AGENTS：敘事那一句引用稽核區）。
      if (deps.detail && typeof deps.detail === 'object' && Object.keys(deps.detail).length) {
        row.appendChild(keyValueList(deps.detail));
      }
      if (d.method) row.appendChild(el('div', 'rule', '規則：' + d.method));
      box.appendChild(row);
    });
    node.appendChild(box);
  });
  (panel.notes || []).forEach((text) => node.appendChild(el('p', 'note', text)));
  return node;
}

/* 市場預測什麼（稽核區）：會計年度別共識與市場觀測的**原始數字**。
   ⚠ 2026-09-23（Phase 0 Step 0b.1b）：原本這裡是「我們估／市場共識／我們比市場」四欄表＋反推表
   （COMPARE_ROWS／reverseBridgeBlock）——內部預測與相減全部讀 FY+1 因果橋與估值鏈，整組退役。
   現在只印市場說了什麼；每一格都是 materialize 端的同一個 datum，本畫面不算任何數。 */
function versusMarketCard(view) {
  const panel = view.fundamental;
  const lines = lineMap(panel);
  const ctx = panel.context || {};
  const meta = plainPanel('fundamental', panel.title);
  const node = el('section', 'panel');
  node.appendChild(el('h2', null, meta.title));
  node.appendChild(el('div', 'panel-questions', meta.hint));

  const fiscal = (panel.lines || []).filter((line) => line.role === 'consensus_fiscal');
  if (fiscal.length) {
    node.appendChild(el('div', 'group-title', `會計年度別共識（${fiscal.length} 項；身分是 fiscal_period_end）`));
    node.appendChild(renderRows(fiscal));
  } else {
    node.appendChild(el('p', 'note', '還沒有會計年度別共識（consensus_estimates 沒有這檔的列）。'));
  }

  // 市場還說了什麼：賣方目標價與倍數。**這是別人的數字**，不是本系統的預期報酬。
  const context = el('div', 'headline-numbers');
  const target = lines.target_mean && lines.target_mean.datum;
  const count = lines.analyst_count && lines.analyst_count.datum;
  if (target && typeof target.value === 'number') {
    context.appendChild(numberBlock('賣方目標價（均值）', fmtBig(target.value),
      count && typeof count.value === 'number'
        ? `${count.value} 家；不是我們的目標價` : '不是我們的目標價'));
  }
  const forwardPe = lines.forward_pe && lines.forward_pe.datum;
  if (forwardPe && typeof forwardPe.value === 'number') {
    context.appendChild(numberBlock('市場給的預估本益比', fmtNumber(forwardPe.value, 1) + 'x',
      '以市場共識 EPS 計'));
  }
  if (context.childNodes.length) node.appendChild(context);
  node.appendChild(el('p', 'note', ctx.rule || ''));
  return node;
}

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
  // Phase 7 Step 7.0e：v2 短評照五題排（對照表只住 contracts，經 `.meta.json` 帶來）；其餘照舊一格一行。
  const available = Boolean(panel && panel.context && panel.context.available);
  // 個股頁 S5（2026-10-08）：首屏照 page_schema 的段與塊排（取代 Phase 7 Step 7.0e 的五題）；v1 短評照舊一格一行。
  const screen = available ? schemaFirstScreen(payload, view, panel) : null;
  if (screen) {
    node.appendChild(screen);
  } else if (available) {
    const story = el('div', 'story');
    (panel.lines || []).filter((line) => line.key.indexOf('brief:') === 0)
      .forEach((line) => story.appendChild(storyRow(line)));
    node.appendChild(story);
  }
  if (available) {
    const rides = view.bet && lineMap(view.bet).rides;
    if (rides && Array.isArray(rides.datum.value) && rides.datum.value.length) {
      const glossary = unitGlossary();
      if (glossary) node.appendChild(glossary);
    }
  } else {
    const box = el('div', 'attention flags');
    box.appendChild(el('div', 'attention-head', '還沒寫短評'));
    box.appendChild(el('div', 'attention-body', (panel && panel.reason) || meta.hint));
    node.appendChild(box);
  }
  // ⚠ **2026-09-23（Phase 0 Step 0b.1）：首屏那把尺與「要翻倍需要什麼為真」計算框整塊退役。**
  // ROADMAP「個股頁」對照表把它們列進「拿掉」：尺上是現價／沒賭對／賭對／判斷錯了，
  // 計算框問的是「這個結構允不允許翻倍」——兩者都建在估值鏈與多年反向橋上。
  // 接手的是末行候選狀態與財務三題三個字（Phase 3 Step 3.7，下面這一行）。
  const line = candidateLine(view, Boolean(screen));
  if (line) node.appendChild(line);
  // 走勢圖留下來：它是**脈絡**不是訊號（AGENTS「量測、訊號、脈絡三分」）。
  node.appendChild(priceCard(payload));
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
 * （v2 敘事的格、既有元件；都沒有就照印合約宣告的「還沒寫／還沒做」）＋一個展開（這一塊的格，照抄填得滿表）。
 * 這一頁的短評沒帶齊合約放的每一格（v1 短評）或 `.meta.json` 是舊的——回 null，照舊版面，不猜、不補。 */
function schemaFirstScreen(payload, view, panel) {
  const schema = VOCAB && VOCAB.page_schema;
  const screen = schema && schema.first_screen;
  if (!screen || !Array.isArray(screen.sections) || !screen.sections.length) return null;
  const lines = lineMap(panel);
  const readings = screen.readings || {};
  const slots = [];
  Object.keys(readings).forEach((key) => (readings[key].slots || []).forEach((slot) => slots.push(slot)));
  if (!slots.every((slot) => lines['brief:' + slot])) return null;
  const blocks = {};
  (schema.blocks || []).forEach((block) => { blocks[block.key] = block; });
  const box = el('div', 'schema-screen');
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

/** 一塊：讀法（短評的格依序、再放既有元件）；兩者都沒有就印合約的 pending。不改任何一格、不加字。 */
function schemaBlock(payload, view, lines, block, reading) {
  const node = el('div', 'fq ss-block');
  const head = el('h3', 'fq-title', block.title);
  if (block.question) head.title = block.question;
  node.appendChild(head);
  const story = el('div', 'story');
  (reading.slots || []).forEach((slot) => { if (lines['brief:' + slot]) story.appendChild(storyRow(lines['brief:' + slot])); });
  if (story.childNodes.length) node.appendChild(story);
  (reading.parts || []).forEach((part) => questionPart(view, part).forEach((n) => node.appendChild(n)));
  if (!(reading.slots || []).length && !(reading.parts || []).length) {
    node.appendChild(el('div', 'row-reason ss-pending', reading.pending || '還沒寫'));
  }
  blockVisuals(payload, view, block.key).forEach((n) => node.appendChild(n));
  const cells = blockCells(payload, view, block);
  if (cells) node.appendChild(cells);
  return node;
}

/** 一塊的格（展開層）：照抄填得滿表——有值印承載它的 line 的值（結構化的值不在這裡攤開，同一份在稽核區），
 * 缺席印分型與「在哪裡找過」。不判、不算、不排序。 */
function blockCells(payload, view, block) {
  const schema = VOCAB && VOCAB.page_schema;
  const fill = payload.page_fill;
  if (!schema || !fill || !Array.isArray(fill.rows)) return null;
  const elements = (schema.elements || []).filter((e) => e.block === block.key);
  if (!elements.length) return null;
  const byKey = {};
  fill.rows.forEach((row) => { byKey[row.element] = row; });
  const valued = elements.filter((e) => (byKey[e.key] || {}).state === 'value').length;
  return drill(`這一塊的格：${elements.length} 格，有值 ${valued}、缺席 ${elements.length - valued}`, () => {
    const list = el('div', 'ss-cells');
    elements.forEach((element) => {
      const row = byKey[element.key] || {};
      const line = el('div', 'attention-body');
      line.appendChild(document.createTextNode(`${row.state === 'value' ? '●' : '○'} ${element.label}　`));
      if (row.state === 'value') {
        line.appendChild(el('span', 'dim', cellValueText(view, row.lines || [])));
      } else {
        const badge = absenceBadge(row.absence_kind);
        if (badge) line.appendChild(badge);
        if (row.looked) line.appendChild(document.createTextNode(`　找過：${row.looked}`));
      }
      list.appendChild(line);
    });
    return list;
  });
}

/** 有值那一格的字：承載它的 line 的值（字串或數字照印、最多三條）；結構化的值指去稽核區，不在這裡另組字。 */
function cellValueText(view, keys) {
  const index = {};
  Object.keys(view || {}).forEach((name) => {
    const panel = view[name];
    if (panel && Array.isArray(panel.lines)) panel.lines.forEach((line) => { index[line.key] = line; });
  });
  const parts = [];
  keys.slice(0, 3).forEach((key) => {
    const line = index[key];
    const d = line && line.datum;
    if (d && (typeof d.value === 'string' || typeof d.value === 'number')) {
      const text = truncate(String(valueText(d) || d.value), 80);
      if (parts.indexOf(text) < 0) parts.push(text);   // 兩條 line 承載同一句（例：敘事的 our_bet 與賭注面板）只印一次
    }
  });
  return parts.length ? parts.join('｜') : '有值（細節在稽核區）';
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

/* 首屏末行（Phase 3 Step 3.7）：候選狀態＋財務三題三個字。**全部照抄** candidate 面板——字由 materialize 端給
   （與候選板同一個推導），本畫面不判、不算。沒有敘事也沒有持有＝不上板，三個字照印（會死嗎看燈，兩題「未答」）。
   2026-09-30 使用者回饋（「這三個字是要我去候選板看詳細嗎？」）：細節其實在同一頁的稽核區——三個字改成可以點，
   點了打開稽核區、跳到那一題的數字；候選狀態直接寫理由、在等什麼、哪天醒；會死嗎把不是綠的燈逐盞寫出來。 */
const CANDIDATE_WORDS = [['candidate:will_it_die', '會死嗎', 'will_it_die'], ['candidate:priced_in', '已定價嗎', 'priced_in'],
  ['candidate:in_numbers', '出現在數字裡了嗎', 'in_numbers']];

/** 打開同頁的稽核區、捲到那一題（`threeQuestionsCard` 給每一題的標題掛了 id）。稽核區不在就不動。 */
function jumpToAudit(question) {
  const box = document.getElementById('audit-drill');
  if (!box) return;
  box.open = true;
  const target = document.getElementById('tq-' + question) || box;
  target.scrollIntoView({ behavior: 'smooth', block: 'start' });
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

/** 歸零燈：燈名＋顏色＋理由，照抄 wipeout 面板（與稽核區同一份）。`withGreen`＝綠燈也列（五題的④逐盞列；
 * 舊版面只列不是綠的那幾盞，全綠就不印）。灰＝沒量到，不是綠。 */
function lampsBlock(view, withGreen) {
  const panel = view.wipeout;
  if (!panel) return null;
  const items = [];
  (panel.lines || []).filter((line) => line.role === 'wipeout').forEach((line) => {
    const d = line.datum || {};
    const value = d.value || {};
    if (value.colour === 'green' && !withGreen) return;
    const colour = WIPEOUT_COLOURS[value.colour];
    const name = plainLine(line.key, line.display_label).replace(/^歸零旗標：/, '');
    const why = value.colour === 'green' ? '' : (value.reason || d.reason || absenceLabel(d.absence_kind) || '');
    items.push(`${colour ? colour.mark + ' ' + colour.word + '　' + name : '⬜ 灰　' + name + '（沒量到，不是綠）'}${why ? '：' + why : ''}`);
  });
  if (!items.length) return null;
  const box = el('div', 'lamp-notes');
  items.forEach((text) => box.appendChild(el('div', 'row-reason', text)));
  return box;
}

/** 財務三題的三個字（可點：打開稽核區、跳到那一題）。`questions`＝印哪幾題（舊版面三個一起；五題版面分到②④）。
 * 「已定價嗎」在的時候，白話緊跟在後——首屏只有這一處印白話。 */
function wordsBlock(view, questions) {
  const panel = view.candidate;
  if (!panel || !(panel.lines || []).length) return [];
  const lines = lineMap(panel);
  const words = el('div', 'candidate-words');
  CANDIDATE_WORDS.filter((entry) => questions.indexOf(entry[2]) >= 0).forEach(([key, label, question]) => {
    const d = lines[key] && lines[key].datum;
    const word = el('button', 'word word-link', `${label}　${d && d.value ? d.value : '—'} ↓`);
    word.type = 'button';
    word.title = '打開下面的稽核區，跳到這一題的數字';
    word.addEventListener('click', () => jumpToAudit(question));
    words.appendChild(word);
  });
  const out = [words];
  if (questions.indexOf('priced_in') >= 0) {
    const plain = pricedInPlain();
    if (plain) out.push(plain);
  }
  return out;
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
    const badge = absenceBadge(panel.absence_kind);
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
  // 候選板是「和其他檔並排看」，不是這一檔的細節（細節在上面三個字點下去的稽核區）。
  const link = el('a', 'dim', '和其他檔一起看（候選板）→');
  link.href = '#/candidates';
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

function argumentCard(view) {
  const panel = view.argument;
  const meta = plainPanel('argument', panel ? panel.title : '為什麼這樣想');
  const node = el('section', 'panel argument-card');
  node.appendChild(el('h2', null, meta.title));
  node.appendChild(el('div', 'panel-questions', meta.hint));
  if (!panel) return node;
  (panel.lines || []).filter((line) => line.role === 'paragraph').forEach((line) => {
    const d = line.datum;
    const sec = el('div', 'arg-section');
    sec.appendChild(el('h3', null, line.display_label));
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
    node.appendChild(sec);
  });
  return node;
}

/* 基本數字列（2026-09-15 使用者回饋：基本數字不用全部藏進稽核）。
   只放六格、每格白話標籤；全部照抄 headline／bet panel 既有的 Datum，不算、不造句。 */
function numbersStrip(view) {
  const head = lineMap(view.headline);
  const node = el('section', 'panel numbers-strip');
  node.appendChild(el('div', 'group-title', '基本數字'));
  const numbers = el('div', 'headline-numbers');
  const price = head.current_price && head.current_price.datum;
  const quoteUnit = price && price.dependencies ? price.dependencies.quote_unit : null;
  if (price && typeof price.value === 'number') {
    numbers.appendChild(numberBlock(plainLine('current_price'), fmtQuantity(price.value, quoteUnit) || '—',
      price.as_of ? `收盤 ${price.as_of}` : ''));
  }
  /* ⚠ 2026-09-23（Phase 0 Step 0b.1b）：「沒賭對的目標價／要漲跌多少／市場付的倍數 vs 我們給的」隨
     估值鏈退役（C／H 組）；賭注與下檔的四格已隨 E 組退役。基本數字只剩現價——「已定價嗎」由財務三題回答（Phase 3）。 */
  if (numbers.childNodes.length) node.appendChild(numbers);
  return node;
}

async function renderDetail(ticker) {
  markNav('stocks');
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
  app.appendChild(head);

  // 首屏只有短評（2026-09-15 使用者回饋：「一堆數字跟內部名詞堆起來的東西根本看不懂」）。
  // 原本的六張卡整組收進第一個展開，一個字不刪；再下一層才是第二個展開。
  // 三層（2026-09-15）：①短評 ②論證（可長文，直接攤開）＋走勢 ③查核區（一個展開；格只住這裡）
  app.appendChild(briefCard(payload, view));
  app.appendChild(numbersStrip(view));
  app.appendChild(argumentCard(view));
  // Phase 2 Step 2.7：讀圖面板（選配）緊接在論證之後——論證講這條鏈怎麼走，讀圖講鏈上那一層現在還是不是當初讀的樣子。
  const readings = readingsCard(view);
  if (readings) app.appendChild(readings);
  // Phase 3 Step 3.7：downside（錯了怎麼知道）緊接讀圖——每條反證連到盯它的 watch，沒有的印「未盯」。
  const downside = downsideCard(view);
  if (downside) app.appendChild(downside);
  const audit = el('section', 'panel');
  const auditDrill = drill('稽核：每一格的來源、狀態、算式與警告（給查核用；首屏三個字點下去會跳到這裡）', () => {
    const box = el('div', 'why-box');
    box.appendChild(conclusionCard(payload, view));
    // ⚠ 2026-09-23（Phase 0 Step 0b.1）：`fragileCard`（最脆弱的假設）隨 `why` panel 退役
    // ——它列的是估值假設的敏感度，那個模型不在了。
    // ⚠ 2026-09-30（Step 3.7）：`disproofCard` 搬出稽核區、換成論證層的 downsideCard（每條反證連 watch）；
    // 稽核區補上財務三題的數字（值、來源、as of、口徑、規則，或缺席分型）。
    [blockerCard(payload), threeQuestionsCard(view), versusMarketCard(view), pageFillCard(payload)]
      .forEach((card) => { if (card) box.appendChild(card); });
    return box;
  });
  auditDrill.id = 'audit-drill';
  audit.appendChild(auditDrill);
  app.appendChild(audit);

  // 完整細節：**一個展開，展開後就是全部**。先前這裡是七個 details，每個裡面還有第二層
  // details，摘要一律寫著「展開：某某（N 項）」——那是把東西收乾淨，然後叫人再點一次。
  const details = el('section', 'panel');
  details.appendChild(el('h2', null, '完整細節'));
  details.appendChild(el('p', 'note',
    '稽核用：同一份判讀的每一格。點一次就全部攤開，裡面沒有第二層展開，' +
    '也沒有任何一列會叫你「見下方展開」。'));
  details.appendChild(drill('展開完整細節（現價／賭注／下檔／我們與市場／研究現況／判讀狀態／新鮮度）',
    () => {
      const box = el('div', 'full-detail');
      box.appendChild(renderHeadline(view));
      box.appendChild(renderBet(view));
      box.appendChild(renderFundamental(view));
      // ⚠ 2026-09-23（Phase 0 Step 0b.1）：`renderWhy` 與 `renderEntry` 隨兩個 panel 退役。
      box.appendChild(renderResearch(view));
      box.appendChild(renderReadiness(payload));
      box.appendChild(renderFreshness(payload));
      const limits = el('section', 'panel');
      limits.appendChild(el('h2', null, '這份判讀不是什麼'));
      limits.appendChild(listOf(view.limits || []));
      if (view.warnings && view.warnings.length) {
        limits.appendChild(el('div', 'group-title', `組裝時的警告（${view.warnings.length}）`));
        limits.appendChild(listOf(view.warnings));
      }
      box.appendChild(limits);
      return box;
    }));
  app.appendChild(details);
  window.scrollTo(0, 0);
}

/* ---------- 結構表（structure_table state；照抄 structure_table() 的輸出，不重排、不加權、沒有名次） ----------
   ⚠ 2026-09-23（Phase 0 Step 0b.3）：這一頁原本是「瓶頸排序」（首選、可行動／純結構兩份序、產業別分組、
   落差註記）；跨檔排序退役（G1／L19）後只剩逐邊的結構事實。列序是 (company_id, relation, bottleneck)
   字典序——索引不是名次，畫面上沒有 # 欄。籃子頁與多年視角頁（0a.2 退役 kind）的程式碼同批移除。 */

let TABLE_VOCAB = null;

function markNav(name) {
  document.querySelectorAll('.nav a').forEach((link) => {
    const active = link.dataset.view === name;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
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

/** sole_source 是三態：true／false／null。**null 是「未填」，不是 false**——畫面必須分得出來。 */
function soleSourceBadge(value) {
  const table = (TABLE_VOCAB && TABLE_VOCAB.sole_source_states) || {};
  let text; let key;
  if (value === true) { text = '獨家供應'; key = 'true'; }
  else if (value === false) { text = '有第二來源'; key = 'false'; }
  else { text = '沒人說過是不是獨家'; key = 'null'; }
  const badge = el('span', 'badge ' + (value === true ? 'badge-sole' : 'badge-absence'), text);
  badge.title = table[key] || '';
  return badge;
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

/* 關係動詞寫成人話，原始 label 附在 title 供查圖（判準：望文生義還是要查表）。 */
const RELATION_PLAIN = { supplies_to: '供貨給', depends_on: '依賴', constrained_by: '受限於' };

/** 節點的人話名字（materialize 時從圖取）；圖裡沒有名字才印 ID——不從 ID 猜名字。ID 一律放 title。 */
function nodeLabel(name, id) {
  const node = name ? el('span', 'node-name', name) : el('code', null, id);
  node.title = `圖裡的節點 ID：${id}（可貼回來查）`;
  return node;
}

function edgeCell(row) {
  const cell = el('td', 'rank-edge');
  const verb = el('div', 'dim', RELATION_PLAIN[row.relation] || row.relation);
  verb.title = row.relation;
  cell.appendChild(verb);
  cell.appendChild(nodeLabel(row.bottleneck_name, row.bottleneck));
  return cell;
}

function subCell(row) {
  const cell = el('td', 'rank-sub');
  const hasSub = row.substitutability !== null && row.substitutability !== undefined;
  cell.appendChild(el('span', 'sub-score', hasSub ? `${row.substitutability}/5` : '未填'));
  cell.appendChild(document.createTextNode(' '));
  cell.appendChild(soleSourceBadge(row.sole_source));
  // Phase 6 Step 6.5：**這個值本身**（贏得 sub 值的那一筆）的引文撐不撐得住——旗標跟著值走，只標、不改值。
  if (row.sub_language_in_quote === false) {
    const own = el('div', 'dim', '⚠ 這個值的引文沒談可替代性');
    own.title = row.sub_assertion_id || '';
    cell.appendChild(own);
  }
  // Phase 4 Step 4.4b：這條邊上帶 sub 的每一筆裡，引文沒有任何一個字在談可替代性的筆數（id 在滑鼠提示裡，指得回原文）。
  const without = row.assertions_without_sub_language || [];
  if (without.length) {
    const flag = el('div', 'dim', `引文沒談可替代性 ${without.length} 筆`);
    flag.title = without.join('\n');
    cell.appendChild(flag);
  }
  return cell;
}

function anchorCell(row) {
  const cell = el('td', 'rank-anchor');
  if (row.demand_anchor) {
    cell.appendChild(nodeLabel(row.demand_anchor_name, row.demand_anchor));
    // Phase 6 Step 6.7a：錨逐列——這一列的節點走不到、退回從公司走的，標「公司層」（字彙在滑鼠提示，來自 artifact）。
    const company = row.anchor_basis === 'company';
    const hops = el('div', 'dim', company ? `公司層｜公司離它 ${row.demand_hops} 步` : `離它 ${row.demand_hops} 步`);
    if (row.anchor_basis_label) hops.title = row.anchor_basis_label;
    cell.appendChild(hops);
  } else {
    cell.appendChild(el('span', 'badge badge-blocked', '🔴 找不到誰在花錢'));
  }
  return cell;
}

function hopsText(row) {
  return (row.demand_hops === null || row.demand_hops === undefined) ? '—' : `${row.demand_hops} 跳`;
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

/* 沒有 # 欄：列序是索引不是名次。 */
const TABLE_COLUMNS = [
  { title: '標的', cell: companyCell },
  { title: '卡在哪一層', cell: edgeCell },
  { title: '有多難換掉', cell: subCell },
  { title: '證據強度', cell: (row) => { const c = el('td', 'nowrap', row.evidence_label || row.evidence); c.title = row.evidence; return c; } },
  { title: '合格狀態', cell: (row) => el('td', 'nowrap', row.qualification_status || '—') },
  { title: '離花錢的人幾步', cell: (row) => el('td', 'nowrap', hopsText(row)) },
  { title: '誰在花錢', cell: anchorCell },
];

/* 需求鏈：每一列「誰在花錢 → 這一列卡在哪的節點」（公司層的列 → 這家公司）。節點名取 artifact 的 `chain_names`，沒有才印 ID。 */
function chainList(rows, notes) {
  const ul = el('ul', 'notes');
  rows.forEach((row) => {
    const li = el('li', null, `${row.ticker || row.company_label || row.company_id} ${RELATION_PLAIN[row.relation] || row.relation} `
      + `${row.bottleneck_name || row.bottleneck}`);
    li.title = `${row.company_id} ${row.relation} ${row.bottleneck}`;
    const sub = el('div', 'dim');
    if (row.chain && row.chain.length) {
      sub.textContent = row.chain.map((id, i) => (row.chain_names || [])[i] || id).join(' → ')
        + `　（距需求端 ${row.demand_hops} 跳${row.anchor_basis === 'company' ? '；公司層' : ''}）`;
      sub.title = row.chain.join(' → ');
    }
    else sub.appendChild(mdInline(notes.no_anchor_chain || ''));
    li.appendChild(sub);
    ul.appendChild(li);
  });
  return ul;
}

async function renderStructureTable() {
  markNav('structure-table');
  let payload;
  try {
    payload = await getJSON(`${API}/structure-table`);
  } catch (err) {
    renderStateError(err, '讀不到結構表');
    return;
  }
  TABLE_VOCAB = payload.vocab || {};
  const detailSet = new Set(payload.analyst_view_tickers || []);
  const notes = payload.notes || {};
  const rows = payload.rows || [];
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';

  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.title));
  const badges = el('div', 'badges');
  const pit = payload.point_in_time || {};
  badges.appendChild(el('span', 'badge badge-fresh', pit.mode === 'as_of' ? `as-of ${payload.as_of}` : '現況'));
  if (payload.freshness && payload.freshness.state === 'stale') {
    const b = el('span', 'badge badge-stale', 'stale');
    b.title = payload.freshness.rule;
    badges.appendChild(b);
  }
  head.appendChild(badges);
  app.appendChild(head);
  // 2026-10-07 使用者回饋（「結構表可以留但我不知道怎麼查」）：一句什麼時候用它。
  app.appendChild(el('p', 'note', '什麼時候用：想知道某一層（例如 CW 雷射、快接頭）有哪幾家在供貨、'
    + '從需求端走到這一層經過哪幾層——用下面的「只看某一層」挑；想看一家公司坐在哪幾層，用公司名搜。'));

  // ① 已知限制：契約說「解讀前必讀」，所以不摺疊。
  const limits = el('section', 'panel');
  limits.appendChild(el('h2', null, '🔴 已知限制，解讀前必讀'));
  const ol = el('ol', 'limits');
  (payload.limitations || []).forEach((text) => {
    const li = el('li');
    li.appendChild(mdInline(text));
    ol.appendChild(li);
  });
  limits.appendChild(ol);
  const cov = payload.coverage || {};
  limits.appendChild(el('p', 'note',
    `EdgeAssertion ${cov.assertions} → canonical edge ${cov.canonical_edges}（去重收斂 ${cov.duplicate_collapse} 筆）` +
    `｜substitutability 有值 ${cov.edges_with_substitutability}/${cov.canonical_edges}` +
    `｜lead time 有值 ${cov.edges_with_lead_time} 條`));
  const subLanguage = payload.sub_language;
  limits.appendChild(el('p', 'note', subLanguage
    ? `sub 引文不含可替代性語言 ${subLanguage.without}/${subLanguage.checked} 筆帶 sub 的 assertion（字表 ${subLanguage.language}；只印、不放閘——量的是措辭，不是 sub 對不對）`
    : 'sub 引文不含可替代性語言：這份結構表沒有核對（請重跑 materialize --structure-table）'));
  // 層計數器（Phase 4 Step 4.4c）：graph_walk artifact 的 layer_stats.summary 照抄——前端不重算、不重組（L16）。
  try {
    const walk = await getJSON(`${API}/graph-walk`);
    const layer = walk.layer_stats;
    limits.appendChild(el('p', 'note', layer && layer.summary
      ? layer.summary
      : '層：graph_walk artifact 沒有 layer_stats（請重跑 materialize --graph-walk）——不是 0'));
  } catch (err) {
    limits.appendChild(el('p', 'note', '層：讀不到 graph_walk artifact（upstream_unavailable）——不是 0'));
  }
  app.appendChild(limits);

  // ② 結構表：全部列、沒有名次、沒有首選。
  // 2026-09-30 使用者回饋（「結構表是死的頁面」）：加搜尋（代號／公司／層的名字）與依層篩選——**只篩、不重排**，
  // 列序照舊是 materialize 當下的索引；篩掉幾條照印（INV-3 的可見面）。
  const sec1 = el('section', 'panel');
  sec1.appendChild(el('h2', null, `結構表（${rows.length} 條邊）——卡在哪、多難繞、誰在花錢`));
  if (notes.order) sec1.appendChild(mdParagraph(notes.order, 'panel-questions'));
  if (rows.length) {
    const controls = el('div', 'table-filter');
    const search = el('input');
    search.type = 'search';
    search.placeholder = '搜尋代號、公司或層（例：AXTI、InP）';
    search.setAttribute('aria-label', '搜尋結構表');
    const layerSelect = el('select');
    layerSelect.setAttribute('aria-label', '只看某一層');
    layerSelect.appendChild(el('option', null, '全部的層'));
    layerSelect.firstChild.value = '';
    // 層的選項由 materialize 端給（依名字字母）：前端一律不排序，這個檔連排序呼叫都是禁字。
    (payload.layers || []).forEach((layer) => {
      const option = el('option', null, `${layer.name || layer.id}（${layer.edges}）`);
      option.value = layer.id;
      layerSelect.appendChild(option);
    });
    const shown = el('div', 'dim table-filter-count');
    controls.appendChild(search);
    controls.appendChild(layerSelect);
    controls.appendChild(shown);
    sec1.appendChild(controls);
    const holder = el('div');
    sec1.appendChild(holder);
    const haystack = (row) => [row.ticker, row.company_label, row.company_id, row.bottleneck_name, row.bottleneck,
      row.demand_anchor_name, row.demand_anchor].filter(Boolean).join(' ').toLowerCase();
    const apply = () => {
      const q = search.value.trim().toLowerCase();
      const layer = layerSelect.value;
      const picked = rows.filter((row) => (!layer || row.bottleneck === layer) && (!q || haystack(row).includes(q)));
      holder.textContent = '';
      if (picked.length) holder.appendChild(rankTable(picked, TABLE_COLUMNS, detailSet));
      else holder.appendChild(el('p', 'empty', '這張表沒有符合的邊——清掉搜尋字或換一層再看'));
      // 需求鏈（原本是「展開：每一列的鏈路」摺疊，兩百多列沒人看）：挑了層或搜了公司，才列那幾條從需求端走過來的路。
      if ((q || layer) && picked.length) {
        holder.appendChild(el('div', 'group-title', `這 ${picked.length} 條的需求鏈（誰在花錢 → … → 卡在哪的節點）`));
        holder.appendChild(chainList(picked, notes));
      } else if (!q && !layer) {
        holder.appendChild(el('p', 'note', '挑一層或搜一家公司，表下面就會列出那幾條從需求端走過來的鏈路。'));
      }
      shown.textContent = (q || layer) ? `顯示 ${picked.length}／${rows.length} 條（篩掉 ${rows.length - picked.length} 條）` : `全部 ${rows.length} 條`;
    };
    search.addEventListener('input', apply);
    layerSelect.addEventListener('change', apply);
    apply();
  } else {
    sec1.appendChild(el('p', 'empty', '（母體為空：沒有任何公司→向下的邊）'));
  }
  // 「需求錨」那一欄的讀法跟著表走（Phase 6 Step 6.7a；文字住 query.bottleneck.ANCHOR_COLUMN_NOTE）。
  if (notes.anchor_column) sec1.appendChild(mdParagraph(notes.anchor_column));
  if (notes.no_anchor_reading) sec1.appendChild(mdParagraph(notes.no_anchor_reading));
  if (notes.table) sec1.appendChild(mdParagraph(notes.table));
  app.appendChild(sec1);

  // ③④ 診斷（2026-10-07 使用者：「不需要給我看的…不是收起來 是拿掉」）：原本兩個面板（走不到需求錨的原因清單、
  // 母體排除理由清單）收成「已知限制」裡的兩行數字——INV-3 的可見面留著（排除了幾條、走不到幾個）；逐條原因與理由
  // 在 artifact 的 `anchor_gaps`／`population` 裡給互動 session 查。⑤ 需求鏈改跟著篩選走（見上面的 `apply`）。
  const gaps = payload.anchor_gaps || {};
  limits.appendChild(el('p', 'note', gaps.population
    ? `瓶頸節點走不到需求錨：${gaps.without_anchor}／${gaps.population} 個（診斷，不改表）`
    : '瓶頸節點走不到需求錨：母體為 0（圖空或查詢失敗），這一格沒有東西可算'));
  const pop = payload.population || {};
  limits.appendChild(el('p', 'note', `母體：圖裡的邊 ${pop.input}｜收進表 ${pop.accepted}｜不是「公司→向下」的邊 ${pop.excluded}`));

  // ⑥ 視角與新鮮度：as-of 排除的 assertion 計數不得消失（INV-3）。
  if (pit.excluded) {
    const sec5 = el('section', 'panel');
    sec5.appendChild(el('h2', null, '這份表的視角'));
    const kvs = el('div', 'rows');
    kvs.appendChild(kv('視角', pit.mode === 'as_of' ? `as-of ${payload.as_of}` : '現況'));
    kvs.appendChild(kv('as-of 視角排除的 assertion', JSON.stringify(pit.excluded)));
    sec5.appendChild(kvs);
    app.appendChild(sec5);
  }
  app.appendChild(stateFooter(payload));
  window.scrollTo(0, 0);
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
   量化圖只畫系統裡的數字（三題稽核區的值照抄，不另算）；圖上不加標題，看點寫在上方那一句讀法、口徑寫在圖下那一行；
   圖上的字不准互相重疊——由 `?selfcheck=1` 機械量測（selfCheck），0 才算過（S5c）。
   放哪一塊照 page_schema：B6 怎麼被定價＝參考尺、B7 押對了夠大嗎（「出現在數字裡」）＝營收柱狀。
   SVG 元素用資產配置那一段既有的 `svgEl`／`SVG_NS`（同一份，不另寫）。 */

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

function blockVisuals(payload, view, key) {
  const out = [];
  if (key === 'B4') (payload.diagrams || []).forEach((d) => out.push(diagramFigure(d)));
  if (key === 'B6') { const n = rulerChart(view); if (n) out.push(n); }
  if (key === 'B7') { const n = revenueBars(view); if (n) out.push(n); }
  return out;
}

/** 技術示意圖（B4 與層說明頁共用）：研究 session 畫的 SVG，materialize 檢查過才嵌、編成 data URI；
 *  用 <img> 顯示（SVG 在 img 裡不執行任何東西）。規則 6：標「示意」、附出處——出處摺起來，第一眼只看圖。 */
function diagramFigure(d) {
  const box = el('div', 'diagram');
  box.appendChild(el('div', 'diagram-title', d.title || '示意圖'));
  const img = document.createElement('img');
  img.className = 'diagram-img';
  img.src = d.src;
  img.alt = `示意圖：${d.title || ''}`;
  img.loading = 'lazy';
  box.appendChild(img);
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

/** 參考尺：自家三年倍數的最低、中位、最高與今天；同組中位只在同口徑時畫。對數刻度——倍數常跨兩個數量級
 *  （AXTI 三年 P/S 0.53 → 96），線性尺會把中位擠到邊上。圖上只標兩端與今天，中位與組中位寫在圖下（避免字疊字）。 */
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
  const values = [det.min, det.max, det.median, det.multiple_today].concat(cohort ? [cohort.value] : []);
  const lo = Math.min(...values) / 1.2;
  const hi = Math.max(...values) * 1.2;
  const L = 8, R = 312, Y = 30;
  const x = (v) => L + (Math.log(v) - Math.log(lo)) / (Math.log(hi) - Math.log(lo)) * (R - L);
  const svg = svgEl('svg', { viewBox: '0 0 320 58', class: 'chart chart-ruler', role: 'img',
    'aria-label': `自家三年 ${basis} 的位置` });
  svg.appendChild(svgEl('line', { x1: x(det.min), y1: Y, x2: x(det.max), y2: Y, class: 'ruler-range' }));
  svg.appendChild(svgEl('line', { x1: x(det.median), y1: Y - 8, x2: x(det.median), y2: Y + 8, class: 'ruler-median' }));
  if (cohort) {
    const cx = x(cohort.value);
    svg.appendChild(svgEl('path', { d: `M${cx} ${Y - 7}L${cx + 6} ${Y}L${cx} ${Y + 7}L${cx - 6} ${Y}Z`, class: 'ruler-cohort' }));
  }
  const tx = x(det.multiple_today);
  svg.appendChild(svgEl('circle', { cx: tx, cy: Y, r: 5.5, class: 'ruler-today' }));
  const todayText = `今天 ${fmtMultiple(det.multiple_today)}`;
  const anchor = tx < 60 ? 'start' : tx > 260 ? 'end' : 'middle';
  svg.appendChild(svgEl('text', { x: anchor === 'start' ? Math.max(L, tx - 6) : anchor === 'end' ? Math.min(R, tx + 6) : tx,
    y: Y - 13, 'text-anchor': anchor, class: 'chart-label chart-label-strong' }, todayText));
  svg.appendChild(svgEl('text', { x: L, y: Y + 22, 'text-anchor': 'start', class: 'chart-label' }, `最低 ${fmtMultiple(det.min)}`));
  svg.appendChild(svgEl('text', { x: R, y: Y + 22, 'text-anchor': 'end', class: 'chart-label' }, `最高 ${fmtMultiple(det.max)}`));
  const wrap = el('div', 'chart-wrap');
  wrap.appendChild(svg);
  const legend = [`● 今天＝自家三年第 ${fmtNumber(d.value, 1)} 百分位`, `│ 中位 ${fmtMultiple(det.median)}`];
  if (cohort) {
    const cdet = (cohort.dependencies || {}).detail || {};
    legend.push(`◆ 同組中位 ${fmtMultiple(cohort.value)}（${cdet.theme || '主題等權組'}，${cdet.n_same_basis || '?'}／${cdet.n_members || '?'} 檔同口徑）`);
  } else {
    legend.push('◆ 同組中位：沒有同口徑的主題等權組');
  }
  const window_ = det.window_start && det.window_end ? `${String(det.window_start).slice(0, 10)} → ${String(det.window_end).slice(0, 10)}` : '三年';
  legend.push(`${basis}、對數刻度、${window_}${det.samples ? `、${det.samples} 個樣本` : ''}`);
  wrap.appendChild(el('div', 'chart-legend', legend.join('　')));
  return wrap;
}

/** 營收柱狀：最近 12 期（台股月營收、EDGAR 季營收照抄三題③的序列）；柱高＝營收、顏色＝年增正負。
 *  圖上只標最新一期的年增與首尾兩期的期別，其餘寫在圖下（避免字疊字）。 */
function revenueBars(view) {
  const line = tqLine(view, ':in_numbers_series');
  const d = line && line.datum;
  if (!d || d.status !== 'available' || !Array.isArray(d.value) || d.value.length < 2) return null;
  const pts = d.value.slice(-12).map((p) => ({
    label: p.data_month || String(p.period_end || '').slice(0, 7),
    value: typeof p.revenue_twd_thousand === 'number' ? p.revenue_twd_thousand * 1000 : p.value,
    yoy: typeof p.yoy === 'number' ? p.yoy : null,
  }));
  if (pts.some((p) => typeof p.value !== 'number' || !isFinite(p.value))) return null;
  const max = Math.max(...pts.map((p) => p.value));
  if (!(max > 0)) return null;
  const top = 18, bottom = 92, L = 6, R = 314;
  const step = (R - L) / pts.length;
  const barW = Math.max(4, step - 9);   // 柱寬＝每格寬減固定間距（8 季約 30px、12 個月約 17px）
  // 座標換算（同資產配置那段的 pct()／meter()）：營收 → 柱高 px，不是任何財務算術。
  const barHeight = (amount) => Math.max(1, (amount / max) * (bottom - top));
  const svg = svgEl('svg', { viewBox: '0 0 320 112', class: 'chart chart-bars', role: 'img', 'aria-label': '營收與年增' });
  svg.appendChild(svgEl('line', { x1: L, y1: bottom, x2: R, y2: bottom, class: 'chart-axis' }));
  pts.forEach((p, i) => {
    const h = barHeight(p.value);
    const cx = L + step * (i + 0.5);
    const klass = p.yoy == null ? 'bar' : p.yoy >= 0 ? 'bar bar-pos' : 'bar bar-neg';
    svg.appendChild(svgEl('rect', { x: cx - barW / 2, y: bottom - h, width: barW, height: h, rx: 1.5, class: klass }));
    if (i === pts.length - 1 && p.yoy != null) {
      svg.appendChild(svgEl('text', { x: Math.min(R, cx + barW / 2), y: Math.max(11, bottom - h - 5), 'text-anchor': 'end',
        class: 'chart-label chart-label-strong' }, `年增 ${fmtPercent(p.yoy)}`));
    }
  });
  svg.appendChild(svgEl('text', { x: L, y: bottom + 15, 'text-anchor': 'start', class: 'chart-label' }, pts[0].label));
  svg.appendChild(svgEl('text', { x: R, y: bottom + 15, 'text-anchor': 'end', class: 'chart-label' }, pts[pts.length - 1].label));
  const wrap = el('div', 'chart-wrap');
  wrap.appendChild(svg);
  const recent = pts.slice(-3).map((p) => `${p.label} ${p.yoy == null ? '—' : fmtPercent(p.yoy)}`).join('、');
  const last = pts[pts.length - 1];
  const det = (d.dependencies && d.dependencies.detail) || {};   // 幣別由序列自己帶（三題③），這裡只翻成中文
  const ccy = det.currency ? (CURRENCY_WORD[det.currency] || det.currency)
    : (Array.isArray(det.currencies) && det.currencies.length ? `（幣別混合：${det.currencies.join('／')}）` : '（幣別未標）');
  const amount = `${fmtBig(last.value) || '—'}${ccy.startsWith('元') || ccy.startsWith('（') ? '' : ' '}${ccy}`;
  const legend = [`柱高＝營收（最新一期 ${amount}）`, `顏色＝年增正負（最近三期：${recent}）`];
  if (d.dependencies && d.dependencies.basis) legend.push(`來源：${d.dependencies.basis}`);
  wrap.appendChild(el('div', 'chart-legend', legend.join('　')));
  return wrap;
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

function signedPct(value, digits) {
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

/* ---------- 走圖（graph_walk state）與在等什麼（watches state） ----------
   兩頁都是「計數＋清單」——依 dataviz 的 form heuristic，>7 類且每類都有意義時用表格／清單，
   不是更多顏色；九型的「命中／母體」用 KPI stat tile。**這裡沒有圖表、沒有排序、沒有加總**：
   九格各自一格，型別順序是閱讀順序（plan 2026-09-25-001 §0 第 7 條）。 */

function kpiRow(items) {
  const row = el('div', 'tiles');
  items.forEach((it) => row.appendChild(tile(it.label, it.value, it.sub, it.cls)));
  return row;
}

/* 一對重複節點候選。**逐字是主角**：2026-09-18 之前圖裡只有 id 與 name，而兩者都是抽取時
   LLM 取的——用它們判重複等於用 label 驗 label。所以每一端都要印得出它自己的逐字（L18）。 */
function duplicateSide(side) {
  const box = el('div', 'pair-side');
  if (!side) return box;
  const head = el('div');
  head.appendChild(el('code', null, side.node));
  if (side.name) head.appendChild(el('span', 'dim', '　' + side.name));
  box.appendChild(head);
  box.appendChild(el('span', 'rule',
    `${side.abstraction_level || '—'}｜邊 ${side.degree}｜逐字 ${side.quote_count} 段`));
  (side.quotes || []).forEach((q) => {
    const quote = el('div', 'verbatim', q.quote);
    if (q.locator) quote.appendChild(el('div', 'src', q.locator));
    box.appendChild(quote);
  });
  const hidden = (side.quote_count || 0) - (side.quotes || []).length;
  if (hidden > 0) box.appendChild(el('span', 'rule', `…另有 ${hidden} 段逐字（python -m query.structure ${side.node} --quotes）`));
  if (!side.quote_count) box.appendChild(el('span', 'rule', '⚠ 這個節點一段逐字都沒有——它可能是抽取副產品，不是實體'));
  return box;
}

function walkFraction(q) {
  if (q.absence) return q.absence.kind;
  return `${q.hit_n}／${q.scope_n}`;
}

function walkHitList(q) {
  const list = el('ul', 'weak');
  (q.hits || []).forEach((hit) => {
    const li = el('li');
    li.appendChild(mdInline(hit.text || ''));
    if (q.key === 'duplicate_node') {
      li.appendChild(el('span', 'rule', (hit.rules || []).join('＋') + '｜' + (hit.same_abstraction_level ? '同層' : '不同層')));
      li.appendChild(duplicateSide(hit.left));
      li.appendChild(duplicateSide(hit.right));
    } else if (hit.suppliers && hit.suppliers.length) {
      li.appendChild(el('span', 'rule', '供給側：' + hit.suppliers.join('、')));
    } else if (hit.supplier) {
      li.appendChild(el('span', 'rule', `供給側：${hit.supplier}｜證據：${hit.evidence_label || '—'}`));
    } else if (hit.indirect && hit.indirect.length) {
      li.appendChild(el('span', 'rule', '間接相連：' + hit.indirect.slice(0, 6).join('、')));
    } else if (hit.supplies && hit.supplies.length) {
      li.appendChild(el('span', 'rule', '往下供貨：' + hit.supplies.join('、')));
    } else if (hit.first_seen) {
      li.appendChild(el('span', 'rule', `首見 ${hit.first_seen}${hit.title ? '｜' + hit.title : ''}`));
    }
    if (hit.demand && hit.demand.length) li.appendChild(el('span', 'rule', '需求側：' + hit.demand.join('；')));
    // Phase 6 Step 6.5：撐住需求側 sub 值的引文有沒有在談可替代性——artifact 給的那一句照抄，前端不重算（L16）
    if (hit.demand_quote_note) li.appendChild(el('span', 'rule', hit.demand_quote_note));
    list.appendChild(li);
  });
  return list;
}

async function renderGraphWalk() {
  markNav('graph-walk');
  let payload;
  try {
    payload = await getJSON(`${API}/graph-walk`);
  } catch (err) {
    renderStateError(err, '讀不到走圖');
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

  const questions = payload.questions || [];
  const sec0 = el('section', 'panel');
  sec0.appendChild(el('h2', null, '九個問句，各自「命中／母體」——不加總、不排序'));
  sec0.appendChild(kpiRow(questions.map((q) => ({
    label: `${q.order}. ${q.short}`,
    value: walkFraction(q),
    sub: q.absence ? '這次沒讀到——不是 0' : (q.judged ? (q.always_on ? '⚠ 恆亮（≥50%）' : '母體 ≥10') : '母體 <10，只印不判'),
  }))));
  app.appendChild(sec0);

  questions.forEach((q) => {
    const sec = el('section', 'panel');
    sec.appendChild(el('h2', null, `${q.order}. ${q.short}（${walkFraction(q)}）`));
    sec.appendChild(el('div', 'panel-questions', `母體：${q.scope_rule}｜命中：${q.hit_rule}`));
    sec.appendChild(el('p', 'note', '下一步：' + q.next_action));
    if (q.absence) {
      sec.appendChild(el('p', 'warn', '▲ ' + q.absence.reason));
      app.appendChild(sec);
      return;
    }
    if ((q.hits || []).length) sec.appendChild(walkHitList(q));
    else sec.appendChild(el('p', 'note', '這一型今天沒有命中（母體照印在上面）。'));
    const extra = q.extra || {};
    if ((extra.unresolved_names || []).length) {
      sec.appendChild(el('p', 'note',
        `另有 ${extra.unresolved_names.length} 個名字 registry 解析不到（不算命中；ID 沒解析對 ≠ 圖中真無此公司）：`
        + extra.unresolved_names.join('、')));
    }
    const ambiguous = Object.entries(extra.ambiguous_names || {});
    if (ambiguous.length) {
      sec.appendChild(el('p', 'note',
        `另有 ${ambiguous.length} 個名字去掉交易所後綴後對到多家（不解析、不猜）：`
        + ambiguous.map(([name, cands]) => `${name}→${cands.join('／')}`).join('、')));
    }
    // 2026-10-07（使用者：「不需要給我看的…拿掉」）：prod: 抽取副產品與 registry note 提過的那幾對不再印——
    // 它們不在母體、不算命中，是給互動 session 查的（artifact 的 `extra` 照樣帶著）。
    if ((extra.withdrawn || []).length) sec.appendChild(el('p', 'note', '有紀錄但已全部撤回（不在母體）：' + extra.withdrawn.join('、')));
    app.appendChild(sec);
  });

  app.appendChild(stateFooter(payload));
  window.scrollTo(0, 0);
}

/* ---------- 讀圖（structure_readings state）與個股頁的讀圖面板（Phase 2 Step 2.7） ----------
   讀圖是研究判斷（A3）：這裡照抄 ledger 寫下的判讀、單位、引文與反證，加上 materialize 當下與圖比對的**狀態**。
   不排序、不打分：列序是（節點, 單位）字典序；沒有讀圖的節點不列——那是走圖第 1 型的事。 */

const READING_STATUS_TEXT = {
  current: '現行', stale: '跟圖不一致（該重讀）', stale_low: '只有證據等級變了（不必重讀）', expired: '過期（該重讀）',
};

function readingsCard(view) {
  const panel = view.readings;
  if (!panel) return null;
  const node = panelShell(panel, '讀圖：它坐的那一層結構變了沒');
  const hint = plainPanel('readings', panel.title).hint;
  if (hint) node.appendChild(mdParagraph(hint));
  if (!(panel.lines || []).length) {
    node.appendChild(el('p', 'note', panel.reason || '還沒有讀圖'));
    // 多數坐的層還沒有讀圖，但可能已經有層說明——沒讀圖這條路也要連得過去（個股頁 plan S4b）
    const links = layerNoteLinks(panel.context || {});
    if (links) node.appendChild(links);
    return node;
  }
  node.appendChild(renderRows(panel.lines));
  const glossary = unitGlossary();
  if (glossary) node.appendChild(glossary);
  const seats = (panel.context || {}).seats || [];
  if (seats.length) node.appendChild(el('p', 'note', '圖上它供貨或開發的節點：' + seats.join('、')));
  const links = layerNoteLinks(panel.context || {});
  if (links) node.appendChild(links);
  node.appendChild(el('p', 'note', '完整的引文與反證在「讀圖」頁（#/structure-readings）。'));
  return node;
}

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

function readingRow(row) {
  const li = el('li');
  const head = el('div');
  head.appendChild(el('code', null, row.node));
  head.appendChild(el('span', 'dim', `　${row.unit === 'socket' ? '插槽' : '層'}｜${row.kind || '—'}｜`
    + (READING_STATUS_TEXT[row.status] || '這次沒比對到圖（不是現行）')));
  li.appendChild(head);
  li.appendChild(el('span', 'rule', `讀於 ${row.read_on || '—'}｜到期 ${row.expires || '—'}｜${row.reading_id || ''}`
    + ((row.tickers || []).length ? '｜' + row.tickers.join('、') : '')));
  if (row.reason) li.appendChild(el('span', 'rule', '狀態理由：' + row.reason));
  (row.reread_reasons || []).forEach((r) => li.appendChild(el('span', 'rule', '重讀理由：' + r)));
  if (row.reading) li.appendChild(el('p', 'note', row.reading));
  (row.citations || []).forEach((c) => {
    const quote = el('div', 'verbatim', c.quote);
    quote.appendChild(el('div', 'src', `${c.angle}｜${(c.edge || []).join(' ')}｜${c.source_id}`
      + (c.independent ? '｜外部印證' : '')));
    li.appendChild(quote);
  });
  (row.disproof || []).forEach((d) => {
    li.appendChild(el('span', 'rule', `反證／確認條件：${d.condition}（出處 ${d.source || '—'}｜`
      + `${d.watch_id ? 'watch ' + d.watch_id + '（' + (d.watch_status || '?') + '）' : '沒有登記 watch'}）`));
  });
  return li;
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

async function renderStructureReadings() {
  markNav('structure-readings');
  let payload;
  try {
    payload = await getJSON(`${API}/structure-readings`);
  } catch (err) {
    renderStateError(err, '讀不到讀圖');
    return;
  }
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';
  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.title));
  app.appendChild(head);

  const c = payload.counts || {};
  const rows = (payload.rows || []).filter((r) => r.reading_id);
  const sec0 = el('section', 'panel');
  sec0.appendChild(el('h2', null, `現行讀圖 ${rows.length} 份（層 ${rows.filter((r) => r.unit !== 'socket').length}`
    + `／插槽 ${rows.filter((r) => r.unit === 'socket').length}）`));
  sec0.appendChild(kpiRow([
    { label: '現行', value: String(c.current || 0), sub: '與圖一致、未到期' },
    { label: '該重讀', value: String((payload.needs_reread || {}).n || 0), sub: '跟圖不一致、過期或被叫醒', cls: 'hero' },
    { label: '只有證據等級變', value: String(c.stale_low || 0), sub: '記錄，不必重讀' },
    { label: '過期', value: String(c.expired || 0), sub: '到期未重讀' },
  ]));
  app.appendChild(sec0);

  const sec1 = el('section', 'panel');
  sec1.appendChild(el('h2', null, '每一份讀圖（節點 × 單位；依節點字典序，不是名次）'));
  const list = el('ul', 'weak');
  rows.forEach((row) => list.appendChild(readingRow(row)));
  sec1.appendChild(list);
  const withdrawn = (payload.rows || []).filter((r) => !r.reading_id);
  if (withdrawn.length) {
    sec1.appendChild(el('p', 'note', '有紀錄但已全部撤回：' + withdrawn.map((r) => `${r.node}（${r.unit || '全部單位'}）`).join('、')));
  }
  app.appendChild(sec1);

  app.appendChild(renderPredictions(payload.predictions));

  app.appendChild(stateFooter(payload));
  window.scrollTo(0, 0);
}

function watchRow(row, labels) {
  const li = el('li');
  const head = el('div');
  head.appendChild(el('span', 'ticker-plain', row.detail));
  li.appendChild(head);
  const bits = [];
  if (row.target && row.target.label) bits.push('喚醒 ' + row.target.label);
  if (row.expires) bits.push('到期 ' + row.expires);
  if (row.poll_eligible) bits.push('可主動輪詢' + (row.poll_last_checked ? `（上次查 ${row.poll_last_checked}）` : ''));
  li.appendChild(el('span', 'rule', bits.join('｜')));
  if (row.stalled && labels) li.appendChild(el('span', 'rule', labels.stalled || ''));
  if (row.query_hint) li.appendChild(el('span', 'rule', '查詢提示：' + row.query_hint));
  // watch id 與 kind（內部字彙）不印——你用 pq2 編號跟我說話，watch 由互動 session 用 CLI 處理（2026-10-07：「不需要給我看的…拿掉」）
  return li;
}

function watchList(rows, labels) {
  const list = el('ul', 'weak');
  rows.forEach((row) => list.appendChild(watchRow(row, labels)));
  return list;
}

async function renderWatches() {
  markNav('watches');
  let payload;
  try {
    payload = await getJSON(`${API}/watches`);
  } catch (err) {
    renderStateError(err, '讀不到事件監看');
    return;
  }
  const k = payload.counters || {};
  const notes = payload.notes || {};
  const backlog = payload.trace_backlog || {};
  const labels = backlog.wake_state_labels || {};
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

  const sec0 = el('section', 'panel');
  sec0.appendChild(el('h2', null, '常駐計數器'));
  sec0.appendChild(kpiRow([
    { label: '還在等的事件', value: String(k.active), sub: `其中可主動輪詢 ${k.t2_pollable}`, cls: 'hero' },
    { label: '停滯', value: String(k.stalled), sub: '被動層短期不會再醒' },
    { label: 'fired 未消化', value: String(k.fired_unconsumed), sub: '已觸發、還沒有人處理' },
    { label: '追源需處置', value: String((backlog.needs_attention || []).length), sub: `追源 backlog 共 ${backlog.total}` },
  ]));
  sec0.appendChild(el('p', 'note', `喚醒去處：pq2 ${k.wake_pq2}｜lead ${k.wake_lead}｜假設 ${k.wake_hypothesis}｜反證 ${k.wake_disproof ?? 0}`));
  sec0.appendChild(el('p', 'note', notes.budget || ''));
  app.appendChild(sec0);

  // 反證與確認條件：醒來待檢的先列（要有人判定），在盯的接在後面——分兩組是分區不是排序（artifact 的列序照舊）。
  // 條件原文照 markdown 印（粗體）；watch id 不印（2026-10-07：「不需要給我看的…拿掉」）。
  const semantic = payload.semantic || [];
  if (semantic.length) {
    const secS = el('section', 'panel');
    const woken = semantic.filter((row) => row.status === 'fired');
    const watching = semantic.filter((row) => row.status !== 'fired');
    secS.appendChild(el('h2', null, `反證與確認條件（醒來待檢 ${woken.length}｜在盯 ${watching.length}）`));
    secS.appendChild(el('p', 'note', notes.semantic || ''));
    const conditionList = (rows) => {
      const list = el('ul', 'weak');
      rows.forEach((row) => {
        const li = el('li');
        li.appendChild(mdParagraph(row.condition || row.detail || ''));
        const bits = [row.source_ref, '到期 ' + row.expires];
        if (row.semantic_flag) bits.push('預篩（提示）：' + row.semantic_flag.verdict);
        li.appendChild(el('span', 'rule', bits.filter(Boolean).join('｜')));
        list.appendChild(li);
      });
      return list;
    };
    if (woken.length) {
      secS.appendChild(el('div', 'group-title', `醒來待檢（${woken.length}）——判定只在互動 session`));
      secS.appendChild(conditionList(woken));
    }
    secS.appendChild(el('div', 'group-title', `在盯（${watching.length}）`));
    secS.appendChild(conditionList(watching));
    app.appendChild(secS);
  }

  if ((payload.stalled || []).length) {
    const sec1 = el('section', 'panel callout');
    sec1.appendChild(el('h2', null, `停滯（${payload.stalled.length}）——等下去不會有事發生`));
    sec1.appendChild(el('p', 'note', notes.stalled || ''));
    sec1.appendChild(watchList(payload.stalled, labels));
    app.appendChild(sec1);
  }

  if ((backlog.needs_attention || []).length) {
    const sec2 = el('section', 'panel');
    sec2.appendChild(el('h2', null, `追源 backlog：需要當場處置（${backlog.needs_attention.length}）`));
    const list = el('ul', 'weak');
    backlog.needs_attention.forEach((row) => {
      const li = el('li');
      li.appendChild(el('div', null, truncate(row.title || row.lead_id, 160)));
      const bits = [];
      if (row.wake_state) bits.push(labels[row.wake_state] || row.wake_state);
      if (row.trace_status) bits.push('追源狀態 ' + row.trace_status);
      if (row.expires) bits.push('到期 ' + row.expires);
      li.appendChild(el('span', 'rule', bits.join('｜')));
      if (row.next_trigger) li.appendChild(el('span', 'rule', '下一個 trigger：' + truncate(row.next_trigger, 160)));
      list.appendChild(li);
    });
    sec2.appendChild(list);
    app.appendChild(sec2);
  }

  // 2026-10-07（使用者：「不需要給我看的…不是收起來 是拿掉」）：「全部 N 筆」那個摺疊（兩百多列）拿掉——
  // 在等的總數在最上面的計數器；這裡只列要有人動的：本輪該主動查的、已觸發未消化、已到期（到期是重問不是丟）。
  const fired = payload.fired_unconsumed || [];
  const expired = payload.expired || [];
  const due = payload.due_this_round || [];
  const sec3 = el('section', 'panel');
  sec3.appendChild(el('h2', null, `要有人動的（已觸發未消化 ${fired.length}｜已到期 ${expired.length}｜本輪該主動查 ${due.length}）`));
  if (fired.length) {
    sec3.appendChild(el('div', 'group-title', `已觸發、還沒有人處理（${fired.length}）`));
    sec3.appendChild(watchList(fired, labels));
  }
  if (expired.length) {
    sec3.appendChild(el('div', 'group-title', `已到期（${expired.length}；到期是重問不是丟）`));
    sec3.appendChild(watchList(expired, labels));
  }
  if (due.length) {
    sec3.appendChild(el('div', 'group-title', `本輪該主動查的（${due.length}，依 budget）`));
    sec3.appendChild(watchList(due, labels));
  }
  if (!fired.length && !expired.length && !due.length) sec3.appendChild(el('p', 'note', '0——沒有要人動的等待。'));
  sec3.appendChild(el('p', 'note', notes.fired || ''));
  app.appendChild(sec3);

  app.appendChild(stateFooter(payload));
  window.scrollTo(0, 0);
}

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

function signedPct(value) {
  const text = fmtRatioPct(value, 1);
  return text === null ? '—' : (value > 0 ? '+' : '') + text;
}

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
  app.appendChild(stateFooter(payload));
  window.scrollTo(0, 0);
}

/* ---------- 候選狀態板（candidates state；Phase 3 Step 3.6：推導結果照抄——組內按 ticker 字母，不排序、不給尺寸） ---------- */

const CANDIDATE_ORDER = ['open', 'missing', 'priced_wait', 'pass', 'held'];
/* 押的那份讀圖不是現行的兩種情形（derive_row 分開寫，L12）。 */
const RIDE_GONE_TEXT = { superseded: '那一格現行的已是另一份讀圖（該重寫敘事）', not_found: '這次沒讀到那一格的讀圖列' };
const CANDIDATE_SIDE_ORDER = ['not_multiple', 'edge_unmeasurable', 'legacy', 'precondition_failed'];

function candidateRow(row, detailSet) {
  const li = el('li');
  const top = el('div');
  if (detailSet.has(row.ticker)) {
    const a = el('a', null, row.ticker);
    a.href = `#/${encodeURIComponent(row.ticker)}`;
    top.appendChild(a);
  } else {
    top.appendChild(el('strong', null, row.ticker));
  }
  const w = row.three_words || {};
  top.appendChild(el('span', 'dim', `　會死嗎 ${w.will_it_die || '—'}｜已定價 ${w.priced_in || '—'}｜數字裡 ${w.in_numbers || '—'}`));
  li.appendChild(top);
  const bits = [];
  if (row.declared_label && row.derived !== row.declared) bits.push('敘事宣告：' + row.declared_label);
  // 押在哪一格：節點名（沒有才印 ID）＋單位＋判讀＋那份讀圖現在的狀態——字全由 materialize 端給（2026-09-30）。
  (row.rides || []).forEach((r) => bits.push(`押在「${r.node_name || r.node}」（${r.unit_label || (r.unit === 'socket' ? '插槽' : '層')}`
    + `｜判讀 ${r.kind_label || r.kind || '—'}｜${READING_STATUS_TEXT[r.status] || RIDE_GONE_TEXT[r.status] || r.status || '—'}）`));
  const e = row.edge || {};
  bits.push(`邊緣：${e.label || e.state || '—'}（市值 ${e.market_cap_label || '—'}｜分析師 ${e.analyst_count ?? '—'}）`);
  if (row.watch) {
    bits.push(`在等：${row.watch.until ? row.watch.until + ' 醒來重看' : '沒寫醒來日'}；最晚 ${row.watch.expires || '—'} 到期重問`
      + (row.watch.status !== 'active' ? `（這筆等待目前是「${row.watch.status}」）` : '') + `（${row.watch.watch_id}）`);
  }
  if (row.stall_days !== null && row.stall_days !== undefined) bits.push(`滯留 ${row.stall_days} 天`);
  li.appendChild(el('span', 'rule', bits.join('｜')));
  if (row.reason) li.appendChild(el('span', 'rule', '理由：' + row.reason));
  if (row.note) li.appendChild(el('span', 'rule', row.note));
  if (row.held_source) li.appendChild(el('span', 'rule', `Sheet：${row.held_source.sheet_ticker}（解析：${row.held_source.source}）`));
  confirmLines(row, 'span').forEach((line) => li.appendChild(line));
  sharedBetLines(row, 'span').forEach((line) => li.appendChild(line));
  (row.preconditions || []).forEach((p) => li.appendChild(el('span', 'warn', '▲ 前提失效：' + p)));
  (row.rewrite || []).forEach((p) => li.appendChild(el('span', 'warn', '▲ 該重寫：' + p)));
  if (row.holdings_verified === false) li.appendChild(el('span', 'warn', '持股未驗（可能其實已持有）'));
  return li;
}

async function renderCandidates() {
  markNav('candidates');
  let payload;
  try {
    payload = await getJSON(`${API}/candidates`);
  } catch (err) {
    renderStateError(err, '讀不到候選狀態板');
    return;
  }
  const counts = payload.counts || {};
  const oldest = payload.oldest_stall_days || {};
  const labels = payload.group_labels || {};
  const sideLabels = payload.side_labels || {};
  const holdings = payload.holdings || {};
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

  const sec0 = el('section', 'panel');
  sec0.appendChild(el('h2', null, '各組檔數（0 也印）'));
  const aged = (key) => (counts[key] && oldest[key] !== null && oldest[key] !== undefined) ? `最老滯留 ${oldest[key]} 天` : '';
  sec0.appendChild(kpiRow(CANDIDATE_ORDER.map((key) => ({
    label: labels[key] || key,
    value: (counts[key] === null || counts[key] === undefined) ? '未驗' : String(counts[key]),
    sub: key === 'held' && counts.held === null ? '持股未讀到' : aged(key),
    cls: key === 'open' ? 'hero' : undefined,
  }))));
  sec0.appendChild(el('p', 'note', CANDIDATE_SIDE_ORDER.map((k) => `${sideLabels[k] || k} ${counts[k] ?? 0}`).join('｜')
    + `｜無敘事 ${counts.no_narrative ?? 0}（沒有敘事的不上板）`));
  if (holdings.status !== 'ok') {
    sec0.appendChild(el('p', 'warn', '▲ ' + (holdings.reason || '持股未讀到，已持有判定暫停')));
  } else {
    if ((holdings.unresolved || []).length) {
      sec0.appendChild(el('p', 'note', `持股解析不到 ${holdings.unresolved.length}：${holdings.unresolved.join('、')}（不猜；要不要登記是 identity 的決定）`));
    }
    // 使用者決定不研究（config/holdings_coverage.json，Phase 4 Step 4.7b）：不算「解析不到」，另列並附理由與決定日。
    (holdings.ignored || []).forEach((item) => {
      sec0.appendChild(el('p', 'note', `使用者決定不研究：${item.sheet_ticker}（${item.reason}；${item.decided_at}）`));
    });
    if (holdings.ignored_problem) {
      sec0.appendChild(el('p', 'warn', `▲ 不研究名單讀不到（${holdings.ignored_problem}）——全部照列解析不到`));
    }
  }
  app.appendChild(sec0);

  const section = (title, rows, emptyText) => {
    const sec = el('section', 'panel');
    sec.appendChild(el('h2', null, `${title}（${rows.length}）`));
    if (!rows.length) {
      sec.appendChild(el('p', 'note', emptyText));
    } else {
      const list = el('ul', 'weak');
      rows.forEach((row) => list.appendChild(candidateRow(row, detailSet)));
      sec.appendChild(list);
    }
    app.appendChild(sec);
  };
  const groups = payload.groups || {};
  CANDIDATE_ORDER.forEach((key) => {
    const empty = key === 'open'
      ? '0——可開為零就零；讓它非空的路是研究，不是放寬前提。'
      : (key === 'held' && counts.held === null ? '持股未讀到——已持有判定暫停（不是「沒有持有」）。' : '0');
    section(labels[key] || key, groups[key] || [], empty);
  });
  const sides = payload.side_groups || {};
  CANDIDATE_SIDE_ORDER.forEach((key) => {
    if ((sides[key] || []).length) section(sideLabels[key] || key, sides[key], '0');
  });

  // 沒有敘事、不上板的那幾檔（2026-09-30 使用者回饋「候選板是死的」：原本只有計數，看不到是誰）。
  // 2026-10-07 起清單住首頁的「沒有敘事」那一組（首頁照候選狀態分組）——這裡原本摺著同一份清單，重複就拿掉，只留一句與連結。
  const secX = el('section', 'panel');
  secX.appendChild(el('h2', null, `沒有敘事、不上板（${counts.no_narrative ?? 0}）`));
  const noteX = el('p', 'note', '候選狀態是寫敘事時宣告的——這些檔還沒寫敘事，所以不在上面任何一組。'
    + '要讓一檔上板，路是研究它、寫敘事（研究 session 做），不是這個畫面。是哪幾檔：');
  const homeLink = el('a', null, '首頁「沒有敘事」那一組');
  homeLink.href = '#/';
  noteX.appendChild(homeLink);
  noteX.appendChild(document.createTextNode('（依代號字母，不是名次）。'));
  secX.appendChild(noteX);
  app.appendChild(secX);

  const rewrite = payload.narrative_rewrite || [];
  const secW = el('section', 'panel');
  secW.appendChild(el('h2', null, `敘事該重寫（${rewrite.length}）`));
  if (!rewrite.length) {
    secW.appendChild(el('p', 'note', '0'));
  } else {
    const list = el('ul', 'weak');
    rewrite.forEach((b) => list.appendChild(el('li', null, b.kind === 'link'
      ? `${b.ticker}：連結 ${b.link_source_ref}——${b.label || '已沒有在盯的 watch'}`
      : `${b.ticker}：敘事來源的 watch ${b.watch_id} 醒來／觸及／到期未判`)));
    secW.appendChild(list);
  }
  app.appendChild(secW);

  const ledger = payload.ledger || {};
  if (ledger.present === false) {
    app.appendChild(el('p', 'warn', '▲ 敘事 ledger 目錄不存在——「無敘事」是讀不到，不是真的沒有。'));
  } else if (ledger.parse_errors) {
    app.appendChild(el('p', 'warn', `▲ 敘事 ledger 有 ${ledger.parse_errors} 行解析不了（那幾份宣告沒進板）：${(ledger.parse_error_examples || []).join('；')}`));
  }

  const absentText = (block) => {
    const parts = Object.entries(block.absent || {}).map(([k, v]) => `${k} ${v}`);
    return parts.length ? `（${parts.join('、')}）` : '';
  };
  const roll = payload.rollup || {};
  const secR = el('section', 'panel');
  secR.appendChild(el('h2', null, `三題與四盞燈（${roll.universe ?? '?'} 檔；只數有值與缺席，不是結論）`));
  const own = roll.priced_in_own || {};
  const nums = roll.in_numbers || {};
  const wipe = roll.wipeout || {};
  const lamps = wipe.lamps || {};
  const unlit = Object.entries(wipe.unlit_by_kind || {}).map(([k, v]) => `${k} ${v}`).join('、');
  secR.appendChild(el('p', 'note', `已定價①（自家歷史）有值 ${own.valued ?? '?'}／缺席 ${own.absent_total ?? '?'}${absentText(own)}`));
  secR.appendChild(el('p', 'note', `出現在數字裡 有值 ${nums.valued ?? '?'}／缺席 ${nums.absent_total ?? '?'}${absentText(nums)}`));
  secR.appendChild(el('p', 'note', `會死嗎：${wipe.companies ?? '?'} 檔 × 4 盞——紅 ${lamps.red ?? '?'}｜黃 ${lamps.amber ?? '?'}｜綠 ${lamps.green ?? '?'}｜灰（沒量到）${lamps.unlit ?? '?'}${unlit ? `（${unlit}）` : ''}——灰不是綠；四盞都非灰 ${wipe.all_four_non_grey ?? '?'} 檔`));
  if ((wipe.red_tickers || []).length) {
    secR.appendChild(el('p', 'note', `有紅燈的檔：${wipe.red_tickers.join('、')}`));
  }
  const notRead = roll.not_read || {};
  if (notRead.n) {
    secR.appendChild(el('p', 'warn', `▲ 讀不到三題與燈 ${notRead.n} 檔：` + (notRead.tickers || []).map((t) => `${t}（${(notRead.reasons || {})[t] || '—'}）`).join('、')));
  }
  const edge = roll.edge || {};
  secR.appendChild(el('p', 'note', `邊緣判定：邊緣 ${edge.edge ?? 0}｜非邊緣 ${edge.not_edge ?? 0}｜無法量 ${edge.unmeasurable ?? 0}`));
  app.appendChild(secR);

  app.appendChild(stateFooter(payload));
}

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
    if (heading) {
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

async function renderLayerNotes() {
  markNav('layer-notes');
  const payload = await loadLayerNotes();
  if (!payload) return;
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';
  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.title));
  app.appendChild(head);

  const c = payload.counts || {};
  const states = c.claim_states || {};
  const graphAbsence = (payload.graph || {}).absence;
  const sec0 = el('section', 'panel');
  sec0.appendChild(kpiRow([
    { label: '現行', value: String(c.notes || 0), sub: '一層一份、同層每頁共用' },
    { label: '主張', value: String(c.claims || 0), sub: `沒有 watch 在盯 ${states.unwatched || 0}｜被判觸及 ${states.touched || 0}` },
    { label: '連過來的個股頁', value: graphAbsence ? '未算' : String(c.pages_linked || 0), sub: graphAbsence ? graphAbsence.reason : '由圖推' },
    { label: '該重讀', value: String(c.needs_reread || 0), sub: '整份到期、主張觸及或到期、沒人盯', cls: 'hero' },
  ]));
  sec0.appendChild(el('p', 'note', `出處 ${c.citations_with_ref || 0} 個裡，文件有自宣告的 ${c.citations_declared || 0} 個——`
    + '其餘印「文件沒宣告」或為什麼問不到；推一步、沒有出處的不算在內。'));
  app.appendChild(sec0);

  const sec1 = el('section', 'panel');
  sec1.appendChild(el('h2', null, '每一份層說明（依節點 id 的字母序，不是名次）'));
  const list = el('ul', 'weak');
  (payload.rows || []).forEach((row) => {
    const li = el('li');
    const link = el('a', null, row.title);
    link.href = '#/layer/' + encodeURIComponent(row.node);
    const top = el('div');
    top.appendChild(link);
    li.appendChild(top);
    const cited = row.cited_by || {};
    li.appendChild(el('span', 'rule', `${row.node}｜${((payload.labels || {}).units || {})[row.unit] || row.unit}`
      + `｜重讀日 ${row.expires || '—'}｜主張 ${(row.claims || []).length} 條｜`
      + (cited.absence ? '連過來的頁：未連（見下一行）' : `連過來的頁 ${(cited.pages || []).length}：`
        + ((cited.pages || []).map((p) => p.ticker).join('、') || '—'))));
    if (cited.absence) li.appendChild(el('span', 'rule', `沒有頁連過來：${cited.absence.reason}`));
    (row.reread || []).forEach((r) => li.appendChild(el('span', 'rule', '該重讀：' + r)));
    list.appendChild(li);
  });
  if (!(payload.rows || []).length) list.appendChild(el('li', null, '一份層說明都還沒寫（`python -m alpha layer-note <node> --add`）'));
  sec1.appendChild(list);
  if ((payload.withdrawn || []).length) sec1.appendChild(el('p', 'note', '有紀錄但現行已撤回：' + payload.withdrawn.join('、')));
  (payload.parse_errors || []).forEach((e) => sec1.appendChild(el('p', 'warn', '▲ ledger 讀不懂：' + e)));
  (payload.declaration_problems || []).forEach((e) => sec1.appendChild(el('p', 'warn', '▲ 文件自宣告讀不到：' + e)));
  app.appendChild(sec1);

  app.appendChild(stateFooter(payload));
  window.scrollTo(0, 0);
}

async function renderLayerNote(node) {
  markNav('layer-notes');
  const payload = await loadLayerNotes();
  if (!payload) return;
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';
  const back = el('a', 'back', '← 全部層說明');
  back.href = '#/layer-notes';
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
    sec.appendChild(diagramFigure(d));
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
    // `structure-table` 等含連字號的路徑是保留字：ticker 一律大寫（store 的 slug 規則），所以不會撞到真實代碼。
    // ⚠ 2026-09-23（Step 0b.3）：`#/ranking`（瓶頸排序）→ `#/structure-table`；`#/basket`／`#/multi-year` 路由同批移除。
    if (target === 'structure-table') await renderStructureTable();
    else if (target === 'beta') await renderBeta();
    // ⚠ 2026-09-26（Step 2.6）：`#/coverage`（研究缺口）→ `#/graph-walk`（走圖九型）。
    else if (target === 'graph-walk') await renderGraphWalk();
    else if (target === 'structure-readings') await renderStructureReadings();
    else if (target === 'watches') await renderWatches();
    else if (target === 'positions') await renderPositions();
    else if (target === 'candidates') await renderCandidates();
    // 2026-10-02（Phase 5 Step 5.5）：帳號計分表頁——心跳段 5 一直寫「完整表在 APP」，這一頁之前其實不存在。
    else if (target === 'account-scorecard') await renderScorecard();
    // 2026-10-07（個股頁 plan S4b）：層說明。`layer/` 帶斜線與小寫，不會撞到 ticker（ticker 一律大寫、不含斜線）。
    else if (target === 'daily') await renderDaily();
    else if (target === 'layer-notes') await renderLayerNotes();
    else if (target.startsWith('layer/')) await renderLayerNote(target.slice('layer/'.length));
    else if (target) await renderDetail(target);
    else await renderList();
    if (/[?&]selfcheck=1\b/.test(window.location.search)) setTimeout(selfCheck, 0);
  } catch (err) {
    app.textContent = '';
    const box = el('div', 'error');
    box.appendChild(el('h2', null, '無法載入'));
    box.appendChild(el('p', null, 'APP 讀不到已 materialize 的判讀。'));
    const p = el('p', 'note');
    p.appendChild(document.createTextNode('請在本機跑：'));
    p.appendChild(el('code', null, 'python -m webapp materialize <TICKER>'));
    box.appendChild(p);
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
