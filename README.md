# Regular Language Closure Operations Simulator
**Run:** `python app.py` (Python 3, no installs) → opens http://127.0.0.1:8000
**Test:** `python test_dfa.py`

- `dfa_logic.py` — ALL the automata logic: validation, trap-state completion, product construction (BFS), complement, string run, step explanations. Read this file for the presentation.
- `app.py` — tiny server connecting the page to `dfa_logic.py`.
- `index.html`, `style.css`, `script.js`, `graph.js` — interface and SVG drawing only.
