/* Ophanim console. Same data and wording as the classic console (brain/console/index.html), new layout:
   force-directed graph (left) | numbered info panels (right), draggable + keyboard-resizable split,
   status bar with connection state, "updated Ns ago" and an audit-log ticker. Polls every 2 s. */
(function () {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const A = window.anime;
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch { } } };

  /* ---------------- clock ---------------- */
  const clock = $('clock');
  const tickClock = () => { const d = new Date(); clock.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }); clock.dateTime = d.toISOString(); };
  tickClock(); setInterval(tickClock, 1000);

  /* ---------------- graph ---------------- */
  const INK = '#060606', PAPER = '#F8F8F8', LIME = '#D7F15B', RED = '#D92D20', VIOLET = '#7A3FE0';
  const cy = cytoscape({
    container: $('cy'), minZoom: 0.3, maxZoom: 2.5,
    style: [
      { selector: 'node', style: { label: 'data(label)', 'font-family': 'JetBrains Mono, monospace', 'font-size': 14, 'font-weight': 700, color: INK,
          'text-valign': 'center', 'text-halign': 'center', 'text-wrap': 'wrap', 'text-max-width': 112,
          shape: 'rectangle', width: 132, height: 48, 'background-color': PAPER, 'border-width': 1.5, 'border-color': INK } },
      { selector: 'node[kind="jewel"]', style: { shape: 'hexagon', width: 132, height: 78, 'background-color': LIME, 'border-width': 2 } },
      { selector: 'node[kind="attacker"]', style: { shape: 'diamond', width: 70, height: 70, 'background-color': RED, 'border-width': 2,
          'text-valign': 'bottom', 'text-margin-y': 8, 'font-size': 14 } },
      { selector: 'node.hot', style: { 'border-color': RED, 'border-width': 3.5 } },
      { selector: 'edge', style: { width: 2, 'line-color': INK, 'target-arrow-color': INK, 'target-arrow-shape': 'triangle', 'arrow-scale': 1.2,
          'curve-style': 'bezier', label: 'data(ease)', 'font-family': 'JetBrains Mono, monospace', 'font-size': 12, 'font-weight': 700, color: INK,
          'text-background-color': PAPER, 'text-background-opacity': 1, 'text-background-padding': 3,
          'text-border-width': 1, 'text-border-color': INK, 'text-border-opacity': 1 } },
      { selector: 'edge[!verified]', style: { 'line-style': 'dashed', 'line-dash-pattern': [7, 5] } },
      { selector: 'edge[?live]', style: { width: 5, 'line-color': RED, 'target-arrow-color': RED, color: RED, 'text-border-color': RED, 'z-index': 10,
          'underlay-color': RED, 'underlay-padding': 6, 'underlay-opacity': 0.12 } },
      { selector: '.faded', style: { opacity: 0.22 } },
      { selector: 'edge.hi', style: { width: 4.5, 'line-color': VIOLET, 'target-arrow-color': VIOLET, 'z-index': 9 } },
      { selector: 'node.hi', style: { 'border-color': VIOLET, 'border-width': 3.5 } },
      { selector: '.picked', style: { 'overlay-color': VIOLET, 'overlay-opacity': 0.14, 'overlay-padding': 8 } },
    ],
  });

  // fixed left-to-right layout, the same on every load: column = steps from the attacker (jewels last),
  // each node sits level with the boxes that lead to it, at least ROW apart, so boxes and labels never overlap
  const COL = 260, ROW = 130;
  function positions() {
    const ids = cy.nodes().map(n => n.id()), parents = {}, depth = { attacker: 0 }, q = ['attacker'];
    cy.edges().forEach(e => (parents[e.target().id()] = parents[e.target().id()] || []).push(e.source().id()));
    while (q.length) { const n = q.shift(); cy.getElementById(n).outgoers('node').forEach(t => { if (depth[t.id()] === undefined) { depth[t.id()] = depth[n] + 1; q.push(t.id()); } }); }
    const last = Math.max(1, ...ids.filter(id => cy.getElementById(id).data('kind') !== 'jewel').map(id => depth[id] ?? 1)) + 1;
    const cols = {};
    ids.forEach(id => { const d = cy.getElementById(id).data('kind') === 'jewel' ? last : (depth[id] ?? 1); (cols[d] = cols[d] || []).push(id); });
    const pos = {};
    Object.keys(cols).map(Number).sort((a, b) => a - b).forEach(d => {
      const list = cols[d];
      const want = id => { const ps = (parents[id] || []).filter(p => pos[p]); return ps.length ? ps.reduce((s, p) => s + pos[p].y, 0) / ps.length : null; };
      const w = {}; list.forEach((id, i) => { w[id] = d <= 1 || want(id) === null ? (i - (list.length - 1) / 2) * ROW : want(id); });
      list.sort((a, b) => w[a] - w[b]);
      const y = []; list.forEach((id, i) => { y[i] = i ? Math.max(w[id], y[i - 1] + ROW) : w[id]; });
      const shift = list.reduce((s, id) => s + w[id], 0) / list.length - y.reduce((s, v) => s + v, 0) / list.length;
      list.forEach((id, i) => { pos[id] = { x: d * COL, y: y[i] + shift }; });
    });
    return pos;
  }
  // fit the whole graph, but never blow it up past 1.4x on a big screen
  function fitView() {
    cy.fit(undefined, 50);
    if (cy.zoom() > 1.4) { cy.zoom(1.4); cy.center(); }
  }
  // first load: place at once; Reset layout button: slide dragged boxes back so the click visibly does something
  function layout(animate) {
    const pos = positions();
    if (animate !== true || reduce) {
      cy.nodes().positions(n => pos[n.id()]);
      fitView();
      return;
    }
    cy.layout({ name: 'preset', positions: n => pos[n.id()], fit: true, padding: 50,
      animate: true, animationDuration: 400, animationEasing: 'ease-out', stop: fitView }).run();
  }

  const NICE = { no_2sv: 'no 2-step login', live_attack: 'live attack', public_link_live: 'public link (live)' };
  const nice = f => NICE[f] || f.replace(/_/g, ' ');
  const label = id => cy.getElementById(id).data('label') || id;
  const edgeLine = e => `${esc(label(e.data('source')))} → ${esc(label(e.data('target')))}: ` +
    Object.entries(e.data('factors') || {}).map(([f, v]) => `${esc(nice(f))} ${esc(v)}`).join(' × ') +
    ` = <b>${esc(e.data('ease'))}</b>${e.data('live') ? ' <span class="chip red">LIVE</span>' : ''}${e.data('verified') ? '' : ' <span class="muted">(not verified)</span>'}`;

  let picked = null;   // clicked node/edge id, kept across refreshes
  function showDetail() {
    cy.elements().removeClass('picked');
    const el = picked && cy.getElementById(picked);
    const box = $('detail');
    if (!el || el.empty()) { box.innerHTML = '<p class="hint">Click a box or an arrow to see why it is risky.</p>'; return; }
    el.addClass('picked');
    const edges = el.isEdge() ? el : el.connectedEdges();
    box.innerHTML = `<h3>${el.isEdge() ? 'Step' : esc(label(picked))}</h3>` + edges.map(e => `<div class="row">${edgeLine(e)}</div>`).join('');
  }
  cy.on('tap', 'node, edge', ev => { picked = ev.target.id(); showDetail(); });
  cy.on('tap', ev => { if (ev.target === cy) { picked = null; showDetail(); } });

  $('zin').onclick = () => cy.zoom({ level: cy.zoom() * 1.2, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  $('zout').onclick = () => cy.zoom({ level: cy.zoom() / 1.2, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  $('fit').onclick = fitView;
  $('relayout').onclick = () => layout(true);
  // the graph box changes size on window resize, maximise, browser zoom and divider drags: follow all of them
  let fitRaf = 0;
  new ResizeObserver(() => { cancelAnimationFrame(fitRaf); fitRaf = requestAnimationFrame(() => { cy.resize(); fitView(); }); }).observe($('cy'));

  // live edges: slow underlay pulse (not a flash), only while an attack is live
  let pulseOn = false;
  function pulse(t) {
    const live = cy.edges('[?live]');
    if (!live.length || reduce) { pulseOn = false; return; }
    live.style('underlay-opacity', 0.08 + 0.14 * (0.5 + 0.5 * Math.sin(t / 420)));
    requestAnimationFrame(pulse);
  }

  let nodeKey = '';
  function updateGraph(g) {
    const key = g.nodes.map(n => n.data.id).sort().join(',');
    if (key !== nodeKey) {           // first load or nodes changed: rebuild + force layout
      nodeKey = key;
      cy.elements().remove();
      cy.add([...g.nodes, ...g.edges]);
      layout();
    } else {                         // same nodes: update edges in place, keep positions and zoom
      const ids = new Set(g.edges.map(e => e.data.id));
      cy.edges().forEach(e => { if (!ids.has(e.id())) e.remove(); });
      g.edges.forEach(e => { const el = cy.getElementById(e.data.id); el.nonempty() ? el.data(e.data) : cy.add(e); });
      g.nodes.forEach(n => cy.getElementById(n.data.id).data(n.data));
    }
    const live = cy.edges('[?live]');
    cy.nodes().removeClass('hot'); live.connectedNodes().addClass('hot');
    $('g-count').textContent = `${g.nodes.length} nodes · ${g.edges.length} steps`;
    $('live-chip').hidden = !live.length;
    window.OphanimMark && OphanimMark.setAlert(!!live.length);
    if (live.length && !pulseOn) { pulseOn = true; requestAnimationFrame(pulse); }
    return live.length;
  }

  /* ---------------- risk / fix / paths ---------------- */
  let shownRisk = null;
  function setRisk(v, hot) {
    const el = $('risk');
    el.classList.toggle('hot', hot);
    if (shownRisk === null || !A || reduce) { el.textContent = v; shownRisk = v; return; }
    if (v === shownRisk) return;
    const o = { v: +shownRisk }; shownRisk = v;
    A.animate(o, { v: +v, duration: 900, ease: 'outExpo', onUpdate: () => { el.textContent = o.v.toFixed(2).replace(/\.?0+$/, ''); }, onComplete: () => { el.textContent = v; } });
  }
  function highlightPath(p) {
    cy.elements().removeClass('hi faded');
    if (!p) return;
    const nodes = cy.collection(p.path.map(id => cy.getElementById(id)));
    let edges = cy.collection();
    for (let i = 0; i < p.path.length - 1; i++) edges = edges.union(cy.getElementById(`${p.path[i]}-${p.path[i + 1]}`));
    cy.elements().not(nodes).not(edges).addClass('faded');
    nodes.addClass('hi'); edges.addClass('hi');
  }
  let lastPaths = [];
  function renderPaths(ps) {
    lastPaths = ps;
    $('paths').innerHTML = ps.length ? ps.map((p, i) => `<li tabindex="0" data-i="${i}" class="${i === 0 ? 'top' : ''}">
      <span class="pn">${String(i + 1).padStart(2, '0')}</span><span>${esc(p.sentence)}</span><span class="pr" title="risk">${esc(p.risk)}</span></li>`).join('')
      : '<li class="empty-li"><p class="empty">No open paths.</p></li>';
  }
  const pathsEl = $('paths');
  ['mouseover', 'focusin'].forEach(t => pathsEl.addEventListener(t, e => { const li = e.target.closest('li[data-i]'); if (li) highlightPath(lastPaths[+li.dataset.i]); }));
  ['mouseleave', 'focusout'].forEach(t => pathsEl.addEventListener(t, () => highlightPath(null)));

  /* ---------------- incidents ---------------- */
  let MITRE = null;   // signal type -> technique, loaded once when Expert view is first switched on
  const sevChip = s => `<span class="chip ${s === 'critical' ? 'red' : s === 'high' ? 'lime' : ''}">${esc(s)}</span>`;
  function renderIncidents(incs, expert) {
    const list = incs.slice().reverse();
    $('incs').innerHTML = list.length ? list.map(i => `<article class="inc ${esc(i.severity)}">
      <div class="inc-head"><span class="inc-id">#${esc(i.id)}</span><h3>${esc(i.title)}</h3></div>
      <div class="inc-meta">${sevChip(i.severity)}<span class="chip ink">${esc(i.status)}</span><span class="chip">policy ${esc(i.policy)}</span></div>
      <div class="inc-sec"><span class="lbl">Signals</span><div class="sig">${(i.signals || []).map(s => `<span class="chip"><b>${esc(s.type)}</b>${s.score ? ` · score ${esc(s.score.score)}: ${esc((s.score.markers || []).join(', '))}` : ''}</span>`).join('<span class="arrow">→</span>')}</div></div>
      <div class="inc-sec"><span class="lbl">Runbook</span><ol class="runbook">${(i.runbook || []).map(s => `<li class="${(i.done || []).includes(s) ? 'done' : ''}">${esc(s)}</li>`).join('')}</ol></div>
      ${expert ? `<div class="expert-row"><span class="lbl">MITRE ATT&amp;CK</span> ${esc([...new Set((i.signals || []).map(s => MITRE && MITRE[s.type]).filter(Boolean))].join('; ') || '-')}
        · <a href="/incidents/${encodeURIComponent(i.id)}/report" target="_blank" rel="noopener">report + audit trail ↗</a></div>` : ''}
    </article>`).join('') : '<p class="empty">No incidents yet. Everything is quiet.</p>';
  }

  /* ---------------- ticker (audit log) ---------------- */
  let tickerTop = -1;
  function summary(b) {
    switch (b.kind) {
      case 'event': return `${b.type || ''} · ${b.entity || ''}`;
      case 'incident': return `incident #${b.id} ${b.severity || ''}${b.merged ? ' (merged)' : ''}`;
      case 'notify': return `alert sent for #${b.incident_id}${b.reminder ? ' (reminder ' + b.reminder + ')' : ''}`;
      default: return Object.entries(b).filter(([k]) => k !== 'kind').slice(0, 3).map(([k, v]) => `${k} ${typeof v === 'object' ? '…' : v}`).join(' · ');
    }
  }
  function renderTicker(rows) {
    if (!rows.length || rows[0].id === tickerTop) return;
    tickerTop = rows[0].id;
    const items = rows.slice(0, 20).map(r => `<span><b>#${esc(r.id)} ${esc(r.body.kind)}</b>${esc(summary(r.body))} · ${esc(r.hash)}</span>`).join('');
    $('ticker').innerHTML = items + items.replace(/<span>/g, '<span aria-hidden="true">');
  }
  const status = document.querySelector('.status'), tt = $('tick-toggle');
  tt.onclick = () => { const p = status.classList.toggle('paused'); tt.setAttribute('aria-pressed', p); tt.textContent = p ? '▶' : '❚❚'; tt.setAttribute('aria-label', p ? 'Play the event ticker' : 'Pause the event ticker'); };

  /* ---------------- poll ---------------- */
  let lastOk = 0;
  const get = u => fetch(u, { cache: 'no-store' }).then(r => { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); });
  async function tick() {
    try {
      const expert = $('expert').checked;
      const [g, paths, a, incs, audit] = await Promise.all([get('/graph'), get('/paths'), get('/audit/verify'), get('/incidents'), get('/audit').catch(() => null)]);
      if (expert && !MITRE) MITRE = await get('/mitre').catch(() => ({}));
      const liveN = updateGraph(g);
      setRisk(g.risk, liveN > 0);
      $('open').textContent = g.open_paths;
      // During a live attack the prevention fix is the wrong first step: the alert's buttons stop the attack
      const impact = g.one_fix ? `<span class="chip lime">closes ${esc(g.one_fix.paths_closed)} paths</span><span class="chip">risk -${esc(g.one_fix.risk_drop)}</span>` : '';
      $('fix-block').classList.toggle('urgent', liveN > 0);
      if (liveN > 0) {
        $('fix').textContent = 'Follow the steps in the alert first';
        $('fix-impact').innerHTML = `<span class="chip red">live attack</span>` +
          (g.one_fix ? `<span class="after">After that: ${esc(g.one_fix.text)}</span>` : '');
      } else {
        $('fix').textContent = g.one_fix ? g.one_fix.text : 'No fix needed';
        $('fix-impact').innerHTML = impact;
      }
      showDetail();
      renderPaths(paths.filter(p => p.open).slice(0, 3));
      $('audit').innerHTML = a.ok ? '<span class="ok">verified</span>' : `<span class="bad">BROKEN at row ${esc(a.broken_at)}</span>`;
      const chip = $('audit-chip'); chip.textContent = a.ok ? 'Audit verified' : `Audit BROKEN @ row ${a.broken_at}`; chip.className = 'chip ' + (a.ok ? 'lime' : 'red');
      renderIncidents(incs, expert);
      if (audit) renderTicker(audit.rows || []);
      lastOk = Date.now();
      $('conn').classList.remove('down'); $('conn-t').textContent = 'Brain connected';
    } catch (e) {
      $('conn').classList.add('down'); $('conn-t').textContent = 'Brain unreachable';
    }
  }
  setInterval(() => { $('updated').textContent = lastOk ? `Updated ${Math.round((Date.now() - lastOk) / 1000)}s ago` : 'Waiting for data'; }, 1000);
  $('expert').addEventListener('change', tick);
  tick(); setInterval(tick, 2000);

  /* ---------------- resizable split (pointer + keyboard) ---------------- */
  const split = $('split'), div = $('divider');
  function setLeft(pct, save) {
    pct = Math.max(30, Math.min(80, pct));
    split.style.setProperty('--left', pct + '%');
    div.setAttribute('aria-valuenow', Math.round(pct));
    if (save) store.set('ophanim.split', String(pct));
  }
  const saved = parseFloat(store.get('ophanim.split'));
  if (saved) setLeft(saved);
  div.addEventListener('pointerdown', e => {
    div.setPointerCapture(e.pointerId); div.classList.add('drag');
    const move = ev => { if (!ev.buttons) return up(); const r = split.getBoundingClientRect(); setLeft(((ev.clientX - r.left) / r.width) * 100); };
    // end the drag however it ends (button released, capture lost, pointer cancelled), or the split keeps following the mouse
    const up = () => { div.classList.remove('drag');
      ['pointermove', 'pointerup', 'pointercancel', 'lostpointercapture'].forEach(t => div.removeEventListener(t, t === 'pointermove' ? move : up));
      setLeft(parseFloat(split.style.getPropertyValue('--left')), true); };
    div.addEventListener('pointermove', move);
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(t => div.addEventListener(t, up));
  });
  div.addEventListener('dblclick', () => setLeft(60, true));
  div.addEventListener('keydown', e => {
    const cur = parseFloat(split.style.getPropertyValue('--left')) || 60, step = e.shiftKey ? 10 : 2;
    const map = { ArrowLeft: cur - step, ArrowRight: cur + step, Home: 30, End: 80, Enter: 60 };
    if (e.key in map) { e.preventDefault(); setLeft(map[e.key], true); }
  });
})();
