"""test_dfa.py — checks every operation against its theoretical definition.  Run: python test_dfa.py"""
import itertools, unittest
import dfa_logic as L

STRINGS = [""] + ["".join(t) for n in range(1, 8) for t in itertools.product("01", repeat=n)]  # ε .. length 7
EX = [e["m"] for e in L.EXAMPLES]
LOGIC = {"union": lambda a, b: a or b, "intersection": lambda a, b: a and b, "difference": lambda a, b: a and not b}
acc = lambda m, s: L.run(m, s)["accepted"]


class Tests(unittest.TestCase):
    def test_product_ops_match_logic(self):
        for op, f in LOGIC.items():
            for A, B in itertools.product(EX, EX):
                R = L.build(A, B, op)["machine"]
                for s in STRINGS:
                    self.assertEqual(acc(R, s), f(acc(A, s), acc(B, s)), (op, s))

    def test_complement_reverses(self):
        for A in EX:
            R = L.build(A, None, "complement")["machine"]
            for s in STRINGS:
                self.assertNotEqual(acc(R, s), acc(A, s))

    def test_different_sizes_and_multiple_accepting(self):
        multi = {"states": ["a", "b", "c"], "alphabet": ["0", "1"], "start": "a", "accept": ["b", "c"],
                 "delta": {"a": {"0": "b", "1": "c"}, "b": {"0": "b", "1": "a"}, "c": {"0": "c", "1": "c"}}}
        R = L.build(multi, EX[0], "union")["machine"]
        for s in STRINGS:
            self.assertEqual(acc(R, s), acc(multi, s) or acc(EX[0], s))

    def test_state_without_outgoing_transitions(self):
        # B is accepting and has NO outgoing transitions: language = {"0"}
        A = {"states": ["A", "B"], "alphabet": ["0", "1"], "start": "A", "accept": ["B"],
             "delta": {"A": {"0": "B"}, "B": {}}}
        out = L.build(A, A, "union")
        self.assertTrue(out["notes"] and "machine" in out)
        for s in STRINGS:
            self.assertEqual(acc(out["machine"], s), s == "0")
        comp = L.build(A, None, "complement")["machine"]       # complement must accept everything except "0"
        for s in STRINGS:
            self.assertEqual(acc(comp, s), s != "0")

    def test_errors_and_invalid_symbol(self):
        self.assertIn("error", L.run(EX[0], "1a0"))
        self.assertTrue(L.run(EX[0], "")["accepted"] is False)           # ε on 'ends in 0'
        other = dict(EX[1], alphabet=["0", "1", "2"])
        self.assertIn("errors", L.build(EX[0], other, "union"))
        self.assertIn("errors", L.build({**EX[0], "start": ""}, EX[1], "union"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
