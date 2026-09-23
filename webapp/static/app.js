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
      `${PANEL_TITLE[attention.panel] || attention.panel}：${attention.status}`));
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

  if (panel.disproofs && panel.disproofs.length) {
    node.appendChild(el('div', 'group-title', '什麼會推翻它（disproof）'));
    const list = el('ul', 'weak');
    panel.disproofs.forEach((item) => {
      const li = el('li', null, item.condition || item.label || JSON.stringify(item));
      const bits = [];
      if (item.check_frequency) bits.push('核查頻率 ' + item.check_frequency);
      if (item.action_on_trigger) bits.push('觸發後 ' + item.action_on_trigger);
      if (item.status) bits.push('狀態 ' + item.status);
      if (bits.length) li.appendChild(el('span', 'rule', bits.join('｜')));
      list.appendChild(li);
    });
    node.appendChild(list);
  }
  if (panel.catalysts && panel.catalysts.length) {
    node.appendChild(group(`催化劑（${panel.catalysts.length}）`, () => listOf(
      panel.catalysts.map((c) => [c.label, c.due, c.state].filter(Boolean).join('｜')))));
  }
  if (panel.checkpoints && panel.checkpoints.length) {
    node.appendChild(group(`檢核點（${panel.checkpoints.length}）`, () => listOf(
      panel.checkpoints.map((c) => [c.label, c.due, c.state].filter(Boolean).join('｜')))));
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
      `卡在「${PANEL_TITLE[item.panel] || item.panel}」這一層（${item.status}）　`));
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
      `旗標：${PANEL_TITLE[item.panel] || item.panel}（${item.status}）`);
    box.appendChild(head2);
    if (item.reason) box.appendChild(el('div', 'attention-body', item.reason));
    node.appendChild(box);
  });
  if (readiness.optional_unavailable && readiness.optional_unavailable.length) {
    node.appendChild(el('p', 'note',
      'optional 能力未提供：' + readiness.optional_unavailable.join('、') +
      '（**不影響** readiness——沒有 entry 判準不代表這檔研究不完整）'));
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
  // 隨估值鏈退役（C／H 組）；賭注／下檔的四價區塊已隨 E 組退役。反證那一端在 research 面板的 disproofs。
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
      `${colour ? colour.mark + ' ' + colour.word : '⬜ 灰'}　${plainLine(line.key) || line.display_label}`));
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
  const node = panelShell(panel, '賭注的每一格（optional，不影響這份判讀完不完整）');
  node.appendChild(el('p', 'note', (panel.context || {}).optional_rule || ''));
  node.appendChild(renderRows(panel.lines));
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
  if (series.length) node.appendChild(drill('表格版：每一個交易日的收盤', () => seriesTable(series)));
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

function disproofCard(view) {
  const panel = view.research;
  const disproofs = panel.disproofs || [];
  const catalysts = panel.catalysts || [];
  if (!disproofs.length && !catalysts.length) return null;
  const meta = plainPanel('research', panel.title);
  const node = el('section', 'panel');
  node.appendChild(el('h2', null, meta.title));
  node.appendChild(el('div', 'panel-questions', meta.hint));
  if (disproofs.length) {
    const list = el('ul', 'weak');
    disproofs.forEach((item) => {
      const li = el('li', null, item.condition || item.label || '');
      const bits = [];
      if (item.check_frequency) bits.push('多久看一次：' + item.check_frequency);
      if (item.action_on_trigger) bits.push('觸發後要做什麼：' + item.action_on_trigger);
      if (item.status) bits.push('狀態 ' + item.status);
      if (bits.length) li.appendChild(el('span', 'rule', bits.join('｜')));
      list.appendChild(li);
    });
    node.appendChild(list);
  }
  if (catalysts.length) {
    node.appendChild(el('div', 'group-title', '什麼時候會知道'));
    node.appendChild(listOf(catalysts.map((c) => [c.label, c.due, c.state].filter(Boolean).join('｜'))));
  }
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
  if (panel && panel.context && panel.context.available) {
    const story = el('div', 'story');
    (panel.lines || []).filter((line) => line.key.indexOf('brief:') === 0).forEach((line) => {
      const row = el('div', 'story-row');
      row.appendChild(el('div', 'story-label', plainLine(line.key, line.display_label)));
      const text = el('div', 'story-text', String(line.datum.value || ''));
      if (line.datum.status === 'partial' && line.datum.reason) text.title = line.datum.reason;
      row.appendChild(text);
      story.appendChild(row);
    });
    node.appendChild(story);
  } else {
    const box = el('div', 'attention flags');
    box.appendChild(el('div', 'attention-head', '還沒寫短評'));
    box.appendChild(el('div', 'attention-body', (panel && panel.reason) || meta.hint));
    node.appendChild(box);
  }
  // ⚠ **2026-09-23（Phase 0 Step 0b.1）：首屏那把尺與「要翻倍需要什麼為真」計算框整塊退役。**
  // ROADMAP「個股頁」對照表把它們列進「拿掉」：尺上是現價／沒賭對／賭對／判斷錯了，
  // 計算框問的是「這個結構允不允許翻倍」——兩者都建在估值鏈與多年反向橋上。
  // 接手的是末行候選狀態與財務三題三個字（Phase 3）；在那之前首屏只有句子、燈與走勢圖。
  // 走勢圖留下來：它是**脈絡**不是訊號（AGENTS「量測、訊號、脈絡三分」）。
  node.appendChild(priceCard(payload));
  return node;
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
  const audit = el('section', 'panel');
  audit.appendChild(drill('稽核：每一格的來源、狀態、算式與警告（給查核用，不是給你讀的）', () => {
    const box = el('div', 'why-box');
    box.appendChild(conclusionCard(payload, view));
    // ⚠ 2026-09-23（Phase 0 Step 0b.1）：`fragileCard`（最脆弱的假設）隨 `why` panel 退役
    // ——它列的是估值假設的敏感度，那個模型不在了。風險與認錯條件在 disproofCard。
    [blockerCard(payload), disproofCard(view), versusMarketCard(view)]
      .forEach((card) => { if (card) box.appendChild(card); });
    return box;
  }));
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

/* ---------- 籃子（V3；ranking × 各檔 overview × positions 的 join；順序照抄、首選是 filter） ---------- */

function pctCell(value) { return returnCell(value); }

const BASKET_COLUMNS = [
  { title: '#', cell: (row) => el('td', 'rank-num', row.rank) },
  { title: '標的', cell: (row, set) => companyCell({ ticker: row.ticker, company_id: row.company_id, company_label: row.company_label }, set) },
  { title: '同一個賭注的群', cell: (row) => el('td', 'nowrap dim', row.sector || '—') },
  { title: '賭什麼', cell: (row) => {
      // Q2（2026-09-17）：三種狀態必須在畫面上分得出來——「刻意不主張」是研究結論（settled），
      // 「欠一個答案」是待辦。壓成同一句「還沒寫賭注」等於把結論與待辦混成一格（L12）。
      const c = el('td', 'wrap');
      if (row.our_bet) c.textContent = row.our_bet;
      else if (row.bet_state === 'bet') c.textContent = '（有賭注，還沒寫短評）';
      else if (row.bet_state === 'abstained') {
        c.appendChild(el('span', 'badge badge-settled', '刻意不主張'));
        if (row.bet_absence_reason) c.appendChild(el('div', 'note', row.bet_absence_reason));
      } else {
        c.appendChild(el('span', 'badge badge-blocked', '欠一個答案'));
      }
      return c;
    } },
  { title: '賭對，漲跌', cell: (row) => pctCell(row.payoff) },
  { title: '沒賭對，漲跌', cell: (row) => pctCell(row.base_return) },
  { title: '裁決點', cell: (row) => {
      const r = row.ripeness;
      return el('td', 'nowrap', r && r.linked ? `已裁決 ${r.resolved}／${r.linked}` : '—');
    } },
  { title: '市場承認了嗎', cell: (row) => {
      const c = el('td', 'nowrap');
      if (typeof row.consensus_moved === 'number') c.textContent = `共識朝我們 ${fmtPercent(row.consensus_moved)}（${row.consensus_points} 次）`;
      else c.textContent = '—';
      return c;
    } },
  { title: '部位', cell: (row) => {
      const c = el('td', 'nowrap');
      if (row.position) c.textContent = `持有 ${fmtNumber(row.position.shares, 2)} 股（${fmtPercent(row.position.live_return)}）`;
      else c.appendChild(el('span', 'dim', '未持有'));
      return c;
    } },
  { title: 'filter', cell: (row) => {
      const c = el('td', 'nowrap');
      if (row.passes_filter) c.appendChild(el('span', 'badge badge-ready', '通過'));
      else c.textContent = (row.filter_reasons || []).map((k) => ((BASKET_VOCAB && BASKET_VOCAB[k]) || k)).join('；');
      return c;
    } },
];
let BASKET_VOCAB = null;

/* 量的候選（Q1，2026-09-17）：被門檻擋下、但已研究過的那些。**另一個問題、另一組條件、沒有排序。** */
const VOLUME_COLUMNS = [
  { title: '標的', cell: (row, set) => companyCell({ ticker: row.ticker, company_id: row.company_id, company_label: row.company_label }, set) },
  { title: '卡在哪', cell: (row) => el('td', 'nowrap dim', row.bottleneck || '—') },
  { title: '替代難度', cell: (row) => el('td', 'nowrap', `${row.substitutability ?? '—'}（門檻 ${row.threshold ?? '—'}）`) },
  { title: '出貨了嗎', cell: (row) => {
      const c = el('td', 'nowrap');
      const shipping = row.qualification_status === 'qualified' || row.qualification_status === 'designed_in';
      if (shipping) c.appendChild(el('span', 'badge badge-ready', row.qualification_status));
      else c.appendChild(el('span', 'dim', row.qualification_status || '未填'));
      return c;
    } },
  { title: '需求錨', cell: (row) => el('td', 'nowrap dim', row.demand_anchor || '（走不到）') },
  { title: '賭什麼', cell: (row) => {
      const c = el('td', 'wrap');
      if (row.our_bet) c.textContent = row.our_bet;
      else if (row.bet_state === 'bet') c.textContent = '（有賭注，還沒寫短評）';
      else if (row.bet_state === 'abstained') c.appendChild(el('span', 'badge badge-settled', '刻意不主張'));
      else c.appendChild(el('span', 'badge badge-blocked', '欠一個答案'));
      return c;
    } },
  { title: 'filter', cell: (row) => {
      const c = el('td', 'nowrap');
      if (row.passes_filter) c.appendChild(el('span', 'badge badge-ready', '通過'));
      else c.textContent = (row.filter_reasons || []).map((k) => ((VOLUME_VOCAB && VOLUME_VOCAB[k]) || k)).join('；');
      return c;
    } },
];
let VOLUME_VOCAB = null;


// Phase 7 Step 7.4（2026-09-19）：「要幾倍，哪一格得為真」。
// ⚠ 這一頁**只讀已 materialize 的 artifact**，一個數都不算——多年橋是金融模型，
// 而 APP 呈現契約禁止 request path 跑模型。要更新就跑 `python -m webapp materialize --multi-year`。
async function renderMultiYear() {
  markNav('multi-year');
  let payload;
  try {
    payload = await getJSON(`${API}/multi-year`);
  } catch (err) {
    renderStateError(err, '讀不到多年視角');
    return;
  }
  app.textContent = '';
  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.title));
  app.appendChild(head);

  const intro = el('section', 'panel callout');
  intro.appendChild(el('p', 'arg-text', payload.this_is_not || ''));
  const counts = payload.counts || {};
  // ⚠ 四種缺席各自現形，不併成一個「還沒寫」（INV-3）：「我們還沒寫目標年度」是待辦，
  // 「方法不適用」是已經算過而且知道答案沒有意義，兩者要做的事完全不同。
  const absences = [
    counts.no_horizon ? `還沒寫下目標年度 ${counts.no_horizon}` : '',
    counts.method_not_applicable ? `方法不適用 ${counts.method_not_applicable}` : '',
    counts.no_judgment ? `沒有判斷檔 ${counts.no_judgment}` : '',
    counts.other_missing ? `其他缺料 ${counts.other_missing}` : '',
  ].filter(Boolean);
  intro.appendChild(el('p', 'note',
    `${counts.input || 0} 檔｜算得出 ${counts.available || 0}`
    + (absences.length ? `｜${absences.join('｜')}` : '')));
  app.appendChild(intro);

  (payload.rows || []).forEach((row) => {
    const card = el('section', 'panel');
    card.appendChild(el('h2', null, row.ticker));
    if (row.status !== 'available') {
      // ⚠ 「還沒有人寫下來」與「這一檔沒有多年主張」是兩件事——理由逐字印出來，不壓成一句。
      card.appendChild(el('p', 'note', row.reason || '算不出來'));
      app.appendChild(card);
      return;
    }
    card.appendChild(el('p', 'note',
      `目標年度 ${row.horizon}｜基期 ${row.base_period}｜距離 ${row.span_years} 年`
      + `｜現價 ${row.current_price}｜目標倍數 ${row.target_multiple}x`));
    if (row.multiple_source) card.appendChild(el('p', 'note', row.multiple_source));
    (row.bridge_warnings || []).forEach((w) => card.appendChild(el('p', 'note', w)));
    const table = el('table', 'rank compare');
    const thead = el('thead');
    const hr = el('tr');
    ['倍率', '需要 EPS', '比錨點高', '解得出來的', '拉到極限也做不到'].forEach((label) => {
      hr.appendChild(el('th', null, label));
    });
    thead.appendChild(hr);
    table.appendChild(thead);
    const tbody = el('tbody');
    (row.ladder || []).forEach((step) => {
      const tr = el('tr');
      tr.appendChild(el('td', null, `${step.multiple}x`));
      tr.appendChild(el('td', null, step.required_eps == null ? '—' : step.required_eps.toFixed(2)));
      tr.appendChild(el('td', null, signedPct(step.required_gap, 0)));
      const solved = (step.solutions || []).filter((s) => s.status === 'solved')
        .map((s) => `${s.driver}[${s.scope}] = ${s.implied_value == null ? '—' : s.implied_value.toPrecision(4)}`);
      tr.appendChild(el('td', null, solved.length ? solved.join('；') : '—'));
      tr.appendChild(el('td', null, (step.unreachable || []).join('、') || '—'));
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    card.appendChild(table);
    app.appendChild(card);
  });
}

async function renderBasket() {
  markNav('basket');
  let payload;
  try {
    payload = await getJSON(`${API}/basket`);
  } catch (err) {
    renderStateError(err, '讀不到籃子');
    return;
  }
  BASKET_VOCAB = (payload.filter || {}).reason_labels || {};
  const detailSet = new Set(payload.analyst_view_tickers || []);
  app.textContent = '';
  footerWarning.textContent = payload.correlation_warning || '';
  const head = el('div', 'detail-head');
  head.appendChild(el('h1', null, payload.title));
  app.appendChild(head);

  // 首選（filter 的結果）或它為什麼缺席——兩者不同形。
  const pick = el('section', 'panel callout');
  if (payload.top_pick) {
    const p = payload.top_pick;
    pick.appendChild(el('h2', null, `首選：${p.ticker}（結構第 ${p.rank}）`));
    if (p.our_bet) pick.appendChild(el('p', 'arg-text', p.our_bet));
    pick.appendChild(el('p', 'note', `賭對漲跌 ${fmtPercent(p.payoff)}｜群：${p.sector || '—'}｜${p.note}`));
  } else {
    pick.appendChild(el('h2', null, '目前沒有首選'));
    pick.appendChild(el('p', 'arg-text', payload.top_pick_absent_reason || ''));
  }
  const f = payload.filter || {};
  pick.appendChild(el('p', 'note', `filter：${f.input} 檔進來、${f.accepted} 檔通過、${f.filtered} 檔被擋。${f.rule || ''}`));
  // 賭注帳（Q2）：每一列強制二選一，欠帳會自己出現在首屏——不是要人翻表才看得到（L14）。
  const bl = payload.bet_ledger;
  if (bl) {
    pick.appendChild(mdParagraph(
      `賭注帳：有賭注 ${bl.bet}｜刻意不主張 ${bl.abstained}｜**欠一個答案 ${bl.unanswered}**`
      + (bl.owed && bl.owed.length ? `（${bl.owed.join('、')}）` : ''), 'note'));
    pick.appendChild(mdParagraph(bl.rule || '', 'note'));
  }
  app.appendChild(pick);

  const sec = el('section', 'panel');
  sec.appendChild(el('h2', null, `全部（${(payload.rows || []).length} 檔，順序＝瓶頸排序）`));
  sec.appendChild(rankTable(payload.rows || [], BASKET_COLUMNS, detailSet));
  (payload.correlation_notes || []).forEach((t) => sec.appendChild(el('p', 'warn', '▲ ' + t)));
  app.appendChild(sec);

  // 第二個宇宙（Q1）：**分開呈現、分開判定**——另一個問題，不與上面那份比較、不合併計數。
  const vf = payload.volume_filter;
  if (vf) {
    VOLUME_VOCAB = vf.reason_labels || {};
    const vol = el('section', 'panel');
    vol.appendChild(el('h2', null, `量的候選（${(payload.volume_rows || []).length} 家；已研究、低於門檻）`));
    vol.appendChild(mdParagraph(vf.universe_note || '', 'note'));
    vol.appendChild(mdParagraph(vf.order_note || '', 'note'));
    vol.appendChild(el('p', 'note', `filter：${vf.input} 家進來、${vf.accepted} 家通過、${vf.filtered} 家被擋。`));
    const vbl = payload.volume_bet_ledger;
    if (vbl) {
      vol.appendChild(mdParagraph(
        `賭注帳：有賭注 ${vbl.bet}｜刻意不主張 ${vbl.abstained}｜**欠一個答案 ${vbl.unanswered}**`
        + (vbl.owed && vbl.owed.length ? `（${vbl.owed.join('、')}）` : ''), 'note'));
    }
    vol.appendChild(rankTable(payload.volume_rows || [], VOLUME_COLUMNS, detailSet));
    (vf.missing_criteria || []).forEach((t) => vol.appendChild(el('p', 'warn', '▲ 今天還沒有資料源：' + t)));
    app.appendChild(vol);
  }
  app.appendChild(stateFooter(payload, '這份籃子不是什麼'));
}

/* ---------- 瓶頸排序（跨標的 state；照抄 rank_bottlenecks 的輸出，不重排、不加權） ---------- */

let RANK_VOCAB = null;

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
  const table = (RANK_VOCAB && RANK_VOCAB.sole_source_states) || {};
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
  cell.appendChild(el('div', 'company', row.company_label || row.company_id));
  return cell;
}

/* 關係動詞寫成人話，原始 label 附在 title 供查圖（判準：望文生義還是要查表）。 */
const RELATION_PLAIN = { supplies_to: '供貨給', depends_on: '依賴', constrained_by: '受限於' };

function edgeCell(row) {
  const cell = el('td', 'rank-edge');
  const verb = el('div', 'dim', RELATION_PLAIN[row.relation] || row.relation);
  verb.title = row.relation;
  cell.appendChild(verb);
  const node = el('code', null, row.bottleneck);
  node.title = '圖裡的節點 ID，可貼回來查';
  cell.appendChild(node);
  return cell;
}

function subCell(row) {
  const cell = el('td', 'rank-sub');
  const hasSub = row.substitutability !== null && row.substitutability !== undefined;
  cell.appendChild(el('span', 'sub-score', hasSub ? `${row.substitutability}/5` : '未填'));
  cell.appendChild(document.createTextNode(' '));
  cell.appendChild(soleSourceBadge(row.sole_source));
  return cell;
}

function anchorCell(row) {
  const cell = el('td', 'rank-anchor');
  if (row.demand_anchor) {
    cell.appendChild(el('code', null, row.demand_anchor));
    cell.appendChild(el('div', 'dim', `離它 ${row.demand_hops} 步`));
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
  wrap.appendChild(table);
  return wrap;
}

const ACTIONABLE_COLUMNS = [
  { title: '#', cell: (row) => el('td', 'rank-num', row.rank) },
  { title: '標的', cell: companyCell },
  { title: '卡在哪一層', cell: edgeCell },
  { title: '有多難換掉', cell: subCell },
  { title: '證據強度', cell: (row) => { const c = el('td', 'nowrap', row.evidence_label || row.evidence); c.title = row.evidence; return c; } },
  { title: '合格狀態', cell: (row) => el('td', 'nowrap', row.qualification_status || '—') },
  { title: '誰在花錢', cell: anchorCell },
];

const STRUCTURAL_COLUMNS = [
  { title: '#', cell: (row) => el('td', 'rank-num', row.rank) },
  { title: '標的', cell: companyCell },
  { title: '卡在哪一層', cell: edgeCell },
  { title: '有多難換掉', cell: subCell },
  { title: '離花錢的人幾步', cell: (row) => el('td', 'nowrap', hopsText(row)) },
  { title: '目前證據強度', cell: (row) => { const c = el('td', 'nowrap', row.evidence_label || row.evidence); c.title = row.evidence; return c; } },
  { title: '落差', cell: (row) => {
      const cell = el('td', 'dim nowrap');
      if (row.gap_note) cell.textContent = row.gap_note;
      else if (row.actionable_rank) cell.textContent = `可行動排序第 ${row.actionable_rank}`;
      else cell.textContent = '—';
      return cell;
    } },
];

function renderRankingError(err) {
  app.textContent = '';
  const box = el('div', 'error');
  const detail = (err.body && err.body.error) || {};
  box.appendChild(el('h2', null, '讀不到瓶頸排序'));
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

async function renderRanking() {
  markNav('ranking');
  let payload;
  try {
    payload = await getJSON(`${API}/ranking`);
  } catch (err) {
    renderRankingError(err);
    return;
  }
  RANK_VOCAB = payload.vocab || {};
  const detailSet = new Set(payload.analyst_view_tickers || []);
  const notes = payload.notes || {};
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

  // ① 首選：authority 的第 1 名，不是本畫面的判斷。
  const pick = el('section', 'panel callout');
  pick.appendChild(el('h2', null, '現在要投哪一檔'));
  if (payload.top_pick) {
    const p = payload.top_pick;
    const line = el('div', 'pick-line');
    line.appendChild(el('span', 'pick-rank', '#1'));
    if (p.ticker && detailSet.has(p.ticker)) {
      const link = el('a', 'ticker-link', p.ticker);
      link.href = '#/' + encodeURIComponent(p.ticker);
      line.appendChild(link);
    } else {
      line.appendChild(el('span', 'ticker-plain', p.ticker || '—'));
    }
    line.appendChild(el('span', 'company', p.company_label || p.company_id));
    line.appendChild(el('span', 'dim', `${p.relation} →`));
    line.appendChild(el('code', null, p.bottleneck));
    pick.appendChild(line);
    pick.appendChild(el('p', 'note', p.note));
  } else {
    pick.appendChild(el('p', 'note', payload.top_pick_absent_reason || '無候選'));
  }
  app.appendChild(pick);

  // ② 已知限制：契約說「解讀前必讀」，所以不摺疊。
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
  app.appendChild(limits);

  // ③ 可行動排序
  const sortKeys = (RANK_VOCAB.sort_keys) || {};
  const sec1 = el('section', 'panel');
  sec1.appendChild(el('h2', null, `可行動排序（${payload.rows.length} 條）——現在能投什麼`));
  sec1.appendChild(el('div', 'panel-questions', '排序鍵優先序（不是加權）：' + (sortKeys.rows || []).join(' › ')));
  if (payload.rows.length) sec1.appendChild(rankTable(payload.rows, ACTIONABLE_COLUMNS, detailSet));
  else sec1.appendChild(el('p', 'empty', '（無符合門檻的瓶頸邊）'));
  app.appendChild(sec1);

  // ④ 純結構排序
  const sec2 = el('section', 'panel');
  sec2.appendChild(el('h2', null, '純結構排序（只看多卡，不看證據）——該去補誰的證據'));
  sec2.appendChild(el('div', 'panel-questions', '排序鍵優先序（不是加權）：' + (sortKeys.structural_rows || []).join(' › ')));
  (notes.two_rankings || []).forEach((text) => sec2.appendChild(mdParagraph(text)));
  const structural = payload.structural_rows || [];
  const shown = structural.slice(0, 10);
  if (shown.length) sec2.appendChild(rankTable(shown, STRUCTURAL_COLUMNS, detailSet));
  else sec2.appendChild(el('p', 'empty', '（無）'));
  if (structural.length > shown.length) {
    const rest = structural.slice(shown.length);
    sec2.appendChild(drill(`展開：其餘 ${rest.length} 條`, () => rankTable(rest, STRUCTURAL_COLUMNS, detailSet)));
  }
  if (notes.structural_table) sec2.appendChild(mdParagraph(notes.structural_table));
  app.appendChild(sec2);

  // ⑤ 產業別分組：解決可視性，不解決可比性。
  const sec3 = el('section', 'panel');
  sec3.appendChild(el('h2', null, '產業別分組（解決可視性，分數不可跨組比較）'));
  (payload.correlation_notes || []).forEach((text) => sec3.appendChild(el('p', 'warn', '⚠ ' + text)));
  if (payload.empty_sectors && payload.empty_sectors.length) {
    sec3.appendChild(el('p', 'warn', '🔴 空產業組（sub 覆蓋未及，研究缺口）：' + payload.empty_sectors.join('、')));
  }
  if (notes.no_anchor_reading) sec3.appendChild(mdParagraph(notes.no_anchor_reading));
  const byRank = {};
  payload.rows.forEach((row) => { byRank[row.rank] = row; });
  (payload.sectors || []).forEach((sector) => {
    const box = el('div', 'sector');
    box.appendChild(el('div', 'group-title', `${sector.sector}（可行動 ${sector.actionable_count} 條）`));
    const ul = el('ul', 'notes');
    sector.actionable_ranks.slice(0, 3).forEach((rank) => {
      const row = byRank[rank];
      if (!row) return;
      const hasSub = row.substitutability !== null && row.substitutability !== undefined;
      ul.appendChild(el('li', null,
        `#${row.rank} ${row.ticker || '—'}（${row.company_label || row.company_id}） ${row.relation} → ${row.bottleneck}` +
        `｜sub ${hasSub ? row.substitutability : '未填'}${row.sole_source === true ? '｜sole_source' : ''}` +
        `｜${row.evidence_label || row.evidence}`));
    });
    if (sector.structural_first) {
      const f = sector.structural_first;
      ul.appendChild(el('li', 'dim', `↳ 純結構第一（該去補證據的）：${f.ticker || f.company_id} → ${f.bottleneck}`));
    }
    box.appendChild(ul);
    sec3.appendChild(box);
  });
  app.appendChild(sec3);

  // ⑥ 需求鏈
  const sec4 = el('section', 'panel');
  sec4.appendChild(el('h2', null, '需求鏈（誰在花錢 → 這家公司）'));
  sec4.appendChild(drill(`展開：每一列的鏈路（${payload.rows.length}）`, () => {
    const ul = el('ul', 'notes');
    payload.rows.forEach((row) => {
      const li = el('li', null, `#${row.rank} ${row.company_id} ${row.relation} ${row.bottleneck}`);
      const sub = el('div', 'dim');
      if (row.chain && row.chain.length) sub.textContent = row.chain.join(' → ') + `　（距需求端 ${row.demand_hops} 跳）`;
      else sub.appendChild(mdInline(notes.no_anchor_chain || ''));
      li.appendChild(sub);
      ul.appendChild(li);
    });
    return ul;
  }));
  app.appendChild(sec4);

  // ⑦ 新鮮度與 authority
  const f = payload.freshness || {};
  const sec5 = el('section', 'panel');
  sec5.appendChild(el('h2', null, '這份排序有多新'));
  const rows = el('div', 'rows');
  rows.appendChild(kv('materialize 於', `${f.generated_at}（${Number(f.age_hours).toFixed(1)} 小時前，${f.state}）`));
  rows.appendChild(kv('排序權威', `${payload.authority.function}（${payload.authority.command}）`));
  rows.appendChild(kv('視角', pit.mode === 'as_of' ? `as-of ${payload.as_of}` : '現況'));
  if (pit.excluded) rows.appendChild(kv('as-of 視角排除的 assertion', JSON.stringify(pit.excluded)));
  rows.appendChild(kv('新鮮度身分', payload.freshness_identity));
  rows.appendChild(kv('artifact content digest', payload.content_digest));
  sec5.appendChild(rows);
  sec5.appendChild(el('p', 'note', f.rule || ''));
  sec5.appendChild(el('p', 'note', payload.authority.note || ''));
  app.appendChild(sec5);

  // ⑧ 這份排序不是什麼
  const sec6 = el('section', 'panel');
  sec6.appendChild(el('h2', null, '這份排序不是什麼'));
  sec6.appendChild(listOf(payload.this_is_not || []));
  app.appendChild(sec6);
  window.scrollTo(0, 0);
}

/* ---------- 資產配置（beta state；照抄 Engine D beta monitor 的輸出，不重算、不排序） ----------
   圖表依 dataviz skill：形式先於顏色；色跟實體走（sleeve 的 slot 由 materialize 固定）；細的 mark、
   hairline 格線；每張圖都有表格版；tooltip 只加分不當唯一讀法。所有數字都是 artifact 的原值，
   這裡只做 ×100 的百分比排版與座標換算——沒有任何財務算術。 */

const SVG_NS = 'http://www.w3.org/2000/svg';

function svgEl(tag, attrs, text) {
  const node = document.createElementNS(SVG_NS, tag);
  Object.keys(attrs || {}).forEach((k) => node.setAttribute(k, String(attrs[k])));
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
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

function allocationTable(sleeves) {
  const box = el('div', 'table-view');
  const table = el('table');
  const head = el('thead');
  const hr = el('tr');
  ['Sleeve', '角色', '目標', '容忍區間', '實際', '差距', '狀態'].forEach((t) => hr.appendChild(el('th', null, t)));
  head.appendChild(hr);
  table.appendChild(head);
  const body = el('tbody');
  sleeves.forEach((s) => {
    const tr = el('tr');
    [s.label, s.role || '', fmtRatioPct(s.target, 1), '±' + fmtRatioPct(s.band, 1), fmtRatioPct(s.actual, 1) || '算不到',
      typeof s.gap === 'number' ? (s.gap > 0 ? '+' : '') + fmtRatioPct(s.gap, 1) : '—', s.state_label || ''].forEach((t) => tr.appendChild(el('td', null, t)));
    body.appendChild(tr);
  });
  table.appendChild(body);
  box.appendChild(table);
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

function seriesTable(series) {
  const box = el('div', 'table-view');
  const table = el('table');
  const head = el('thead'); const hr = el('tr');
  ['交易日', '收盤（自身序列）'].forEach((t) => hr.appendChild(el('th', null, t)));
  head.appendChild(hr); table.appendChild(head);
  const body = el('tbody');
  series.slice().reverse().forEach((r) => {
    const tr = el('tr');
    tr.appendChild(el('td', null, r.session_date));
    tr.appendChild(el('td', null, fmtNumber(r.close, decimalsFor(r.close))));
    body.appendChild(tr);
  });
  table.appendChild(body); box.appendChild(table);
  return box;
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
  if (inst.series && inst.series.length) card.appendChild(drill('表格版：每一個交易日的收盤', () => seriesTable(inst.series)));
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
    sec1.appendChild(drill('表格版', () => allocationTable(alloc.sleeves || [])));
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

  // ⑤ 新鮮度與 authority；這份畫面不是什麼。
  const f = payload.freshness || {};
  const sec5 = el('section', 'panel');
  sec5.appendChild(el('h2', null, '這份畫面有多新'));
  const rows = el('div', 'rows');
  rows.appendChild(kv('materialize 於', `${f.generated_at}（${Number(f.age_hours).toFixed(1)} 小時前，${f.state}）`));
  rows.appendChild(kv('權威', `${(payload.authority || {}).function}（${(payload.authority || {}).command}）`));
  rows.appendChild(kv('行情更新', `${(payload.refresh || {}).status || '—'}｜${(payload.refresh || {}).note || ''}`));
  rows.appendChild(kv('新鮮度身分', payload.freshness_identity));
  rows.appendChild(kv('artifact content digest', payload.content_digest));
  sec5.appendChild(rows);
  sec5.appendChild(el('p', 'note', f.rule || ''));
  app.appendChild(sec5);

  const sec6 = el('section', 'panel');
  sec6.appendChild(el('h2', null, '這份畫面不是什麼'));
  sec6.appendChild(listOf(payload.this_is_not || []));
  app.appendChild(sec6);
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

/* ---------- 覆蓋掃描（coverage state）與在等什麼（watches state） ----------
   兩頁都是「計數＋清單」——依 dataviz 的 form heuristic，>7 類且每類都有意義時用表格／清單，
   不是更多顏色；四個桶的數字用 KPI stat tile。這裡沒有圖表，也沒有排序。 */

function kpiRow(items) {
  const row = el('div', 'tiles');
  items.forEach((it) => row.appendChild(tile(it.label, it.value, it.sub, it.cls)));
  return row;
}

function nodeList(rows, opts) {
  const o = opts || {};
  const list = el('ul', 'weak');
  rows.forEach((row) => {
    const li = el('li');
    if (o.question && row.question) {
      li.appendChild(el('div', null, row.question));
      li.appendChild(el('span', 'rule', `${row.node}${row.name ? '　' + row.name : ''}`));
    } else {
      const head = el('div');
      head.appendChild(el('code', null, row.node));
      if (row.name) head.appendChild(el('span', 'dim', '　' + row.name));
      li.appendChild(head);
      const linked = (row.indirect || []).slice(0, 6);
      if (linked.length) li.appendChild(el('span', 'rule', '間接相連：' + linked.join('、')));
      const direct = (row.direct || []).slice(0, 6);
      if (direct.length) li.appendChild(el('span', 'rule', '直接供應：' + direct.join('、')));
    }
    list.appendChild(li);
  });
  return list;
}

/* 一對重複節點候選。**逐字是主角**：2026-09-18 之前圖裡只有 id 與 name，而兩者都是抽取時
   LLM 取的——用它們判重複等於用 label 驗 label。所以每一端都要印得出它自己的逐字（L18）。 */
function duplicateSide(side) {
  const box = el('div', 'pair-side');
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

function duplicateList(rows, ruleLabels) {
  const list = el('ul', 'weak');
  (rows || []).forEach((row) => {
    const li = el('li');
    const head = el('div');
    head.appendChild(el('code', null, row.pair[0]));
    head.appendChild(el('span', 'dim', ' ↔ '));
    head.appendChild(el('code', null, row.pair[1]));
    li.appendChild(head);
    li.appendChild(el('span', 'rule',
      (row.rules || []).map((r) => (ruleLabels || {})[r] || r).join('＋')
      + '｜' + (row.same_abstraction_level ? '同層' : '不同層')));
    li.appendChild(duplicateSide(row.left));
    li.appendChild(duplicateSide(row.right));
    (row.registry_mentions || []).forEach((m) => {
      li.appendChild(el('span', 'rule',
        `📄 ${m.canonical}（${m.basis}／${m.approval_receipt || '無 receipt'}）：${m.note}`));
    });
    list.appendChild(li);
  });
  return list;
}

async function renderCoverage() {
  markNav('coverage');
  let payload;
  try {
    payload = await getJSON(`${API}/coverage`);
  } catch (err) {
    renderStateError(err, '讀不到覆蓋掃描');
    return;
  }
  const c = payload.counts || {};
  const notes = payload.notes || {};
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
  sec0.appendChild(el('h2', null, `圖裡 ${c.nodes} 個瓶頸節點，哪些還沒有供應商`));
  sec0.appendChild(kpiRow([
    { label: '🔴 真的還沒挖', value: String(c.research_gap_real), sub: '有名有姓、零供應商的子瓶頸', cls: 'hero' },
    { label: '🟡 建模待補', value: String(c.modelling_gap), sub: '研究過了，邊沒接上' },
    { label: '✅ 已覆蓋', value: String(c.covered), sub: '有公司直接連上' },
    { label: '⚪ 概念節點', value: String(c.concept), sub: '不適用「誰供應它」' },
  ]));
  sec0.appendChild(mdParagraph(notes.buckets || ''));
  sec0.appendChild(mdParagraph(notes.scope || ''));
  app.appendChild(sec0);

  const sec1 = el('section', 'panel callout');
  sec1.appendChild(el('h2', null, `🔴 真正的空白（${c.research_gap_real}）——可以直接拿去研究的題目`));
  sec1.appendChild(mdParagraph(notes.research_gap_split || ''));
  sec1.appendChild(nodeList(payload.research_gaps || [], { question: true }));
  sec1.appendChild(el('p', 'note', notes.question_template || ''));
  if ((payload.product_noise || []).length) {
    sec1.appendChild(drill(`展開：另有 ${payload.product_noise.length} 個是抽取產生的產品名詞（只計數，不是題目）`,
      () => nodeList(payload.product_noise)));
  }
  app.appendChild(sec1);

  const sec2 = el('section', 'panel');
  sec2.appendChild(el('h2', null, `🟡 建模待補（${c.modelling_gap}）——補邊，不是重新研究`));
  sec2.appendChild(el('div', 'panel-questions', (payload.next_steps || {}).modelling_gap || ''));
  sec2.appendChild(nodeList(payload.modelling_gaps || []));
  app.appendChild(sec2);

  const dup = payload.duplicates || {};
  const secDup = el('section', 'panel');
  secDup.appendChild(el('h2', null,
    `${dup.title || '重複節點候選'}（${c.duplicate_unmentioned}）——先問「它是不是旁邊那個」`));
  secDup.appendChild(kpiRow([
    { label: '沒人提過', value: String(c.duplicate_unmentioned), sub: '這些要人看', cls: 'hero' },
    { label: 'registry 提過', value: String(c.duplicate_mentioned), sub: '先讀 note 說了什麼' },
    { label: '掃描節點', value: String(dup.node_total || 0), sub: '非公司實體（公司走 registry）' },
  ]));
  secDup.appendChild(duplicateList(dup.unmentioned, dup.rule_labels));
  if ((dup.mentioned || []).length) {
    secDup.appendChild(drill(`展開：registry 的 note 提過的 ${dup.mentioned.length} 對`,
      () => duplicateList(dup.mentioned, dup.rule_labels)));
  }
  const dupNotes = el('ul', 'notes');
  (dup.this_is_not || []).forEach((t) => dupNotes.appendChild(el('li', null, t.replace(/[`*]/g, ''))));
  secDup.appendChild(dupNotes);
  app.appendChild(secDup);

  const sec3 = el('section', 'panel');
  sec3.appendChild(el('h2', null, '其餘'));
  sec3.appendChild(drill(`展開：✅ 已覆蓋（${c.covered}）`, () => nodeList(payload.covered || [])));
  sec3.appendChild(drill(`展開：⚪ 概念／政策節點（${c.concept}）`, () => nodeList(payload.concept || [])));
  app.appendChild(sec3);

  app.appendChild(stateFooter(payload, '這份掃描不是什麼'));
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
  li.appendChild(el('span', 'rule', `${row.watch_id}｜${row.kind}`));
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
  sec0.appendChild(el('p', 'note', `喚醒去處：pq2 ${k.wake_pq2}｜lead ${k.wake_lead}｜假設 ${k.wake_hypothesis}`));
  sec0.appendChild(el('p', 'note', notes.budget || ''));
  app.appendChild(sec0);

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
      li.appendChild(el('span', 'rule', row.lead_id));
      list.appendChild(li);
    });
    sec2.appendChild(list);
    app.appendChild(sec2);
  }

  const sec3 = el('section', 'panel');
  sec3.appendChild(el('h2', null, `全部在等的事件（${(payload.active || []).length}）`));
  if ((payload.due_this_round || []).length) {
    sec3.appendChild(el('div', 'group-title', `本輪該主動查的（${payload.due_this_round.length}，依 budget）`));
    sec3.appendChild(watchList(payload.due_this_round, labels));
  }
  sec3.appendChild(drill(`展開：全部 ${(payload.active || []).length} 筆`, () => watchList(payload.active || [], labels)));
  if ((payload.fired_unconsumed || []).length) {
    sec3.appendChild(drill(`展開：fired 未消化（${payload.fired_unconsumed.length}）`,
      () => watchList(payload.fired_unconsumed, labels)));
  }
  if ((payload.expired || []).length) {
    sec3.appendChild(drill(`展開：已到期（${payload.expired.length}）`, () => watchList(payload.expired, labels)));
  }
  sec3.appendChild(el('p', 'note', notes.fired || ''));
  app.appendChild(sec3);

  app.appendChild(stateFooter(payload, '這一頁不是什麼'));
  window.scrollTo(0, 0);
}

/* 共用頁尾：新鮮度 ＋ authority ＋「不是什麼」。三個 state 頁面同一份。 */
function stateFooter(payload, notTitle) {
  const wrap = el('div');
  const f = payload.freshness || {};
  const sec = el('section', 'panel');
  sec.appendChild(el('h2', null, '這份畫面有多新'));
  const rows = el('div', 'rows');
  rows.appendChild(kv('materialize 於', `${f.generated_at}（${Number(f.age_hours).toFixed(1)} 小時前，${f.state}）`));
  rows.appendChild(kv('權威', `${(payload.authority || {}).function}（${(payload.authority || {}).command}）`));
  rows.appendChild(kv('新鮮度身分', payload.freshness_identity));
  rows.appendChild(kv('artifact content digest', payload.content_digest));
  sec.appendChild(rows);
  sec.appendChild(el('p', 'note', f.rule || ''));
  sec.appendChild(el('p', 'note', (payload.authority || {}).note || ''));
  wrap.appendChild(sec);
  const not = el('section', 'panel');
  not.appendChild(el('h2', null, notTitle));
  not.appendChild(listOf(payload.this_is_not || []));
  wrap.appendChild(not);
  return wrap;
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

/* 欄位名一律白話：術語（錨點／excess）只出現在下方說明列，不放進表頭。
   2026-09-08 使用者：「錨點前／入圖以來／超額是啥意思」——那三個詞要查表才懂，就不該當欄名。 */
function positionColumns(benchmark) {
  return [
    { title: '標的', cell: (row, set) => companyCell({ ticker: row.ticker, company_id: row.company_id }, set) },
    { title: '起算日', cell: (row) => el('td', 'nowrap', row.anchor_date || '—') },
    { title: '報價日', cell: (row) => el('td', 'nowrap', row.current_date || '—') },
    { title: '起算前 30 天', cell: (row) => returnCell(row.pre_anchor_return) },
    { title: '起算後到現在', cell: (row) => returnCell(row.absolute_return) },
    { title: `同期比 ${benchmark || 'QQQ'} 多／少`, cell: (row) => returnCell(row.excess_return) },
  ];
}

const LIVE_COLUMNS = [
  { title: '標的', cell: (row, set) => companyCell({ ticker: row.ticker, company_id: row.company_id }, set) },
  { title: '成交日', cell: (row) => el('td', 'nowrap', row.executed_at || '—') },
  { title: '成交價', cell: (row) => el('td', 'nowrap', fmtQuantity(row.price, row.currency) || '—') },
  { title: '股數', cell: (row) => el('td', 'nowrap', fmtNumber(row.shares, 4) || '—') },
  { title: '現價', cell: (row) => el('td', 'nowrap', fmtQuantity(row.current, row.current_currency) || '—') },
  { title: 'live 報酬', cell: (row) => returnCell(row.live_return) },
  { title: '同檔 shadow', cell: (row) => returnCell(row.shadow_return) },
];

async function renderPositions() {
  markNav('positions');
  let payload;
  try {
    payload = await getJSON(`${API}/positions`);
  } catch (err) {
    renderStateError(err, '讀不到部位與問責');
    return;
  }
  const notes = payload.notes || {};
  const c = payload.counters || {};
  const agg = payload.aggregate || {};
  const health = payload.anchor_health;
  const live = payload.live || {};
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

  // ① 真實部位在最前面——那才是「你的錢在哪」。
  const sec0 = el('section', 'panel callout');
  sec0.appendChild(el('h2', null, `真實成交的部位（${(live.tickers || []).length} 檔）`));
  if ((live.rows || []).length) {
    sec0.appendChild(rankTable(live.rows, LIVE_COLUMNS, detailSet));
  } else {
    sec0.appendChild(el('p', 'note', '目前沒有任何真實成交的部位——所有 cohort 都只有 paper 記分板。'));
  }
  sec0.appendChild(mdParagraph(notes.two_anchors || ''));
  if ((live.tickers || []).length < 3) {
    sec0.appendChild(el('p', 'warn',
      `▲ live 樣本僅 ${(live.tickers || []).length} 檔，不足以回答「系統準不準」。`
      + '這個數字只有靠累積真實下單才會變大，時間經過不會讓它自己滿足。'));
  }
  sec0.appendChild(el('p', 'note', `只有 paper 的 cohort：${(live.paper_only || []).length} 個。`));
  app.appendChild(sec0);

  // ② 樣本效度**先於**數字——排版順序本身就是判準的一部分。
  if (health) {
    const sec1 = el('section', 'panel');
    sec1.appendChild(el('h2', null, '這批數字能證明什麼（先看這裡）'));
    sec1.appendChild(el('div', 'panel-questions',
      '下面的漲跌是真的，但「它代表系統選股很準」不一定成立——差別在起算日的意義。'));
    if (health.judgment_anchors === 0) {
      sec1.appendChild(el('p', 'warn',
        '■ 沒有任何一檔的起算日是「你決定要買」的那天——所以下面的漲跌不能當成選股能力的證據。'
        + 'cohort 由入圖建立，錨點的語意是「這家公司的 claim 那天進圖」，不是「那天是進場時機」。'));
      sec1.appendChild(el('p', 'note', notes.judgment_anchor || ''));
    }
    if (health.span_days < health.span_warn_days) {
      sec1.appendChild(el('p', 'warn',
        `▲ 這些起算日全擠在 ${health.span_days} 天內——不能當成 ${health.paired} 個獨立的驗證。`
        + '這批 cohort 建立於同一段期間，若又同屬一個主題，超額很可能是同一次行情被相關標的複製多次。'));
    }
    const rows = el('div', 'rows');
    rows.appendChild(kv('起算日是「你真的決定要買」的那天',
      `${health.judgment_anchors} 檔｜其餘 ${health.paired - health.judgment_anchors} 檔的起算日只是「被放進清單」`));
    rows.appendChild(kv('這些起算日集中在多長的期間',
      `${health.first} ~ ${health.last}（${health.span_days} 天，橫跨 ${health.weeks} 個日曆週）`));
    rows.appendChild(kv(`被放進清單前 ${health.pre_anchor_days} 天，中位漲跌`, fmtRatioPct(health.pre_median, 1) || '—'));
    rows.appendChild(kv('被放進清單後到現在，中位漲跌', fmtRatioPct(health.post_median, 1) || '—'));
    rows.appendChild(kv('放進清單前漲得比放進後多的',
      `${health.chasing} / ${health.paired} 檔` + (health.chasing_tickers.length ? `（${health.chasing_tickers.join('、')}）` : '')
      + '——這個比例高代表我們常在漲完之後才注意到'));
    sec1.appendChild(rows);
    sec1.appendChild(mdParagraph(notes.sample_validity || ''));
    app.appendChild(sec1);
  }

  // ③ 常駐計數器
  const sec2 = el('section', 'panel');
  sec2.appendChild(el('h2', null, '常駐計數器'));
  sec2.appendChild(kpiRow([
    { label: '追蹤中的公司', value: `${c.eligible_cohorts}/${c.total_cohorts}`,
      sub: `研究完整到可以進清單的／全部建過檔的${c.legacy_eligible_cohorts ? `；另有 ${c.legacy_eligible_cohorts} 個還用舊判準` : ''}` },
    { label: '算得出報酬的', value: `${c.shadow_measurable_cohorts}/${c.shadow_anchored_cohorts}`,
      sub: '有起算價、抓得到現價的；其餘多半是未上市或沒有代碼' },
    { label: '真實下單', value: `${c.live_choices} 次決定／${c.live_fills} 筆成交`,
      sub: '「系統準不準」只靠這個數字變大，時間經過不會讓它自己滿足' },
    { label: '已結案的判斷', value: `${c.measured_outcomes}/${c.outcomes}`,
      sub: '已經收尾、而且算得出結果的／全部收尾的（內部叫「結案歸因」）' },
  ]));
  if (c.duplicate_cohort_companies || c.orphan_cohorts) {
    sec2.appendChild(el('p', 'note',
      `不進分母但必須現形：重複 cohort ${c.duplicate_cohort_companies || 0}｜無 identity 殘骸 ${c.orphan_cohorts || 0}`));
  }
  app.appendChild(sec2);

  // ④ 等權重聚合
  const sec3 = el('section', 'panel');
  sec3.appendChild(el('h2', null, '推薦籃子整體（等權重）'));
  const aggRow = el('div', 'numbers');
  aggRow.appendChild(numberBlock('絕對', agg.absolute === null || agg.absolute === undefined ? '—' :
    (agg.absolute > 0 ? '+' : '') + fmtRatioPct(agg.absolute, 1), `${agg.n} 檔等權`, signClass(agg.absolute)));
  if (agg.excess !== null && agg.excess !== undefined) {
    aggRow.appendChild(numberBlock(`超額（vs ${agg.benchmark}）`,
      (agg.excess > 0 ? '+' : '') + fmtRatioPct(agg.excess, 1), `已量測 ${agg.measured}/${agg.total}`, signClass(agg.excess)));
  }
  sec3.appendChild(aggRow);
  /* 時序（2026-09-11）。**一個點不是趨勢**——先前這裡只有當天的聚合值，因為落檔用的是
     覆寫制，於是「系統的判斷準不準」結構上只能回答今天。樣本外驗證需要歷史。 */
  const series = payload.aggregate_series || {};
  const srows = series.rows || [];
  if (srows.length >= 2) {
    const first = srows[0];
    const last = srows[srows.length - 1];
    sec3.appendChild(el('p', 'note',
      `時序：${srows.length} 個交易日（${first.date} → ${last.date}）；`
      + `等權絕對 ${fmtRatioPct(first.equal_weight_absolute, 1)} → ${fmtRatioPct(last.equal_weight_absolute, 1)}。`));
  } else {
    sec3.appendChild(el('p', 'note',
      `時序：目前 ${srows.length} 天。${series.reason || '每天累積一筆，兩天以上才看得出趨勢。'}`));
  }
  if (series.skipped) {
    sec3.appendChild(el('p', 'note', `（時序檔有 ${series.skipped} 行解析失敗，已跳過但沒有靜默丟棄）`));
  }
  sec3.appendChild(mdParagraph(notes.aggregate || ''));
  app.appendChild(sec3);

  /* ④b power-law 三量（D15，2026-09-18）。**與等權並列不是取代**：上面那格回答
     「排序整體準不準」，這一格回答「有沒有抓到那一檔」——賭注是小賠多檔一檔補回，
     平均值天生看不到它。`null` ＝ 這次沒算（舊 artifact），不是「都是 0」。 */
  const pl = payload.power_law;
  const sec3b = el('section', 'panel');
  sec3b.appendChild(el('h2', null, '有沒有抓到那一檔（power-law 三量）'));
  if (!pl || !pl.n) {
    sec3b.appendChild(el('p', 'note',
      '這份 artifact 還沒有 power-law 三量——跑一次 `python -m webapp materialize --positions` 產生。'));
  } else {
    const top = pl.top_contributor || {};
    /* `fmtRatioPct` 對非數字回 `null`，直接字串相接會印出「+null」——artifact 是外部資料，
       前端不得假設欄位一定是數字（既有的等權那格也是先檢查再接）。缺值印「—」。 */
    const signed = (v, digits) => (typeof v === 'number' && isFinite(v)
      ? (v > 0 ? '+' : '') + fmtRatioPct(v, digits) : '—');
    const plRow = el('div', 'numbers');
    plRow.appendChild(numberBlock('籃子總報酬', signed(pl.basket_total_return, 2),
      `${pl.n} 檔等權（與上一格同一個數字）`, signClass(pl.basket_total_return)));
    plRow.appendChild(numberBlock(`最大單檔　${top.ticker || '?'}`,
      signed(top.contribution, 2),
      `該檔 ${signed(top.absolute_return, 1)}`
      + (typeof top.peak_return === 'number' ? `，期間高點 ${signed(top.peak_return, 1)}` : ''),
      signClass(top.contribution)));
    plRow.appendChild(numberBlock(`其餘 ${top.rest_n} 檔合計`,
      signed(top.rest_contribution, 2),
      '恆等式：總報酬 ＝ 最大單檔 ＋ 其餘（刻意不做除法）', signClass(top.rest_contribution)));
    sec3b.appendChild(plRow);
    sec3b.appendChild(el('p', 'note',
      `曾達 2 倍 ${pl.reached_2x_ever}/${pl.peak_measured} 檔（現價仍在 2 倍以上 ${pl.reached_2x_now}）`
      + `｜量測起始 ${pl.measurement_start || '?'}、最長已持有 ${pl.max_days_held} 天。`
      + '　用期間高點算的那個是進行中的下界，只增不減。'));
    const mat = pl.maturity || {};
    const matText = ['12m', '24m'].map((k) => {
      const m = mat[k] || {};
      return m.matured
        ? `${k}：${m.reached_2x}/${m.matured} 檔（${fmtRatioPct(m.share, 0) || '—'}）`
        : `${k}：分母還沒出現（沒有一檔滿 ${k}）`;
    }).join('｜');
    sec3b.appendChild(el('p', 'note', `達 2 倍的比例　${matText}`));
    (pl.known_biases || []).forEach((b) => sec3b.appendChild(mdParagraph('⚠ ' + b)));
  }
  sec3b.appendChild(mdParagraph(notes.power_law || ''));
  app.appendChild(sec3b);

  /* ④c 賭注收斂（V4，2026-09-19）。**第三個維度**：上面兩格都以股價為錨點，而本圖標的
     同漲同跌；共識修正不受 beta 污染，也不需要賣出就能驗證。
     ⚠ 「共識沒動」與「賭注寫下後還沒有共識抓取」是相反的結論，這裡分成兩格印。 */
  const bc = payload.bet_convergence;
  const sec3c = el('section', 'panel');
  sec3c.appendChild(el('h2', null, '市場承認了嗎（賭注收斂）'));
  if (!bc) {
    sec3c.appendChild(el('p', 'note',
      '這份 artifact 還沒有賭注收斂——跑一次 `python -m webapp materialize --positions` 產生。'));
  } else if (!bc.n_bets) {
    sec3c.appendChild(el('p', 'note',
      `還沒有任何一檔寫下賭注（掃過 ${bc.scanned == null ? '?' : bc.scanned} 檔）`
      + '——這不是 0%，是還沒有分子也沒有分母。'));
  } else {
    const bcRow = el('div', 'numbers');
    bcRow.appendChild(numberBlock('朝我們移動', String(bc.toward_us),
      `有賭注 ${bc.n_bets} 檔、量得到 ${bc.measurable} 檔`, bc.toward_us > 0 ? 'pos' : null));
    bcRow.appendChild(numberBlock('反向移動', String(bc.away_from_us),
      '共識往我們的反方向走', bc.away_from_us > 0 ? 'neg' : null));
    bcRow.appendChild(numberBlock('共識沒動', String(bc.unchanged),
      bc.shortest_window_days == null ? '市場看過了、沒改'
        : `已觀測 ${bc.shortest_window_days}–${bc.longest_window_days} 天`));
    bcRow.appendChild(numberBlock('還沒輪到市場說話', String(bc.not_yet_observable),
      '賭注寫下後還沒有共識抓取　←這不是「沒動」'));
    sec3c.appendChild(bcRow);
    const bcList = el('ul', 'notes');
    (bc.rows || []).forEach((r) => {
      const since = r.bet_since || '?';
      if (r.state === 'not_yet_observable') {
        bcList.appendChild(el('li', null,
          `${r.ticker}：賭注 ${since} 寫下，之後還沒有共識抓取`
          + (typeof r.days_waiting === 'number' ? `（已等 ${r.days_waiting} 天）` : '')));
        return;
      }
      /* 分母（起點差距）跟著比例一起印：它極小時比例會被放大到不可讀，
         只看「移了 −7175%」的人會以為共識大幅反向跑掉。 */
      bcList.appendChild(el('li', null,
        `${r.ticker}：自 ${since} 起 ${r.n_points} 次抓取，共識朝我們移了 ${signedPct(r.closed_fraction, 1)}`
        + `（起點差距 ${typeof r.gap_at_start === 'number' ? r.gap_at_start.toFixed(4) : '—'}）`
        + `　[${r.state}]`));
    });
    sec3c.appendChild(bcList);
    if (bc.no_bet) {
      sec3c.appendChild(el('p', 'note', `另有 ${bc.no_bet} 檔沒有寫下賭注（只進計數，不進上面的清單）。`));
    }
    (bc.known_biases || []).forEach((b) => sec3c.appendChild(mdParagraph('⚠ ' + b)));
  }
  sec3c.appendChild(mdParagraph(notes.bet_convergence || ''));
  app.appendChild(sec3c);

  // ⑤ 逐檔
  const sec4 = el('section', 'panel');
  sec4.appendChild(el('h2', null, `逐檔（${payload.rows.length}）`));
  sec4.appendChild(rankTable(payload.rows, positionColumns((payload.benchmarks || {}).primary), detailSet));
  const legend = el('ul', 'notes');
  [['起算日', '這檔被放進追蹤清單的那天（內部叫「錨點」）。**它不是你買進的日子**——除非那筆有真實成交。'],
   ['起算前 30 天', '在被放進清單之前的一個月，它自己漲跌了多少。這一欄是用來看「我們是不是總在追已經漲完的東西」。'],
   ['起算後到現在', '從那天到最新收盤，它漲跌了多少（內部叫「入圖以來」）。'],
   [`同期比 ${(payload.benchmarks || {}).primary || 'QQQ'} 多／少`,
    '同一段期間內，它比大盤多賺或少賺幾個百分點（內部叫「超額報酬」）。正的代表跑贏。']]
    .forEach(([term, note]) => {
      const li = el('li');
      li.appendChild(el('b', null, term));
      li.appendChild(document.createTextNode('：'));
      li.appendChild(mdInline(note));
      legend.appendChild(li);
    });
  sec4.appendChild(legend);
  if ((payload.unavailable || []).length) {
    sec4.appendChild(el('p', 'note',
      `另有 ${payload.unavailable.length} 個 cohort 的 Shadow 是 unavailable，無錨點可計算（多半是無 ticker 的未上市或殘骸）。`));
  }
  sec4.appendChild(el('p', 'warn', '▲ ' + (notes.monitoring || '')));
  app.appendChild(sec4);

  app.appendChild(stateFooter(payload, '這一頁不是什麼'));
  window.scrollTo(0, 0);
}

/* ---------- 路由 ---------- */

async function route() {
  const hash = window.location.hash || '#/';
  const target = decodeURIComponent(hash.replace(/^#\/?/, ''));
  app.textContent = '';
  app.appendChild(el('p', 'loading', '載入中…'));
  try {
    if (!VOCAB) {
      const meta = await getJSON(`${API}/meta`);
      VOCAB = meta.vocabularies || {};
    }
    // `ranking` 是保留字：ticker 一律大寫（store 的 slug 規則），所以不會撞到真實代碼。
    if (target === 'basket') await renderBasket();
    else if (target === 'multi-year') await renderMultiYear();
    else if (target === 'ranking') await renderRanking();
    else if (target === 'beta') await renderBeta();
    else if (target === 'coverage') await renderCoverage();
    else if (target === 'watches') await renderWatches();
    else if (target === 'positions') await renderPositions();
    else if (target) await renderDetail(target);
    else await renderList();
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

window.addEventListener('hashchange', route);
route();
