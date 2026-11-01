/* graph.js — SVG rendering of a DFA with state highlighting. */
const Graph = (() => {
  const NS = 'http://www.w3.org/2000/svg', R = 30;
  const el = (tag, attrs = {}, text) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (text !== undefined) n.textContent = text; return n; };

  /** BFS-layered layout: column = distance from start, rows spread vertically. */
  function layout(m) {
    const layer = { [m.start]: 0 }, q = [m.start];
    for (let i = 0; i < q.length; i++) for (const a of m.alphabet) { const t = m.delta[q[i]][a]; if (!(t in layer)) { layer[t] = layer[q[i]] + 1; q.push(t); } }
    const extra = Math.max(...Object.values(layer)) + 1;
    m.states.forEach(s => { if (!(s in layer)) layer[s] = extra; });
    const cols = {}; m.states.forEach(s => (cols[layer[s]] = cols[layer[s]] || []).push(s));
    const maxN = Math.max(...Object.values(cols).map(c => c.length)), pos = {};
    for (const l in cols) cols[l].forEach((s, i) => pos[s] = { x: 110 + l * 240, y: 100 + i * 140 + (maxN - cols[l].length) * 70 });
    return { pos, layer };
  }

  function draw(svg, m) {
    svg.innerHTML = '';
    const { pos, layer } = layout(m), nodes = {};
    svg.appendChild(el('defs')).innerHTML = '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#475569"/></marker>';
    const g = svg.appendChild(el('g'));
    // group parallel edges so "0,1" share one arrow
    const edges = {};
    for (const s of m.states) for (const a of m.alphabet) { const t = m.delta[s][a], k = s + '\u0000' + t; (edges[k] = edges[k] || { s, t, l: [] }).l.push(a); }
    for (const e of Object.values(edges)) {
      const P = pos[e.s], Q = pos[e.t], txt = e.l.join(',');
      if (e.s === e.t) {
        g.appendChild(el('path', { d: `M${P.x - 12} ${P.y - R + 3} C${P.x - 40} ${P.y - R - 50} ${P.x + 40} ${P.y - R - 50} ${P.x + 12} ${P.y - R + 3}`, class: 'edge', 'marker-end': 'url(#ah)' }));
        g.appendChild(el('text', { x: P.x, y: P.y - R - 38, class: 'elabel' }, txt)); continue;
      }
      const dx = Q.x - P.x, dy = Q.y - P.y, len = Math.hypot(dx, dy), nx = -dy / len, ny = dx / len;
      const rev = edges[e.t + '\u0000' + e.s];
      const dl = Math.abs(layer[e.s] - layer[e.t]), curv = dl === 0 ? 60 : Math.max(rev ? 42 : 0, dl > 1 ? 50 + 35 * (dl - 2) : 0), side = curv || 12;
      const C = { x: (P.x + Q.x) / 2 + nx * curv * 2, y: (P.y + Q.y) / 2 + ny * curv * 2 };
      const cut = (A, B, r) => { const d = Math.hypot(B.x - A.x, B.y - A.y); return { x: A.x + (B.x - A.x) * r / d, y: A.y + (B.y - A.y) * r / d }; };
      const S = cut(P, C, R), E = cut(Q, C, R + 4);
      g.appendChild(el('path', { d: `M${S.x} ${S.y} Q${C.x} ${C.y} ${E.x} ${E.y}`, class: 'edge', 'marker-end': 'url(#ah)' }));
      g.appendChild(el('text', { x: .25 * S.x + .5 * C.x + .25 * E.x + nx * Math.sign(side) * 10, y: .25 * S.y + .5 * C.y + .25 * E.y + ny * Math.sign(side) * 10 + 4, class: 'elabel' }, txt));
    }
    for (const s of m.states) {
      const { x, y } = pos[s], n = g.appendChild(el('g', { class: 'node' + (m.accept.includes(s) ? ' acc' : '') + (s === m.start ? ' start' : '') }));
      n.appendChild(el('circle', { cx: x, cy: y, r: R }));
      if (m.accept.includes(s)) n.appendChild(el('circle', { cx: x, cy: y, r: R - 5, class: 'inner' }));
      n.appendChild(el('text', { x, y: y + 4, class: 'nlabel', 'font-size': s.length > 9 ? 9 : 12 }, s));
      if (s === m.start) g.appendChild(el('path', { d: `M${x - R - 36} ${y} L${x - R - 2} ${y}`, class: 'edge start-arrow', 'marker-end': 'url(#ah)' }));
      nodes[s] = n;
    }
    // fixed default size: 1 SVG unit = 1 px, so the graph is readable; wide graphs scroll inside the card
    const bb = g.getBBox(), pad = 30, w = bb.width + 2 * pad, h = bb.height + 2 * pad;
    svg.setAttribute('viewBox', [bb.x - pad, bb.y - pad, w, h].join(' '));
    svg.style.width = w + 'px'; svg.style.height = Math.max(h, 220) + 'px';
    return { highlight(list, cls = 'hl') { Object.values(nodes).forEach(n => n.classList.remove('hl', 'cur')); list.forEach(s => nodes[s] && nodes[s].classList.add(cls)); } };
  }
  return { draw };
})();
