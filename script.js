/* script.js — browser UI only (editors, drawing, animation). All DFA logic lives in dfa_logic.py via /api/*. */
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
const fmt = a => '{' + a.map(esc).join(', ') + '}';
const clone = o => JSON.parse(JSON.stringify(o));
const post = (url, body) => fetch(url, { method: 'POST', body: JSON.stringify(body) }).then(r => r.json());
const OPINFO = {
  union: ['A ∪ B', 'Accepted if A or B accepts. Product construction, accept when qA ∈ F_A OR qB ∈ F_B.'],
  intersection: ['A ∩ B', 'Accepted only if both accept. Product construction, accept when qA ∈ F_A AND qB ∈ F_B.'],
  complement: ['A̅', 'Accepted if A rejects (relative to Σ*). Same DFA with accepting states swapped. Only Machine A is used.'],
  difference: ['A − B', 'Accepted if A accepts and B rejects. Product construction, accept when qA ∈ F_A AND qB ∉ F_B.'],
};
const emptyM = () => ({ states: [], alphabet: ['0', '1'], start: '', accept: [], delta: {} });
let EXAMPLES = [], edA, edB, op = 'union', res = null, parts = null, graph = null, gIn = {}, timer = null, seq = 0, abTexts = null, abSeq = 0;
const eps = s => s === '' ? 'ε' : s;
/* strings over Σ in length-then-alphabet order: ε, a, b, aa, ab, … */
function samples(alpha, n) { const out = [''], q = ['']; while (out.length < n && q.length) { const w = q.shift(); if (w.length >= 4) break; for (const a of alpha) { q.push(w + a); out.push(w + a); } } return out.slice(0, n); }

/* ---------- DFA editor: only edits the machine data; accepting states are exactly the ticked boxes ---------- */
function Editor(root, onChange, init, copyFrom) {
  let m = clone(init);
  const set = x => { m = x; render(); onChange(); };
  function render() {
    root.innerHTML = `<label>Alphabet Σ (comma-separated) <input class="alpha" value="${esc(m.alphabet.join(','))}" size="8"></label>
    <div class="scroll"><table class="t"><tr><th>Start</th><th>Final</th><th>State</th>${m.alphabet.map(a => `<th>on ${esc(a)}</th>`).join('')}<th></th></tr>
    ${m.states.map((s, i) => `<tr><td><input type="radio" name="${root.id}" class="start" data-i="${i}" ${m.start === s ? 'checked' : ''}></td>
      <td><input type="checkbox" class="acc" data-i="${i}" ${m.accept.includes(s) ? 'checked' : ''}></td>
      <td><input class="name" data-i="${i}" value="${esc(s)}" size="5"></td>
      ${m.alphabet.map(a => `<td><select class="tr" data-i="${i}" data-a="${esc(a)}"><option value="">(none)</option>${m.states.map(t => `<option ${(m.delta[s] || {})[a] === t ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></td>`).join('')}
      <td><button class="del" data-i="${i}" title="Remove state">×</button></td></tr>`).join('')}</table></div>
    <p class="muted">Final states: <b>${fmt(m.accept)}</b> · "(none)" = no transition (treated as a trap state)</p>
    <div class="row"><button class="add">+ State</button>
      <select class="ex"><option value="">Load example…</option>${EXAMPLES.map((e, i) => `<option value="${i}">${esc(e.name)}</option>`).join('')}</select>
      ${copyFrom ? '<button class="copy" title="Use the same alphabet as Machine A">Copy Σ from A</button>' : ''}
      <button class="reset">Reset</button></div>`;
  }
  root.addEventListener('change', ev => {
    const c = ev.target, i = +c.dataset.i, s = m.states[i];
    if (c.classList.contains('alpha')) { m.alphabet = [...new Set(c.value.split(',').map(x => x.trim()).filter(Boolean))]; render(); }
    else if (c.classList.contains('start')) m.start = s;
    else if (c.classList.contains('acc')) { m.accept = c.checked ? [...m.accept, s] : m.accept.filter(x => x !== s); render(); }
    else if (c.classList.contains('tr')) { m.delta[s] = m.delta[s] || {}; if (c.value) m.delta[s][c.dataset.a] = c.value; else delete m.delta[s][c.dataset.a]; }
    else if (c.classList.contains('name')) {                       // rename, updating every reference
      const n = c.value.trim();
      if (!n || (n !== s && m.states.includes(n))) { render(); return; }
      m.states[i] = n; if (m.start === s) m.start = n; m.accept = m.accept.map(x => x === s ? n : x);
      m.delta[n] = m.delta[s] || {}; if (n !== s) delete m.delta[s];
      for (const q in m.delta) for (const a in m.delta[q]) if (m.delta[q][a] === s) m.delta[q][a] = n;
      render();
    } else if (c.classList.contains('ex')) { if (c.value !== '') set(clone(EXAMPLES[+c.value].m)); return; }
    onChange();
  });
  root.addEventListener('click', ev => {
    const c = ev.target;
    if (c.classList.contains('add')) { let k = 0; while (m.states.includes('q' + k)) k++; m.states.push('q' + k); m.delta['q' + k] = {}; if (!m.start) m.start = 'q' + k; render(); onChange(); }
    else if (c.classList.contains('del')) {
      const s = m.states[+c.dataset.i]; m.states.splice(+c.dataset.i, 1); delete m.delta[s];
      m.accept = m.accept.filter(x => x !== s); if (m.start === s) m.start = '';
      for (const q in m.delta) for (const a in m.delta[q]) if (m.delta[q][a] === s) delete m.delta[q][a];
      render(); onChange();
    } else if (c.classList.contains('copy')) { m.alphabet = [...copyFrom()]; render(); onChange(); }
    else if (c.classList.contains('reset')) set(emptyM());
  });
  render();
  return { get: () => m };
}

/* ---------- navigation & operation selection ---------- */
function showTab(t) { history.replaceState(null, '', '#' + t);
  if (t === 'sim') setTimeout(drawAll);  /* SVG sizes are only measurable once the tab is visible */
  document.querySelectorAll('.tab').forEach(s => s.hidden = s.id !== t); document.querySelectorAll('nav button').forEach(b => b.classList.toggle('on', b.dataset.tab === t)); }
document.querySelectorAll('nav button').forEach(b => b.onclick = () => showTab(b.dataset.tab));
$('#start').onclick = () => showTab('sim');
for (const k in OPINFO) {
  $('#opcards').insertAdjacentHTML('beforeend', `<div class="card op" data-op="${k}"><h3>${OPINFO[k][0]}</h3><p>${OPINFO[k][1]}</p></div>`);
  $('#opsel').insertAdjacentHTML('beforeend', `<button data-op="${k}">${OPINFO[k][0]}</button>`);
}
function selectOp(k) {
  op = k; $('#opdesc').textContent = OPINFO[k][1]; $('#cardB').style.opacity = k === 'complement' ? .4 : 1;
  document.querySelectorAll('#opsel button').forEach(b => b.classList.toggle('on', b.dataset.op === k));
  rebuild();
}
document.querySelectorAll('#opcards .op').forEach(c => c.onclick = () => { showTab('sim'); selectOp(c.dataset.op); });
document.querySelectorAll('#opsel button').forEach(b => b.onclick = () => selectOp(b.dataset.op));

/* ---------- drawing: the two input machines (as edited, possibly incomplete) and the result ---------- */
function drawInputs() {
  if (!edA) return;
  gIn = { A: Graph.draw($('#svgA'), edA.get()), B: Graph.draw($('#svgB'), edB.get()) };
  $('#samplesAB').innerHTML = samples(edA.get().alphabet, 8).map(s => `<button class="chip">${esc(eps(s))}</button>`).join('');
}
function drawAll() { drawInputs(); if (res && !$('#result').hidden) graph = Graph.draw($('#svg'), res); }

/* ---------- build (Python does the work) ---------- */
async function rebuild() {
  clearTimeout(timer);                                             // stop any trace animation of the old machine
  drawInputs();
  const id = ++seq, r = await post('/api/build', { A: edA.get(), B: edB.get(), op });
  if (id !== seq) return;                                          // a newer request replaced this one
  $('#result').hidden = !!r.errors;
  $('#msg').innerHTML = r.errors ? '<div class="err"><b>Cannot construct yet:</b><ul>' + r.errors.map(e => `<li>${esc(e)}</li>`).join('') + '</ul></div>'
    : r.notes.map(n => `<div class="note">${esc(n)}</div>`).join('');
  if (r.errors) { refreshAB(); return; }
  $('#restitle').textContent = `Resulting DFA — ${op[0].toUpperCase() + op.slice(1)} (${OPINFO[op][0]})`;
  res = r.machine; parts = r.parts; graph = Graph.draw($('#svg'), res);
  const { pairs, accepted, rejected } = r.info;
  $('#stats').innerHTML = `<span>States: <b>${res.states.length}</b>${pairs ? ` <small>reachable, of ${pairs} = |Q<sub>A</sub>|·|Q<sub>B</sub>| possible pairs</small>` : ''}</span>
    <span>Accepting: <b>${res.accept.length}</b></span><span>Σ = <b>${fmt(res.alphabet)}</b></span><span>Start: <b>${esc(res.start)}</b></span>`;
  $('#lang').innerHTML = accepted === null ? '<div class="note"><b>L = ∅</b> — no string is accepted (no accepting state is reachable).</div>'
    : rejected === null ? '<div class="note"><b>L = Σ*</b> — every string is accepted (no rejecting state is reachable).</div>'
    : `<p class="muted">Shortest accepted: <button class="chip ok-chip">${esc(eps(accepted))}</button> · shortest rejected: <button class="chip err-chip">${esc(eps(rejected))}</button></p>`;
  $('#table').innerHTML = r.table_html;
  $('#samples').innerHTML = samples(res.alphabet, 10).map(s => `<button class="chip">${esc(eps(s))}</button>`).join('');
  $('#trace').innerHTML = '';
  refreshAB();
}
/* ---------- string testing: path computed by Python, animated here ---------- */
async function testString(str) {
  clearTimeout(timer); if (!res) return;
  const names = Object.keys(parts), out = $('#trace');
  const [r, ...pr] = await Promise.all([res, ...names.map(k => parts[k])].map(machine => post('/api/run', { machine, text: str })));
  if (r.error) { out.innerHTML = `<div class="err">${esc(r.error)}</div>`; return; }
  const mark = ok => `<span class="${ok ? 'okc' : 'errc'}">${ok ? '✓ accepts' : '✗ rejects'}</span>`;
  const why = names.map((k, i) => `${k}: ${mark(pr[i].accepted)}`).join(' · ') + ` → ${OPINFO[op][0]}: ${mark(r.accepted)}`;
  const rows = [`Start → <b>${esc(res.start)}</b>`, ...r.syms.map((c, i) => `Read <code>${esc(c)}</code> → <b>${esc(r.path[i + 1])}</b>`)];
  out.innerHTML = `<p class="muted">Input: ${r.syms.length ? esc(str) : 'ε (empty string)'}</p><ol class="trace" start="0"></ol><div id="verdict"></div>`;
  let i = 0;
  (function tick() {
    $('.trace').insertAdjacentHTML('beforeend', `<li>${rows[i]}</li>`); graph.highlight([r.path[i]], 'cur');
    for (const k in gIn) gIn[k].highlight(names.includes(k) ? [pr[names.indexOf(k)].path[i]] : [], 'cur');
    if (++i < rows.length) { timer = setTimeout(tick, 450); return; }
    $('#verdict').innerHTML = `<div class="${r.accepted ? 'ok' : 'err'}"><b>${r.accepted ? 'ACCEPTED' : 'REJECTED'}</b> — final state ${esc(r.path[r.path.length - 1])} is ${r.accepted ? '' : 'not '}in the accepting set ${fmt(res.accept)}.</div>
      <p class="why">${why}</p>`;
  })();
}
$('#run').onclick = () => testString($('#str').value.trim());
$('#str').onkeydown = e => { if (e.key === 'Enter') $('#run').click(); };
const chipRun = e => { if (e.target.classList.contains('chip')) { const t = e.target.textContent === 'ε' ? '' : e.target.textContent; $('#str').value = t; testString(t); } };
$('#samples').onclick = chipRun; $('#lang').onclick = chipRun;
/* ---------- strings tested on the input machines A and B (independent of the operation) ---------- */
const toks = v => { const t = v.split(/[\s,]+/).filter(Boolean).map(x => x === 'ε' ? '' : x); return t.length ? t : ['']; };
const verdict = ok => `<span class="${ok ? 'okc' : 'errc'}">${ok ? '✓ accepts' : '✗ rejects'}</span>`;
function refreshAB() { if (abTexts) testInputs(abTexts); }          // keep the table in sync after any edit
async function testInputs(texts) {
  abTexts = texts; const id = ++abSeq;
  const r = await post('/api/test_inputs', { A: edA.get(), B: edB.get(), texts });
  const withOp = res && !$('#result').hidden;                       // add a column for the operation result when it exists
  const rr = withOp ? await Promise.all(texts.map(t => post('/api/run', { machine: res, text: t }))) : null;
  if (id !== abSeq) return;
  const cell = (side, i) => {
    if (r[side].errors) return '<td class="muted">—</td>';
    const x = r[side].results[i];
    return x.error ? `<td class="errc">${esc(x.error)}</td>` : `<td>${verdict(x.accepted)}<div class="path">${x.path.map(esc).join(' → ')}</div></td>`;
  };
  const errs = ['A', 'B'].flatMap(k => r[k].errors || []), dead = ['A', 'B'].filter(k => r[k].dead).map(k => `Machine ${k}: missing transitions go to trap state '${esc(r[k].dead)}'`);
  const count = k => r[k].errors ? '' : `<span>${k} accepts <b>${r[k].results.filter(x => x.accepted).length}</b> of ${texts.length}</span>`;
  $('#traceAB').innerHTML = (errs.length ? `<div class="err"><ul>${errs.map(e => `<li>${esc(e)}</li>`).join('')}</ul></div>` : '')
    + `<table class="t" style="margin-top:10px"><tr><th>String</th><th>Machine A</th><th>Machine B</th>${withOp ? `<th>${esc(OPINFO[op][0])} result</th>` : ''}</tr>`
    + texts.map((t, i) => `<tr><td><code>${esc(eps(t))}</code></td>${cell('A', i)}${cell('B', i)}${withOp ? (rr[i].error ? '<td class="muted">—</td>' : `<td>${verdict(rr[i].accepted)}</td>`) : ''}</tr>`).join('') + '</table>'
    + `<div class="stats" style="margin-top:8px">${count('A')}${count('B')}</div>` + (dead.length ? `<p class="muted">${dead.join(' · ')}</p>` : '');
}
$('#runAB').onclick = () => testInputs(toks($('#strAB').value.trim()));
$('#strAB').onkeydown = e => { if (e.key === 'Enter') $('#runAB').click(); };
$('#samplesAB').onclick = e => { if (e.target.classList.contains('chip')) { const cur = $('#strAB').value.trim(); $('#strAB').value = cur ? cur + ' ' + e.target.textContent : e.target.textContent; $('#runAB').click(); } };
/* ---------- start-up ---------- */
showTab(['home', 'sim', 'theory'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'home');
fetch('/api/examples').then(r => r.json()).then(ex => {
  EXAMPLES = ex; edA = Editor($('#edA'), rebuild, ex[0].m); edB = Editor($('#edB'), rebuild, ex[1].m, () => edA.get().alphabet); selectOp('union');
}).catch(() => document.body.insertAdjacentHTML('afterbegin', '<div class="err" style="margin:16px">Python server not reachable. Start it with <code>python app.py</code> and open the address it prints</div>'));
