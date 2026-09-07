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

const ABSENCE_SHORT = {
  not_yet_recorded: '還沒寫',
  deliberate_abstention: '刻意不主張',
  method_not_applicable: '方法不適用',
  upstream_unavailable: '上游缺料',
  inputs_incompatible: '輸入身分不相容',
  provider_missing: '來源不提供',
  capability_absent: '本層沒有這個能力',
  point_in_time_unavailable: '此視角無時點投影',
  insufficient_evidence: '證據不足',
  invalidated: '已失效',
  not_applicable_unspecified: '宣告不適用（未說哪一種）',
};

function absenceBadge(kind) {
  if (!kind) return null;
  const badge = el('span', 'badge ' + (isSettled(kind) ? 'badge-settled' : 'badge-absence'),
                   ABSENCE_SHORT[kind] || kind);
  badge.title = absenceLabel(kind);
  return badge;
}

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

  // 只有真的有 target 才顯示這一格——沒有就顯示「為什麼沒有」，不補任何倍數。
  const target = row.future_target;
  if (target.value !== null && target.value !== undefined) {
    numbers.appendChild(numberBlock(
      'Future target',
      fmtQuantity(target.value, target.currency) || '—',
      target.value_date && target.value_date.value ? `@ ${target.value_date.value}` : ''));
  }

  const ret = row.implied_return.simple;
  const ann = row.implied_return.annualized;
  if (typeof ret.value === 'number') {
    numbers.appendChild(numberBlock(
      '隱含報酬',
      fmtPercent(ret.value),
      typeof ann.value === 'number' ? `年化 ${fmtPercent(ann.value)}` : '',
      signClass(ret.value)));
  }
  card.appendChild(numbers);

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
  const data = await getJSON(`${API}/stocks`);
  app.textContent = '';
  footerWarning.textContent = data.correlation_warning || '';
  if (!data.stocks.length && !data.unavailable.length) {
    app.appendChild(el('p', 'empty',
      '還沒有任何 materialized 判讀。請在本機跑 `python -m webapp materialize <TICKER>`。'));
    return;
  }
  const cards = el('div', 'cards');
  data.stocks.forEach((row) => cards.appendChild(renderCard(row)));
  app.appendChild(cards);

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
  if (text !== null) {
    const cell = el('div', 'row-value', text);
    if (datum.unit === 'ratio' && typeof datum.value === 'number') cell.classList.add(signClass(datum.value));
    row.appendChild(cell);
  } else if (datum.value && typeof datum.value === 'object') {
    row.appendChild(el('div', 'row-value', '見下方展開'));
  } else {
    row.classList.add('row-absent');
    const cell = el('div', 'row-value');
    const badge = absenceBadge(datum.absence_kind);
    if (badge) cell.appendChild(badge); else cell.appendChild(document.createTextNode('—'));
    row.appendChild(cell);
  }
  if (datum.reason) row.appendChild(el('div', 'row-reason', datum.reason));
  return row;
}

function renderRows(lines, filterRoles) {
  const box = el('div', 'rows');
  lines.filter((line) => !filterRoles || filterRoles.indexOf(line.role) >= 0)
    .forEach((line) => box.appendChild(renderRow(line.display_label, line.datum)));
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

function drill(title, buildBody) {
  const node = document.createElement('details');
  node.appendChild(el('summary', null, title));
  node.appendChild(buildBody());
  return node;
}

function renderHeadline(view) {
  const panel = view.headline;
  const node = panelShell(panel, '① 頭條：現價 → future target → 隱含報酬');
  const lines = lineMap(panel);

  const numbers = el('div', 'headline-numbers');
  const price = lines.current_price && lines.current_price.datum;
  const quoteUnit = price && price.dependencies ? price.dependencies.quote_unit : null;
  if (price) {
    numbers.appendChild(numberBlock('現價', fmtQuantity(price.value, quoteUnit) || '—',
      price.as_of ? `bar ${price.as_of}` : ''));
  }
  const target = lines.fair_value && lines.fair_value.datum;
  const valueDate = lines.value_date && lines.value_date.datum;
  if (target && target.value !== null && target.value !== undefined) {
    const currency = target.dependencies ? target.dependencies.currency : null;
    numbers.appendChild(numberBlock('Future target value',
      fmtQuantity(target.value, currency) || '—',
      valueDate && valueDate.value ? `@ ${valueDate.value}` : ''));
  }
  const ret = lines.price_return && lines.price_return.datum;
  const ann = lines.annualized_price_return && lines.annualized_price_return.datum;
  if (ret && typeof ret.value === 'number') {
    numbers.appendChild(numberBlock('隱含價格報酬', fmtPercent(ret.value),
      ann && typeof ann.value === 'number' ? `年化 ${fmtPercent(ann.value)}` : '', signClass(ret.value)));
  }
  if (numbers.childNodes.length) node.appendChild(numbers);

  // 沒有 target／沒有報酬時：把「為什麼沒有」放到跟數字一樣顯眼的位置，而不是留白。
  [['Future target value', target], ['隱含價格報酬', ret]].forEach(([label, datum]) => {
    if (!datum || datum.value !== null && datum.value !== undefined) return;
    const box = el('div', 'attention ' + (isSettled(datum.absence_kind) ? 'settled' : 'blocked'));
    const head = el('div', 'attention-head');
    head.appendChild(document.createTextNode(label + '：'));
    const badge = absenceBadge(datum.absence_kind);
    if (badge) head.appendChild(badge);
    box.appendChild(head);
    if (datum.reason) box.appendChild(el('div', 'attention-body', datum.reason));
    box.appendChild(el('div', 'attention-body', absenceLabel(datum.absence_kind) || ''));
    node.appendChild(box);
  });

  const one = lines.epistemics_one_sentence && lines.epistemics_one_sentence.datum;
  if (one && one.value && one.value.one_sentence) {
    const box = el('div', 'onesentence', one.value.one_sentence);
    box.appendChild(el('span', 'src', '出處：implied_return.epistemics.one_sentence（authority 自組，不是本畫面造的句子）'));
    node.appendChild(box);
  }

  const basis = basisDisplay((panel.context || {}).accounting_basis);
  const meta = el('div', 'meta-line',
    `期間 ${(panel.context || {}).period || '—'}　口徑 ${basis.label}（contract 值 ${basis.raw || 'null'}）`);
  meta.title = basis.note;
  node.appendChild(meta);
  node.appendChild(el('p', 'note', basis.note));

  node.appendChild(drill('展開：頭條的每一格（含缺席理由）', () => renderRows(panel.lines)));
  if (one && one.value) {
    node.appendChild(drill('展開：這個數字裡多少是算術、多少是判斷', () => {
      const box = el('div', 'rows');
      const e = one.value;
      (e.deterministic || []).forEach((t) => box.appendChild(kv('確定性算術', t)));
      (e.observations || []).forEach((t) => box.appendChild(kv('觀測', t)));
      Object.keys(e.judgment_inputs || {}).forEach((k) => {
        box.appendChild(kv('判斷輸入 · ' + k, JSON.stringify(e.judgment_inputs[k])));
      });
      (e.this_is_not || []).forEach((t) => box.appendChild(kv('這不是', t)));
      return box;
    }));
  }
  if (panel.notes && panel.notes.length) {
    node.appendChild(drill('展開：這一段不是什麼', () => listOf(panel.notes)));
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
  const node = panelShell(panel, '② 我們預測什麼 vs 市場預測什麼');
  const groups = [
    ['internal', '我們的內部預測'],
    ['consensus_same_period', '同期、同口徑的市場共識（可比）'],
    ['comparison', '兩者的落差'],
    ['consensus_other_period', '其他期間的共識（呈現用，不可與內部相減）'],
    ['market_context', '市場脈絡'],
    ['market_proxy', '價格隱含的粗略代理'],
  ];
  groups.forEach(([role, title], index) => {
    const rows = (panel.lines || []).filter((line) => line.role === role);
    if (!rows.length) return;
    node.appendChild(el('div', 'group-title', title));
    // 前三組直接展開（那是消費者要的答案）；其餘收進 drill-down，避免首屏被淹掉。
    if (index < 3) node.appendChild(renderRows(rows));
    else node.appendChild(drill(`展開：${title}（${rows.length} 項）`, () => renderRows(rows)));
  });
  const basis = basisDisplay((panel.context || {}).accounting_basis);
  node.appendChild(el('p', 'note',
    `內部口徑：${basis.label}（contract 值 ${basis.raw || 'null'}）。${(panel.context || {}).same_period_rule || ''}`));
  if (panel.notes && panel.notes.length) {
    node.appendChild(drill('展開：這一段的警告與涵蓋率說明', () => listOf(panel.notes)));
  }
  return node;
}

function renderWhy(view) {
  const panel = view.why;
  const node = panelShell(panel, '③ 為什麼：最脆弱的假設在哪');
  if (panel.weak_inputs && panel.weak_inputs.length) {
    node.appendChild(el('div', 'group-title', '最脆弱的輸入（依宣告好的列入規則，不是新判斷）'));
    const list = el('ul', 'weak');
    panel.weak_inputs.forEach((item) => {
      const li = el('li');
      const text = valueText(item.datum);
      li.appendChild(document.createTextNode(item.display_label + (text ? '：' + text : '')));
      const rule = (VOCAB && VOCAB.weak_input_rules && VOCAB.weak_input_rules[item.rule]) || item.rule;
      li.appendChild(el('span', 'rule', `列入規則 ${item.rule}｜${rule}`));
      if (item.datum.reason) li.appendChild(el('span', 'rule', truncate(item.datum.reason, 260)));
      list.appendChild(li);
    });
    node.appendChild(list);
  }
  const byRole = [
    ['assumption', '生效的假設'],
    ['sensitivity', '敏感度（估值層已算好，本畫面只排序）'],
    ['trace', '算式逐格'],
    ['epistemics', '算術 vs 判斷的分解'],
  ];
  byRole.forEach(([role, title]) => {
    const rows = (panel.lines || []).filter((line) => line.role === role);
    if (!rows.length) return;
    node.appendChild(drill(`展開：${title}（${rows.length} 項）`, () => renderRows(rows)));
  });
  if (panel.evidence && panel.evidence.length) {
    node.appendChild(drill(`展開：證據來源（${panel.evidence.length} 條）`, () => {
      const box = el('div', 'rows');
      panel.evidence.forEach((item) => {
        const row = el('div', 'row');
        row.appendChild(el('div', 'row-label', item.ref));
        row.appendChild(el('div', 'row-value', item.tier || item.kind || ''));
        if (item.label || item.note) row.appendChild(el('div', 'row-reason', item.label || item.note));
        box.appendChild(row);
      });
      return box;
    }));
  }
  return node;
}

function renderResearch(view) {
  const panel = view.research;
  const node = panelShell(panel, '④ 研究現況：什麼會改變這個答案');
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
    node.appendChild(drill(`展開：催化劑（${panel.catalysts.length}）`, () => listOf(
      panel.catalysts.map((c) => [c.label, c.due, c.state].filter(Boolean).join('｜')))));
  }
  if (panel.checkpoints && panel.checkpoints.length) {
    node.appendChild(drill(`展開：檢核點（${panel.checkpoints.length}）`, () => listOf(
      panel.checkpoints.map((c) => [c.label, c.due, c.state].filter(Boolean).join('｜')))));
  }
  if (panel.risks && panel.risks.length) {
    node.appendChild(drill(`展開：風險（${panel.risks.length}）`, () => listOf(panel.risks)));
  }
  const scores = (panel.lines || []).filter((line) => line.role === 'score');
  if (scores.length) node.appendChild(drill(`展開：五軸判斷（${scores.length}）`, () => renderRows(scores)));
  if (panel.attention && panel.attention.length) {
    node.appendChild(drill(`展開：需要重看的研究成果（${panel.attention.length}）`, () => listOf(
      panel.attention.map((a) => `${a.artifact_type}：${a.state}｜${(a.reasons || []).join('；')}`))));
  }
  return node;
}

function renderEntry(view) {
  const panel = view.entry;
  const node = panelShell(panel, '⑤ Entry threshold（optional，不影響 readiness）');
  node.appendChild(el('p', 'note', (panel.context || {}).optional_rule || ''));
  node.appendChild(renderRows(panel.lines));
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
    node.appendChild(drill('展開：refresh 註記', () => listOf(payload.refresh.notes)));
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
  node.appendChild(drill('展開：readiness 的判準原文', () => el('p', 'note', readiness.rule)));
  return node;
}

async function renderDetail(ticker) {
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

  app.appendChild(renderReadiness(payload));
  app.appendChild(renderHeadline(view));
  app.appendChild(renderFundamental(view));
  app.appendChild(renderWhy(view));
  app.appendChild(renderResearch(view));
  app.appendChild(renderEntry(view));
  app.appendChild(renderFreshness(payload));

  const limits = el('section', 'panel');
  limits.appendChild(el('h2', null, '這份判讀不是什麼'));
  limits.appendChild(listOf(view.limits || []));
  if (view.warnings && view.warnings.length) {
    limits.appendChild(drill(`展開：組裝時的警告（${view.warnings.length}）`, () => listOf(view.warnings)));
  }
  app.appendChild(limits);
  window.scrollTo(0, 0);
}

/* ---------- 路由 ---------- */

async function route() {
  const hash = window.location.hash || '#/';
  const ticker = decodeURIComponent(hash.replace(/^#\/?/, ''));
  app.textContent = '';
  app.appendChild(el('p', 'loading', '載入中…'));
  try {
    if (!VOCAB) {
      const meta = await getJSON(`${API}/meta`);
      VOCAB = meta.vocabularies || {};
    }
    if (ticker) await renderDetail(ticker);
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
