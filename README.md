# Regular Language Closure Operations Simulator

CSET302 (Automata Theory and Computability), Topic 15. A local web app where you define two DFAs (Machine A and Machine B), pick a closure operation (∪, ∩, complement, −), and see the resulting DFA built with the textbook construction, drawn as a graph and a transition table. You can then run strings on it step by step.

**Run:** `python app.py` (Python 3, nothing to install). It opens http://127.0.0.1:8000, or the next free port up to 8009.
**Test:** `python test_dfa.py`

## Features

| Feature | Where |
|---|---|
| DFA editor: alphabet, states, start, final states, transition dropdowns, rename/delete, examples, "Copy Σ from A" | `script.js` (`Editor`) |
| Validation with readable errors (empty Σ, multi-char symbols, no start, unknown targets, `(` `)` `,` in names, differing Σ) | `dfa_logic.validate`, `build` |
| Completion of missing transitions with a non-accepting trap state (with a note shown to the user) | `dfa_logic.complete` |
| Union / intersection / difference by the product construction over reachable pairs (BFS) | `dfa_logic.product` |
| Complement by swapping the final states of the completed DFA | `dfa_logic.complement` |
| Language facts: shortest accepted and rejected strings, L = ∅ and L = Σ* detection, reachable vs. \|Q_A\|·\|Q_B\| pairs | `dfa_logic.shortest`, `build` → `info` |
| SVG drawing (BFS layered layout, merged parallel edges, self-loops, start arrow, double circles) | `graph.js` |
| Live diagrams of Machine A and Machine B under their editors, drawn as edited (missing transitions omitted, works before the machine is valid) | `script.js` (`drawInputs`), `graph.js` |
| String test: animated state-by-state trace highlighted on the result **and** on A's and B's diagrams, verdict, and the verdicts of A and B | `script.js` (`testString`) |
| Sample strings generated from the result's Σ (ε, a, b, aa, …) | `script.js` (`samples`) |
| Light/dark theme (follows the OS), tabs reachable by URL hash (`#home`, `#sim`, `#theory`) | `style.css`, `script.js` |

## Architecture

```
 Browser (index.html + style.css)
   script.js  ── UI, editors, animation ──┐   fetch JSON
   graph.js   ── SVG drawing only         │
                                          ▼
 app.py  (http.server, stdlib)  GET static files, GET /api/examples, POST /api/build, POST /api/run
                                          │  plain function calls
                                          ▼
 dfa_logic.py  ── all automata logic (pure Python, no libraries)
```

The browser never computes automata. It sends the machines as JSON, and Python validates, completes, constructs and runs them. `test_dfa.py` tests `dfa_logic.py` directly.

## Project structure

```
.
├── README.md          this file
├── .gitignore         ignores __pycache__, *.pyc, .DS_Store, Word lock files
├── app.py             tiny stdlib HTTP server + JSON API; picks a free port 8000-8009
├── dfa_logic.py       validation, completion, product, complement, shortest(), run(), examples
├── test_dfa.py        unittest: every operation checked against its set definition on all short strings
├── index.html         page skeleton: Home / Simulator / Theory tabs
├── script.js          editors, operation picker, build/run calls, stats, trace animation
├── graph.js           Graph.draw(svg, machine) → { highlight(states, cls) }
├── style.css          design tokens (light + dark) and all styles
└── CSET302 Milestone 1 – Regular Language Closure Operations Simulator.docx   design-review report
```

## Layer breakdown

**dfa_logic.py**

| Name | Responsibility |
|---|---|
| `OPS` | op name → (symbol, accepting rule on (A accepts, B accepts), rule text) |
| `label(p, q)` | product state name `"(p, q)"` |
| `validate(m, name)` | list of error strings; missing transitions are *not* errors |
| `complete(m)` | adds trap state `dead` (or `dead'`, …) for missing transitions → `(machine, dead_name or None)` |
| `product(A, B, op)` | BFS product construction over reachable pairs only |
| `complement(A)` | same DFA, final states become Q − F |
| `shortest(m, accepted)` | BFS for the shortest accepted/rejected string; `None` = none exists |
| `table_html(m)` | escaped HTML transition table (→ start, * accepting) |
| `build(A, B, op)` | main entry: validate → complete → construct → info |
| `run(m, text)` | runs a string on a complete DFA; `""` or `"ε"` = empty string |
| `EXAMPLES` | four example DFAs over {0,1} |

**app.py**: `Handler.do_GET` serves the files listed in `FILES` and `/api/examples`. `do_POST` handles `/api/build` and `/api/run`. A malformed request gets a JSON error back, and the connection is not dropped.

**script.js**

| Name | Responsibility |
|---|---|
| `Editor(root, onChange, init, copyFrom?)` | renders and edits one machine; `copyFrom` adds the "Copy Σ from A" button (used by B) |
| `showTab`, `selectOp` | navigation (with URL hash; showing the Simulator redraws all graphs, since hidden SVGs can't be measured) and operation selection |
| `drawInputs()`, `drawAll()` | draw A and B from the editors (`#svgA`, `#svgB`); `drawAll` also redraws the result |
| `rebuild()` | stops any running trace, redraws A and B, POSTs `/api/build`, draws graph, stats, language facts, table, samples |
| `testString(str)` | runs the string on the result and on each completed input machine, animates the path on all diagrams, shows the verdict |
| `samples(alpha, n)` | first `n` strings over Σ in length-then-alphabet order |

**graph.js**: `layout` puts states in columns by BFS distance from the start state; states it can't reach go in a last column. `draw` renders edges first and then nodes, sizes the SVG to its content, and returns `highlight`. It accepts incomplete machines (missing or unknown transitions and a missing start state are skipped) and gives each SVG its own arrowhead marker id (`ah-<svg id>`). During a trace, a trap state that was added by completion is not in the drawing of A or B, so nothing is highlighted there while the run is in it.

## App flow

1. Start-up: `GET /api/examples` loads the examples. Machine A starts as "Ends in 0", Machine B as "Even number of 1s", and the operation is union.
2. Any change in an editor or the operation picker calls `rebuild()`, which redraws A's and B's diagrams immediately. A sequence counter throws away responses that arrive out of order.
3. `POST /api/build` returns `{errors}` (the result panel is hidden and the errors are listed) or a result object (see below).
4. Clicking Test, a sample chip or a shortest-string chip sends one `POST /api/run` for the result and one for each completed input machine. The page then animates the path on the result graph and on A's and B's diagrams and shows the verdict and the "A: … · B: … → op: …" line.

## Key data models

Machine (JSON):
```json
{"states": ["q0","q1"], "alphabet": ["0","1"], "start": "q0", "accept": ["q1"],
 "delta": {"q0": {"0": "q1", "1": "q0"}, "q1": {"0": "q1", "1": "q0"}}}
```
State names must not contain `(`, `)` or `,`, because those characters are used in product state names.

## API

| Endpoint | Request | Response |
|---|---|---|
| `GET /api/examples` | none | `[{name, m}]` |
| `POST /api/build` | `{A, B, op}`, where `op` ∈ union, intersection, complement, difference (B is ignored for complement) | `{errors: [str]}` **or** `{machine, table_html, notes: [str], parts: {A, B?}, info: {pairs, accepted, rejected}}` |
| `POST /api/run` | `{machine, text}` | `{syms, path, accepted}` **or** `{error}` |

`parts` holds the *completed* input machines. In `info`, `pairs` is \|Q_A\|·\|Q_B\| (`null` for complement), and `accepted`/`rejected` are the shortest strings (`""` = ε, `null` = none exists). There is no database.

## Design system

The tokens are CSS custom properties on `:root` in `style.css`, with a dark override under `prefers-color-scheme: dark`:
`--bg --card --ink --mut --ac --acl --bd --th --field --canvas --edge --elab`, status colours `--ok* --er* --w*` (warning), graph highlights `--hl --hlbd --cur`, and `--mono` for state names, symbols and strings. The SVG graph uses the same tokens through classes: `.edge`, `.ahead`, `.elabel`, `.node`, `.inner`, `.hl`, `.cur`, `.empty`. `.gwrap` is the scrolling graph box, and `.mini` caps the input diagrams at 320px tall.

## Dependencies

Python 3 standard library only (`http.server`, `json`, `copy`, `html`, `unittest`). Plain HTML, CSS and JS in the browser, with no frameworks and no CDN.

## Configuration

None: no environment variables and no secrets. The server binds to 127.0.0.1 on the first free port from 8000 to 8009.
