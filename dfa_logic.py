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
    bad = [s for s in m["states"] if any(c in s for c in "(),")]
    if bad:  # these characters are used to name product pairs "(p, q)" and would make names collide
        errors.append(f"{name}: state names may not contain '(', ')' or ',' ({fmt(bad)}).")
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
def product(A, B, op, trace=None):
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
            is_new = t not in pair
            if is_new:                         # newly discovered reachable state
                pair[t] = t_pair
                states.append(t)
            delta[s][a] = t
            if trace is not None:              # record the step for the "construction steps" panel
                trace.append({"from": s, "p": p, "q": q, "sym": a, "tp": t_pair[0], "tq": t_pair[1], "to": t, "new": is_new})
        i += 1
    # accepting rule decides which product states are final
    accept = [s for s in states if rule(pair[s][0] in A["accept"], pair[s][1] in B["accept"])]
    return {"states": states, "alphabet": list(A["alphabet"]), "start": start, "accept": accept, "delta": delta}


def complement(A):
    """Same states, transitions and start state; accepting and non-accepting states swap."""
    m = copy.deepcopy(A)
    m["accept"] = [s for s in A["states"] if s not in A["accept"]]
    return m


def shortest(m, accepted=True):
    """BFS from the start state: the shortest string that ends in an accepting state
    (accepted=True) or a non-accepting state (accepted=False). None = no such string,
    i.e. the language is empty (resp. equals Σ*)."""
    seen, queue = {m["start"]: ""}, [m["start"]]
    for s in queue:                                    # the list is also the queue
        if (s in m["accept"]) == accepted:
            return seen[s]
        for a in m["alphabet"]:
            t = m["delta"][s][a]
            if t not in seen:
                seen[t] = seen[s] + a
                queue.append(t)
    return None


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



# ---------------------------------------------------------------- step-by-step explanation + validation
def final_table(A, B, R, op):
    """Rows explaining WHY each product state is final (or not): A accepts?, B accepts?, rule -> final?"""
    rows = []
    for s in R["states"]:
        p, q = s[1:-1].split(", ")
        rows.append({"state": s, "inA": p in A["accept"], "inB": q in B["accept"], "final": s in R["accept"]})
    return rows


def complement_table(A, R):
    """Rows for the complement: every state keeps its transitions, only the final flag flips."""
    return [{"state": s, "wasFinal": s in A["accept"], "final": s in R["accept"]} for s in A["states"]]


def expected_accepts(op, a, b):
    """The theoretical definition of each operation, written independently of the construction."""
    return {"union": a or b, "intersection": a and b, "difference": a and not b, "complement": not a}[op]


def verify(R, A, B, op, cap=20000):
    """Compare the constructed DFA with the DEFINITION of the operation on every string up to a length
    (the longest length that keeps the number of strings under 'cap', at most 8).
    Returns {max_len, tested, mismatches:[...], rows:[...]}; rows are the first strings, for display."""
    import itertools
    alpha = list(R["alphabet"])
    max_len, total = 0, 1
    while max_len < 8 and total + len(alpha) ** (max_len + 1) <= cap:
        max_len += 1
        total += len(alpha) ** max_len
    tested, mismatches, rows = 0, [], []
    for n in range(max_len + 1):
        for tup in itertools.product(alpha, repeat=n):
            w = "".join(tup)
            a = run(A, w)["accepted"]
            b = run(B, w)["accepted"] if B is not None else False
            want, got = expected_accepts(op, a, b), run(R, w)["accepted"]
            tested += 1
            if want != got and len(mismatches) < 5:
                mismatches.append(w)
            if len(rows) < 10:
                rows.append({"w": w, "a": a, "b": b if B is not None else None, "want": want, "got": got})
    return {"max_len": max_len, "tested": tested, "mismatches": mismatches, "ok": not mismatches, "rows": rows}

# ---------------------------------------------------------------- main entry points
def build(A, B, op):
    """Validate, complete, construct. Returns {"errors": [...]} or
    {"machine", "table_html", "notes", "parts", "info"}. "parts" are the completed input
    machines (so strings can also be run on A and B); "info" holds language facts."""
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
        R, parts, pairs = complement(A), {"A": A}, None
        steps = {"kind": "complement", "table": complement_table(A, R)}
        Bv = None
    else:
        B, dead_b = complete(B)
        if dead_b:
            notes.append(f"Machine B had missing transitions, so it was completed with a non-accepting trap state '{dead_b}'.")
        trace = []
        R, parts, pairs = product(A, B, op, trace), {"A": A, "B": B}, len(A["states"]) * len(B["states"])
        steps = {"kind": "product", "start": R["start"], "moves": trace, "table": final_table(A, B, R, op), "rule": OPS[op][2]}
        Bv = B
    info = {"pairs": pairs, "accepted": shortest(R, True), "rejected": shortest(R, False)}
    return {"machine": R, "table_html": table_html(R), "notes": notes, "parts": parts, "info": info,
            "steps": steps, "validation": verify(R, A, Bv, op)}


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

def test_strings(A, B, texts):
    """Run each string on Machine A and on Machine B separately (no operation applied).
    A machine with missing transitions is completed with a trap state first, so the answer
    matches the language it defines. Returns {"A": ..., "B": ...}; each side is either
    {"errors": [...]} (machine not valid yet) or {"dead": name or None, "results": [run(...), ...]}."""
    out = {}
    for key, m in (("A", A), ("B", B)):
        errors = validate(m, f"Machine {key}")
        if errors:
            out[key] = {"errors": errors}
            continue
        full, dead = complete(m)
        out[key] = {"dead": dead, "results": [run(full, t) for t in texts]}
    return out


def _m(states, start, accept, rows):
    return {"states": states, "alphabet": ["0", "1"], "start": start, "accept": accept,
            "delta": {s: {"0": r[0], "1": r[1]} for s, r in zip(states, rows)}}


EXAMPLES = [
    {"name": "Ends in 0",         "m": _m(["q0", "q1"], "q0", ["q1"], [["q1", "q0"], ["q1", "q0"]])},
    {"name": "Even number of 1s", "m": _m(["e", "o"], "e", ["e"], [["e", "o"], ["o", "e"]])},
    {"name": "Starts with 1",     "m": _m(["s", "a", "d"], "s", ["a"], [["d", "a"], ["a", "a"], ["d", "d"]])},
    {"name": "Contains 00",       "m": _m(["r0", "r1", "r2"], "r0", ["r2"], [["r1", "r0"], ["r2", "r0"], ["r2", "r2"]])},
]
