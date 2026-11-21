/* ==========================================================================
   Reference renderer. All data below is SAMPLE DATA.
   In the real app, replace the constants with API responses (see api-contract.md).
   Map geometry rule: roads are absolutely-positioned divs rotated from node A to node B.
   ========================================================================== */

// ---- 12-node Metro Smart City layout, drawn in a 640 x 340 box ------------------
const NODES = {
  N_GATE: [320, 40], NW_RES: [124, 84], NE_TECH: [516, 84], RIVER_BR: [320, 116],
  W_BYPASS: [40, 182], W_IND: [124, 182], DOWNTOWN: [320, 182], E_FIN: [516, 182], E_BYPASS: [600, 182],
  SW_PORT: [124, 292], S_CIVIC: [320, 292], SE_SUB: [516, 292],
};
const LABEL_AT = {
  N_GATE: 'above', NW_RES: 'above', NE_TECH: 'above', RIVER_BR: 'right',
  W_BYPASS: 'below', W_IND: 'below', DOWNTOWN: 'below', E_FIN: 'below', E_BYPASS: 'below',
  SW_PORT: 'below', S_CIVIC: 'below', SE_SUB: 'below',
};
// [from, to, congestion level]  (19 road pairs = 38 directed segments)
const EDGES = [
  ['W_BYPASS', 'NW_RES', 'low'], ['NW_RES', 'N_GATE', 'idle'], ['N_GATE', 'NE_TECH', 'idle'], ['NE_TECH', 'E_BYPASS', 'low'],
  ['E_BYPASS', 'SE_SUB', 'idle'], ['SE_SUB', 'S_CIVIC', 'low'], ['S_CIVIC', 'SW_PORT', 'high'], ['SW_PORT', 'W_BYPASS', 'idle'],
  ['N_GATE', 'RIVER_BR', 'idle'], ['RIVER_BR', 'DOWNTOWN', 'low'], ['DOWNTOWN', 'S_CIVIC', 'idle'], ['NW_RES', 'W_IND', 'idle'],
  ['W_IND', 'SW_PORT', 'high'], ['NE_TECH', 'E_FIN', 'idle'], ['E_FIN', 'SE_SUB', 'low'], ['W_IND', 'DOWNTOWN', 'idle'],
  ['DOWNTOWN', 'E_FIN', 'idle'], ['NW_RES', 'DOWNTOWN', 'idle'], ['NE_TECH', 'DOWNTOWN', 'moderate'],
];
const ROAD_COLOR = { idle: '#CAD3CD', low: '#5E9A78', moderate: '#E0A33A', high: '#E2784A', severe: '#C8534E' };
const ROAD_THICK = { idle: 8, low: 8, moderate: 9, high: 10, severe: 11 };

// ---- sample decisions (replace with GET /api/decisions) ---------------------------
const DECISIONS = [
  { id: 'R-1045', priority: 'high', from: 'NW_RES', to: 'SE_SUB', confidence: 87, tick: 'Tick 42 / 300',
    tags: ['Congestion risk', 'Signal delay'], impact: '−38 s',
    suggested: ['NW_RES', 'DOWNTOWN', 'E_FIN', 'SE_SUB'], current: ['NW_RES', 'W_IND', 'SW_PORT', 'S_CIVIC', 'SE_SUB'],
    eta: '46 s', saved: '38 s',
    explanation: 'The coordinator found a faster path through DOWNTOWN that avoids two congested segments on the west side.',
    bullets: ['Avoids 2 roads at high density', '38 s faster than the current route', 'Fewer stops at intersections'],
    factors: [['Traffic density', 92], ['Signal timing', 78], ['Road capacity', 65], ['Queue length', 58]],
    risks: [['Density rising on W_IND to SW_PORT', 'Expected within 12 ticks'], ['Queue forming at S_CIVIC', 'Moderate, 3 vehicles']],
    impactRows: [['Travel time', '−38 s'], ['Queue length', '−3 veh'], ['Energy use', '−0.4 kWh']], history: 94 },
  { id: 'R-1048', priority: 'medium', from: 'W_BYPASS', to: 'NE_TECH', confidence: 62, tick: 'Tick 57 / 300',
    tags: ['Queue risk'], impact: '−12 s',
    suggested: ['W_BYPASS', 'NW_RES', 'N_GATE', 'NE_TECH'], current: ['W_BYPASS', 'NW_RES', 'DOWNTOWN', 'NE_TECH'],
    eta: '41 s', saved: '12 s',
    explanation: 'Using the northern ring keeps the vehicle out of the DOWNTOWN junction, where a queue is likely to form soon.',
    bullets: ['Skips the DOWNTOWN junction', '12 s faster than the current route', 'Lower confidence: sparse history'],
    factors: [['Traffic density', 71], ['Signal timing', 64], ['Road capacity', 60], ['Queue length', 49]],
    risks: [['Queue risk at DOWNTOWN', 'Likely within 8 ticks'], ['Longer distance on the ring road', 'Adds 2 segments']],
    impactRows: [['Travel time', '−12 s'], ['Queue length', '−2 veh'], ['Energy use', '+0.1 kWh']], history: 81 },
  { id: 'R-1051', priority: 'low', from: 'DOWNTOWN', to: 'E_BYPASS', confidence: 92, tick: 'Tick 63 / 300',
    tags: ['Energy saving'], impact: '−6 s',
    suggested: ['DOWNTOWN', 'E_FIN', 'SE_SUB', 'E_BYPASS'], current: ['DOWNTOWN', 'NE_TECH', 'E_BYPASS'],
    eta: '28 s', saved: '6 s',
    explanation: 'The east corridor avoids the busy diagonal to NE_TECH and keeps speeds steady along the way.',
    bullets: ['Avoids the diagonal to NE_TECH', 'Roads stay below 40% density', 'Small but steady saving'],
    factors: [['Traffic density', 88], ['Signal timing', 83], ['Road capacity', 79], ['Queue length', 70]],
    risks: [['Diagonal NE_TECH to DOWNTOWN near 60%', 'Likely to rise'], ['No other risks found', 'Other segments below 40%']],
    impactRows: [['Travel time', '−6 s'], ['Queue length', '0 veh'], ['Energy use', '−0.6 kWh']], history: 96 },
];
const ACTIVITY = [
  { id: 'R-1042', verb: 'Approved', route: 'NE_TECH to E_BYPASS', when: '2 min ago', kind: 'ok' },
  { id: 'R-1043', verb: 'Modified', route: 'W_BYPASS to S_CIVIC', when: '15 min ago', kind: 'mod' },
  { id: 'R-1040', verb: 'Approved', route: 'N_GATE to SE_SUB', when: '28 min ago', kind: 'ok' },
];
const TABS = [['pending', 'Pending (7)'], ['approved', 'Approved (12)'], ['history', 'History']];

// ---- state ------------------------------------------------------------------------
const state = { sel: 0, tab: 'pending', done: {} };

// ---- helpers ----------------------------------------------------------------------
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const confClass = (c) => (c >= 85 ? 'hi' : c >= 70 ? 'mid' : 'lo');

function segStyle(a, b, th) {
  const [x1, y1] = NODES[a], [x2, y2] = NODES[b];
  const dx = x2 - x1, dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy).toFixed(1);
  const ang = (Math.atan2(dy, dx) * 180 / Math.PI).toFixed(2);
  return `left:${x1}px;top:${y1 - th / 2}px;width:${len}px;height:${th}px;transform:rotate(${ang}deg);`;
}
const pairs = (path) => path.slice(1).map((n, i) => [path[i], n]);

// ---- renderers --------------------------------------------------------------------
function renderTabs() {
  $('tabs').innerHTML = TABS.map(([k, label]) =>
    `<button class="tab ${state.tab === k ? 'on' : ''}" data-tab="${k}" aria-pressed="${state.tab === k}">${esc(label)}</button>`).join('');
}

function renderCards() {
  $('cards').innerHTML = DECISIONS.map((d, i) => `
    <article class="dcard ${i === state.sel ? 'sel' : ''}">
      <div class="row">
        <span class="badge ${d.priority}">${esc(d.priority)} priority</span>
        <span class="conf">Confidence: <b class="${confClass(d.confidence)}">${d.confidence}%</b></span>
      </div>
      <div class="id">#${esc(d.id)}</div>
      <div class="route"><span>${esc(d.from)}</span>
        <svg width="26" height="12" viewBox="0 0 26 12" fill="none" stroke="#5E6F66" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-label="to"><path d="M1 6h23M19 1.5L24 6l-5 4.5"/></svg>
        <span>${esc(d.to)}</span></div>
      <div class="tick">${esc(d.tick)}</div>
      <div class="tags">${d.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join('')}</div>
      <div class="row impact">Est. impact <b>${esc(d.impact)}</b></div>
      <div class="btns">
        <button class="key go" data-pick="${i}">Review</button>
        <button class="key" data-pick="${i}">More info</button>
      </div>
    </article>`).join('');
}

function renderMap(d) {
  const roads = EDGES.map(([a, b, lv]) =>
    `<div class="seg road" style="${segStyle(a, b, ROAD_THICK[lv])}background:${ROAD_COLOR[lv]}"></div>`).join('');
  const alt = pairs(d.current).map(([a, b]) => `<div class="seg alt" style="${segStyle(a, b, 5)}"></div>`).join('');
  const sug = pairs(d.suggested).map(([a, b]) => `<div class="seg sug" style="${segStyle(a, b, 9)}"></div>`).join('');
  $('map-roads').innerHTML = roads + alt + sug;

  const names = Object.keys(NODES);
  $('map-nodes').innerHTML = names.map((k) => {
    const [x, y] = NODES[k];
    let s = 18, bg = '#fff', bd = '#9CAAA1', ring = '';
    if (d.current.includes(k)) bd = '#6F93BE';
    if (d.suggested.includes(k)) bd = '#3B6A4F';
    if (k === d.from) { bg = '#3B6A4F'; bd = '#fff'; ring = 'box-shadow:0 0 0 3px #3B6A4F,0 2px 0 rgba(16,32,24,.18),0 5px 8px rgba(16,32,24,.25);'; s = 20; }
    if (k === d.to) { bg = '#1B2B23'; bd = '#fff'; ring = 'box-shadow:0 0 0 3px #1B2B23,0 2px 0 rgba(16,32,24,.18),0 5px 8px rgba(16,32,24,.25);'; s = 22; }
    return `<div class="node" style="left:${x - s / 2}px;top:${y - s / 2}px;width:${s}px;height:${s}px;background:${bg};border:3px solid ${bd};${ring}"></div>`;
  }).join('');
  $('map-labels').innerHTML = names.map((k) => {
    const [x, y] = NODES[k];
    const at = LABEL_AT[k];
    const pos = at === 'above' ? `left:${x}px;top:${y - 38}px;transform:translateX(-50%);`
      : at === 'below' ? `left:${x}px;top:${y + 16}px;transform:translateX(-50%);`
      : `left:${x + 16}px;top:${y - 11}px;`;
    const col = k === d.from ? 'color:#2F5A44;' : k === d.to ? 'color:#1B2B23;' : '';
    return `<div class="label" style="${pos}${col}">${esc(k)}</div>`;
  }).join('');
}

function renderReview() {
  const d = DECISIONS[state.sel];
  const status = state.done[state.sel];
  $('r-id').textContent = d.id;
  $('r-pri').className = `badge ${d.priority}`;
  $('r-pri').textContent = `${d.priority} priority`;
  $('r-status').hidden = !status;
  $('r-status').textContent = status === 'approved' ? 'Approved' : status === 'rejected' ? 'Rejected' : '';
  $('r-time').textContent = d.eta;
  $('r-saved').textContent = d.saved;
  $('r-conf').className = confClass(d.confidence);
  $('r-conf').textContent = `${d.confidence}%`;
  $('r-expl').textContent = d.explanation;
  $('r-bullets').innerHTML = d.bullets.map((b) =>
    `<li><span class="tick-ico" aria-hidden="true"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#2F5A44" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></span>${esc(b)}</li>`).join('');
  $('r-factors').innerHTML = d.factors.map(([l, v]) =>
    `<div class="factor"><div class="top"><span>${esc(l)}</span><span>${v}%</span></div><div class="bar"><i style="width:${v}%"></i></div></div>`).join('');
  $('r-risks').innerHTML = d.risks.map(([t, s]) => `<div class="risk"><strong>${esc(t)}</strong><span>${esc(s)}</span></div>`).join('');
  $('r-impact').innerHTML = d.impactRows.map(([k, v]) => `<div class="kv"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join('');
  $('r-hist').style.background = `conic-gradient(#4F7F63 0 ${d.history}%, #DDE5DF ${d.history}% 100%)`;
  $('r-hist-n').textContent = `${d.history}%`;
  $('approve-label').textContent = status === 'approved' ? 'Approved' : 'Approve';
  $('approve-sub').textContent = status === 'approved' ? 'Decision recorded' : 'Move to the next review';
  renderMap(d);
}

function renderActivity() {
  const ok = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';
  const mod = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4L19 9a2.1 2.1 0 00-3-3L5 17v3z"/></svg>';
  $('activity').innerHTML = ACTIVITY.map((a) => `
    <li><span class="act-ico ${a.kind === 'mod' ? 'mod' : ''}" aria-hidden="true">${a.kind === 'mod' ? mod : ok}</span>
      <span class="act-text"><strong>#${esc(a.id)} ${esc(a.verb)}</strong><br><span>${esc(a.route)}</span></span>
      <span class="act-time">${esc(a.when)}</span></li>`).join('');
}

function renderAll() { renderTabs(); renderCards(); renderReview(); renderActivity(); }

// ---- events -----------------------------------------------------------------------
document.addEventListener('click', (e) => {
  const pick = e.target.closest('[data-pick]');
  if (pick) { state.sel = Number(pick.dataset.pick); renderCards(); renderReview(); return; }
  const tab = e.target.closest('[data-tab]');
  if (tab) { state.tab = tab.dataset.tab; renderTabs(); }
});
$('btn-approve').addEventListener('click', () => { state.done[state.sel] = 'approved'; renderReview(); });
$('btn-reject').addEventListener('click', () => { state.done[state.sel] = 'rejected'; renderReview(); });

renderAll();
