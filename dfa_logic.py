"""dfa_logic.py — ALL automata-theory logic of the simulator (pure Python, no libraries).

A machine is a plain dict (so it converts to JSON easily):
    {"states": ["q0","q1"], "alphabet": ["0","1"], "start": "q0",
     "accept": ["q1"], "delta": {"q0": {"0": "q1", "1": "q0"}, ...}}
"""
import copy
from html import escape as esc

# Operation name -> (symbol, accepting rule on (A accepts?, B accepts?), text for explanation)
OPS = {
    "union":        ("∪", lambda a, b: a or b,      "qA ∈ F_A OR qB ∈ F_B"),
    "intersection": ("∩", lambda a, b: a and b,     "qA ∈ F_A AND qB ∈ F_B"),
    "difference":   ("−", lambda a, b: a and not b, "qA ∈ F_A AND qB ∉ F_B"),
}


def label(p, q):
    """Name of a product state."""
    return f"({p}, {q})"


# ---------------------------------------------------------------- validation
def validate(m, name):
    """Return a list of error messages (empty = OK). Missing transitions are NOT errors:
    they are fixed later by complete()."""
    errors = []
    if not m["alphabet"]:
        errors.append(f"{name}: the alphabet is empty.")
    if any(len(a) != 1 for a in m["alphabet"]):
        errors.append(f"{name}: every alphabet symbol must be a single character.")
    if not m["states"]:
        errors.append(f"{name}: add at least one state.")
    elif m["start"] not in m["states"]:
        errors.append(f"{name}: select a start state.")
    for s in m["states"]:
        for a, t in m["delta"].get(s, {}).items():
            if a in m["alphabet"] and t not in m["states"]:
                errors.append(f"{name}: δ({s}, {a}) points to unknown state '{t}'.")
    return errors


def complete(m):
    """Make the DFA complete. Every missing transition goes to a non-accepting 'dead' (trap)
    state that loops to itself. This does not change the language, and it is required for
    complement and the product construction. Returns (machine, dead_state_name or None)."""
    m = copy.deepcopy(m)
    missing = [(s, a) for s in m["states"] for a in m["alphabet"] if not m["delta"].get(s, {}).get(a)]
    if not missing:
        return m, None
    dead = "dead"
    while dead in m["states"]:
        dead += "'"
    m["states"].append(dead)
    m["delta"][dead] = {a: dead for a in m["alphabet"]}
    for s, a in missing:
        m["delta"].setdefault(s, {})[a] = dead
    return m, dead


# ---------------------------------------------------------------- operations
def product(A, B, op):
    """Product construction for union / intersection / difference.
    Explores only reachable pairs using BFS (the list 'states' is also the queue)."""
    _, rule, _ = OPS[op]
    start = label(A["start"], B["start"])
    states, pair, delta = [start], {start: (A["start"], B["start"])}, {}
    i = 0
    while i < len(states):
        s = states[i]
        p, q = pair[s]
        delta[s] = {}
        for a in A["alphabet"]:
            t_pair = (A["delta"][p][a], B["delta"][q][a])
            t = label(*t_pair)
            if t not in pair:                  # newly discovered reachable state
                pair[t] = t_pair
                states.append(t)
            delta[s][a] = t
        i += 1
    # accepting rule decides which product states are final
    accept = [s for s in states if rule(pair[s][0] in A["accept"], pair[s][1] in B["accept"])]
    return {"states": states, "alphabet": list(A["alphabet"]), "start": start, "accept": accept, "delta": delta}


def complement(A):
    """Same states, transitions and start state; accepting and non-accepting states swap."""
    m = copy.deepcopy(A)
    m["accept"] = [s for s in A["states"] if s not in A["accept"]]
    return m


# ---------------------------------------------------------------- explanation
def fmt(items):
    return "{" + ", ".join(esc(x) for x in items) + "}"


def table_html(m):
    head = "".join(f"<th>{esc(a)}</th>" for a in m["alphabet"])
    rows = ""
    for s in m["states"]:
        mark = ("→ " if s == m["start"] else "") + ("* " if s in m["accept"] else "")
        cells = "".join(f"<td>{esc(m['delta'][s][a])}</td>" for a in m["alphabet"])
        rows += f"<tr><td>{mark}<b>{esc(s)}</b></td>{cells}</tr>"
    return (f"<table class='t'><tr><th>State</th>{head}</tr>{rows}</table>"
            "<p class='muted'>→ start state, * accepting state</p>")


# ---------------------------------------------------------------- main entry points
def build(A, B, op):
    """Validate, complete, construct. Returns {"errors": [...]} or
    {"machine", "table_html", "notes"}."""
    errors = validate(A, "Machine A")
    if op != "complement":
        errors += validate(B, "Machine B")
        if not errors and set(A["alphabet"]) != set(B["alphabet"]):
            errors.append(f"Alphabets differ ({fmt(A['alphabet'])} vs {fmt(B['alphabet'])}). Both machines must use the "
                          "same alphabet Σ so that the product is defined.")
    if errors:
        return {"errors": errors}

    notes = []
    A, dead_a = complete(A)
    if dead_a:
        notes.append(f"Machine A had missing transitions, so it was completed with a non-accepting trap state '{dead_a}'.")
    if op == "complement":
        R = complement(A)
    else:
        B, dead_b = complete(B)
        if dead_b:
            notes.append(f"Machine B had missing transitions, so it was completed with a non-accepting trap state '{dead_b}'.")
        R = product(A, B, op)
    return {"machine": R, "table_html": table_html(R), "notes": notes}


def run(m, text):
    """Run a string on a (complete) DFA. '' or 'ε' is the empty string."""
    symbols = [] if text in ("", "ε") else list(text)
    for c in symbols:
        if c not in m["alphabet"]:
            return {"error": f"Symbol '{c}' is not in the alphabet {{{', '.join(m['alphabet'])}}}."}
    path = [m["start"]]
    for c in symbols:
        path.append(m["delta"][path[-1]][c])
    return {"syms": symbols, "path": path, "accepted": path[-1] in m["accept"]}


def _m(states, start, accept, rows):
    return {"states": states, "alphabet": ["0", "1"], "start": start, "accept": accept,
            "delta": {s: {"0": r[0], "1": r[1]} for s, r in zip(states, rows)}}


EXAMPLES = [
    {"name": "Ends in 0",         "m": _m(["q0", "q1"], "q0", ["q1"], [["q1", "q0"], ["q1", "q0"]])},
    {"name": "Even number of 1s", "m": _m(["e", "o"], "e", ["e"], [["e", "o"], ["o", "e"]])},
    {"name": "Starts with 1",     "m": _m(["s", "a", "d"], "s", ["a"], [["d", "a"], ["a", "a"], ["d", "d"]])},
    {"name": "Contains 00",       "m": _m(["r0", "r1", "r2"], "r0", ["r2"], [["r1", "r0"], ["r2", "r0"], ["r2", "r2"]])},
]
